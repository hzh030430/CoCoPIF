import sys
import time
import io
import traceback
import psutil
import contextlib
import argparse
import json
import ast
from typing import Dict, Any, List, Union
import multiprocessing
import os
import signal
import threading
import gc


# 全局进程池
_process_pool = None


def get_process_pool():
    """获取或创建全局进程池"""
    global _process_pool
    if _process_pool is None:
        # 创建进程池，使用最少2个进程，最多CPU数量的进程
        _process_pool = multiprocessing.Pool(processes=max(2, min(4, multiprocessing.cpu_count())))
    return _process_pool


def normalize_output(output):
    """
    标准化输出字符串，处理引号和其他可能的格式差异，并检测输出格式
    
    Args:
        output: 要标准化的输出字符串
        
    Returns:
        tuple: (标准化后的字符串, 检测到的格式)
    """
    # 移除首尾空格
    output = output.strip()
    
    # 检测输出格式
    format_detected = "direct"  # 默认格式为直接输出
    if output.startswith('{') and output.endswith('}'):
        format_detected = '{ output }'
    elif output.startswith('[') and output.endswith(']'):
        format_detected = '[ output ]'
    elif output.startswith('(') and output.endswith(')'):
        format_detected = '( output )'
    
    # 如果是上述格式之一，移除首尾符号
    if format_detected != "direct":
        output = output[1:-1].strip()
    
    # 尝试解析JSON（如果是JSON格式）
    try:
        # 如果是合法的JSON字符串，解析并重新序列化以规范化格式
        parsed = json.loads(f'"{output}"')  # 添加引号以使其成为合法的JSON字符串
        return parsed, format_detected
    except:
        pass
    
    # 如果不是JSON，返回原始字符串和检测到的格式
    return output, format_detected


def smart_compare(actual, expected):
    """
    智能比较两个输出字符串，处理常见的格式差异
    
    Args:
        actual: 实际输出
        expected: 期望输出
        
    Returns:
        布尔值，表示是否匹配
    """
    # 标准化实际输出和期望输出
    actual_normalized, _ = normalize_output(actual)
    expected_normalized, _ = normalize_output(expected)
    
    # 直接比较
    if actual_normalized == expected_normalized:
        return True
    
    # 移除所有引号后比较
    if actual_normalized.replace('"', '').replace("'", '') == expected_normalized.replace('"', '').replace("'", ''):
        return True
    
    # 尝试解析为数字后比较
    try:
        actual_num = float(actual_normalized)
        expected_num = float(expected_normalized)
        return abs(actual_num - expected_num) < 1e-6  # 允许小的浮点数差异
    except:
        pass
    
    # 尝试将双引号替换为单引号后比较
    if actual_normalized.replace('"', "'") == expected_normalized.replace('"', "'"):
        return True
    
    # 尝试比较JSON解析后的对象
    try:
        actual_obj = ast.literal_eval(actual_normalized)
        expected_obj = ast.literal_eval(expected_normalized)
        return actual_obj == expected_obj
    except:
        pass
    
    # 所有比较方法都失败，返回False
    return False


# ...existing code...

def execute_code_in_process(code, test_input):
    """
    在子进程中执行代码，兼容顶层逻辑和 if __name__ == '__main__' 块。

    Args:
        code: 要执行的代码
        test_input: 测试输入字符串

    Returns:
        包含执行结果的字典
    """
    # 保存原始标准输入输出
    original_stdin = sys.stdin
    original_stdout = sys.stdout
    
    # 执行前手动触发垃圾回收
    gc.collect()
    
    exec_result = None
    
    try:
        # --- 第一次尝试：直接执行 ---
        sys.stdin = io.StringIO(test_input)
        captured_output_1 = io.StringIO()
        peak_memory_1 = 0
        process = psutil.Process()
        start_memory_1 = process.memory_info().rss / 1024
        monitor_stop_1 = threading.Event()
        error_1 = None
        success_1 = False
        
        def monitor_memory_1():
            nonlocal peak_memory_1
            while not monitor_stop_1.is_set():
                try:
                    current_memory = process.memory_info().rss / 1024 - start_memory_1
                    peak_memory_1 = max(peak_memory_1, current_memory)
                except: pass
                time.sleep(0.1)

        monitor_thread_1 = threading.Thread(target=monitor_memory_1)
        monitor_thread_1.daemon = True
        monitor_thread_1.start()

        try:
            global_namespace_1 = {}
            with contextlib.redirect_stdout(captured_output_1):
                exec(code, global_namespace_1)
            success_1 = True
        except MemoryError:
             # 单独捕获内存错误以提供更具体的信息
             error_1 = "MemoryError: 程序执行过程中内存溢出 (第一次尝试)"
             success_1 = False
        except Exception as e:
            error_1 = traceback.format_exc() # 捕获第一次尝试的错误
            success_1 = False

        monitor_stop_1.set()
        monitor_thread_1.join(timeout=1)
        end_memory_1 = process.memory_info().rss / 1024
        memory_usage_1 = max(end_memory_1 - start_memory_1, peak_memory_1)
        output_1 = captured_output_1.getvalue().strip()

        # 恢复标准输入输出，以便第二次尝试或返回
        sys.stdin = original_stdin
        sys.stdout = original_stdout

        # 如果第一次尝试有输出或发生错误，则使用其结果
        if output_1 or not success_1:
            exec_result = {
                'success': success_1,
                'output': output_1 if success_1 else (error_1 if 'MemoryError' in str(error_1) else ''), # 内存错误时特殊处理输出
                'memory_usage': memory_usage_1 if success_1 else 0,
                'peak_memory_usage': peak_memory_1 if success_1 else 0,
                'error': error_1
            }
        else:
            # --- 第二次尝试：设置 __name__ = '__main__' ---
            # 只有当第一次尝试成功且无输出时才进行第二次尝试
            gc.collect() # 再次垃圾回收

            sys.stdin = io.StringIO(test_input) # 重置标准输入
            captured_output_2 = io.StringIO()
            peak_memory_2 = 0
            # 重新获取起始内存，因为进程状态可能已改变
            start_memory_2 = process.memory_info().rss / 1024
            monitor_stop_2 = threading.Event()
            error_2 = None
            success_2 = False

            def monitor_memory_2():
                nonlocal peak_memory_2
                while not monitor_stop_2.is_set():
                    try:
                        current_memory = process.memory_info().rss / 1024 - start_memory_2
                        peak_memory_2 = max(peak_memory_2, current_memory)
                    except: pass
                    time.sleep(0.1)

            monitor_thread_2 = threading.Thread(target=monitor_memory_2)
            monitor_thread_2.daemon = True
            monitor_thread_2.start()

            try:
                global_namespace_2 = {'__name__': '__main__'}
                with contextlib.redirect_stdout(captured_output_2):
                    exec(code, global_namespace_2)
                success_2 = True
            except MemoryError:
                 error_2 = "MemoryError: 程序执行过程中内存溢出 (第二次尝试)"
                 success_2 = False
            except Exception as e:
                error_2 = traceback.format_exc() # 捕获第二次尝试的错误
                success_2 = False

            monitor_stop_2.set()
            monitor_thread_2.join(timeout=1)
            end_memory_2 = process.memory_info().rss / 1024
            memory_usage_2 = max(end_memory_2 - start_memory_2, peak_memory_2)
            output_2 = captured_output_2.getvalue().strip()

            # 恢复标准输入输出
            sys.stdin = original_stdin
            sys.stdout = original_stdout

            # 使用第二次尝试的结果
            exec_result = {
                'success': success_2,
                'output': output_2 if success_2 else (error_2 if 'MemoryError' in str(error_2) else ''),
                'memory_usage': memory_usage_2 if success_2 else 0,
                'peak_memory_usage': peak_memory_2 if success_2 else 0,
                'error': error_2
            }

        return exec_result

    except MemoryError:
        # 捕获在 setup/teardown 阶段可能发生的内存错误
        sys.stdin = original_stdin # 确保恢复
        sys.stdout = original_stdout
        return {
            'success': False, 'output': '内存溢出错误', 'memory_usage': 0, 'peak_memory_usage': 0,
            'error': "MemoryError: 程序执行过程中内存溢出 (外部捕获)"
        }
    except Exception as e:
        # 捕获其他意外错误
        sys.stdin = original_stdin # 确保恢复
        sys.stdout = original_stdout
        return {
            'success': False, 'output': '', 'memory_usage': 0, 'peak_memory_usage': 0,
            'error': f"Unexpected error in execute_code_in_process: {traceback.format_exc()}"
        }
    finally:
        # 确保标准输入输出总是被恢复
        sys.stdin = original_stdin
        sys.stdout = original_stdout
        # 执行后再次触发垃圾回收
        gc.collect()

# ... rest of the file ...

def evaluate_code(code: str, test_input: str, expected_output: str) -> Dict[str, Any]:
    """使用进程池评估代码，支持超时处理"""
    result = {
        'correct': False,
        'execution_time': 0,
        'memory_usage': 0,
        'peak_memory_usage': 0,
        'output': '',
        'error': None,
        'output_format': None  # 新增字段，用于记录输出格式
    }
    
    # 获取进程池
    pool = get_process_pool()
    
    # 使用进程池异步执行代码
    start_time = time.time()
    async_result = pool.apply_async(execute_code_in_process, (code, test_input))
    
    try:
        # 最多等待10秒钟获取结果
        exec_result = async_result.get(timeout=10)
        execution_time = (time.time() - start_time) * 1000  # 毫秒
        
        result['output'] = exec_result['output']
        result['error'] = exec_result['error']
        result['memory_usage'] = exec_result['memory_usage']
        result['peak_memory_usage'] = exec_result.get('peak_memory_usage', 0)
        result['execution_time'] = execution_time
        
        if not exec_result['success']:
            # 执行出错
            return result
        
    except multiprocessing.TimeoutError:
        # 发生超时
        execution_time = (time.time() - start_time) * 1000
        result['error'] = "运行超时: 程序执行时间超过10000毫秒"
        result['output'] = "运行超时"
        result['execution_time'] = execution_time
        return result
    
    # 比较结果
    expected_output = expected_output.strip()
    actual_normalized, output_format = normalize_output(result['output'])
    expected_normalized, _ = normalize_output(expected_output)
    result['correct'] = actual_normalized == expected_normalized
    result['output_format'] = output_format  # 记录检测到的输出格式
    
    return result


def run_test_case(code: str, test_input: str, expected_output: str, case_id: int = None) -> Dict[str, Any]:
    """运行测试用例并打印结果"""
    if case_id is not None:
        print(f"\n测试用例 #{case_id}:")
    else:
        print("正在评估代码...")
        
    result = evaluate_code(code, test_input, expected_output)
    
    print(f"正确性: {'通过' if result['correct'] else '失败'}")
    print(f"执行时间: {result['execution_time']:.2f} 毫秒")
    print(f"内存使用: {result['memory_usage']:.2f} KB")
    
    # 添加峰值内存使用报告
    if result.get('peak_memory_usage', 0) > 0:
        print(f"峰值内存: {result['peak_memory_usage']:.2f} KB")
    
    if not result['correct']:
        print("\n--- 实际输出 ---")
        print(result['output'])
        print("\n--- 期望输出 ---")
        print(expected_output)
        print("\n--- 输出比较 ---")
        print(f"直接比较: {result['output'] == expected_output}")
        print(f"标准化比较: {normalize_output(result['output']) == normalize_output(expected_output)}")
        print(f"移除引号比较: {result['output'].replace('\"', '').replace('\'', '') == expected_output.replace('\"', '').replace('\'', '')}")
    
    if result['error']:
        print("\n--- 错误信息 ---")
        print(result['error'])
        
    return result


def run_test_cases_batch(code: str, inputs: List[str], outputs: List[str]) -> List[Dict[str, Any]]:
    """批量运行多个测试用例，利用进程池并行处理"""
    
    pool = get_process_pool()
    
    # 存储所有异步任务
    async_results = []
    start_times = []
    
    # 提交所有任务
    for test_input in inputs:
        start_time = time.time()
        async_result = pool.apply_async(execute_code_in_process, (code, test_input))
        async_results.append(async_result)
        start_times.append(start_time)
    
    # 收集结果
    results = []
    for i, (async_result, start_time, expected_output) in enumerate(zip(async_results, start_times, outputs)):
        result = {
            'correct': False,
            'execution_time': 0,
            'memory_usage': 0,
            'peak_memory_usage': 0,
            'output': '',
            'error': None
        }
        
        try:
            # 获取结果，设置超时
            exec_result = async_result.get(timeout=10)
            execution_time = (time.time() - start_time) * 1000
            
            result['output'] = exec_result['output']
            result['error'] = exec_result['error']
            result['memory_usage'] = exec_result['memory_usage']
            result['peak_memory_usage'] = exec_result.get('peak_memory_usage', 0)
            result['execution_time'] = execution_time
            
            if exec_result['success']:
                # 比较结果
                expected_output = expected_output.strip()
                result['correct'] = smart_compare(result['output'], expected_output)
            
        except multiprocessing.TimeoutError:
            # 超时处理
            execution_time = (time.time() - start_time) * 1000
            result['error'] = "运行超时: 程序执行时间超过10000毫秒"
            result['output'] = "运行超时"
            result['execution_time'] = execution_time
        
        # 显示结果
        print(f"\n测试用例 #{i+1}:")
        print(f"正确性: {'通过' if result['correct'] else '失败'}")
        print(f"执行时间: {result['execution_time']:.2f} 毫秒")
        print(f"内存使用: {result['memory_usage']:.2f} KB")
        
        # 显示峰值内存
        if result.get('peak_memory_usage', 0) > 0:
            print(f"峰值内存: {result['peak_memory_usage']:.2f} KB")
        
        if not result['correct']:
            print("\n--- 实际输出 ---")
            print(result['output'])
            print("\n--- 期望输出 ---")
            print(expected_output)
        
        if result['error']:
            print("\n--- 错误信息 ---")
            print(result['error'])
        
        results.append(result)
    
    return results


def parse_structured_test_cases(data):
    """解析结构化测试用例
    
    Args:
        data: 包含测试用例的列表，每个测试用例是包含input和output字段的字典
        
    Returns:
        inputs列表和outputs列表
    """
    inputs = []
    outputs = []
    
    for test_case in data:
        if isinstance(test_case, dict) and 'input' in test_case and 'output' in test_case:
            inputs.append(test_case['input'])
            outputs.append(test_case['output'])
    
    return inputs, outputs


def kill_process_tree(pid):
    """递归杀死进程树"""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        # 先杀死子进程
        for child in children:
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        
        # 然后杀死父进程
        try:
            if parent.is_running():
                parent.kill()
                parent.wait(3)  # 等待进程终止
        except psutil.NoSuchProcess:
            pass
        
        return True
    except psutil.NoSuchProcess:
        return False
    except Exception as e:
        print(f"杀死进程树时出错: {e}")
        return False


def cleanup_process_pool():
    """清理进程池并确保所有进程都被正确终止"""
    global _process_pool
    if _process_pool is not None:
        try:
            # 首先尝试终止所有可能挂起的进程
            _process_pool.terminate()
            # 然后关闭进程池
            _process_pool.close()
            # 设置超时时间，避免永久等待
            _process_pool.join(timeout=3)
            
            # 检查是否还有未关闭的子进程，强制终止它们
            for p in multiprocessing.active_children():
                try:
                    print(f"终止残留子进程: {p.name} (PID: {p.pid})")
                    p.terminate()
                    p.join(timeout=1)
                    
                    # 如果进程仍在运行，尝试更强力的终止方法
                    if p.is_alive():
                        print(f"进程未响应terminate()，尝试kill(): {p.name} (PID: {p.pid})")
                        # 使用psutil更彻底地终止进程树
                        kill_process_tree(p.pid)
                        
                        # 如果仍然存活，使用操作系统的命令强制终止
                        if p.is_alive():
                            if os.name == 'nt':  # Windows
                                os.system(f"taskkill /F /PID {p.pid} /T")
                            else:  # Unix
                                os.system(f"kill -9 {p.pid}")
                except Exception as e:
                    print(f"无法终止子进程 {p.name}: {e}")
            
            # 强制垃圾回收
            gc.collect()
            
        except Exception as e:
            print(f"清理进程池时发生错误: {e}")
        finally:
            # 重置全局进程池变量
            _process_pool = None
            print("进程池已清理完毕")


def main():
    """主函数，处理命令行参数"""
    # Windows下必须保护主入口点
    if sys.platform == 'win32':
        multiprocessing.freeze_support()
    
    parser = argparse.ArgumentParser(description="代码评估工具")
    parser.add_argument("code_file", help="要评估的代码文件路径")
    
    input_output_group = parser.add_mutually_exclusive_group(required=True)
    input_output_group.add_argument("--test-cases", "-tc", help="JSON格式的测试用例列表")
    input_output_group.add_argument("--test-cases-file", "-tcf", help="包含测试用例的文件路径(JSON格式)")
    
    # 保留旧的参数以保持向后兼容
    input_group = parser.add_argument_group("单独指定输入输出 (与--test-cases互斥)")
    input_group.add_argument("--input", "-i", help="JSON格式的测试输入列表或单个测试输入字符串")
    input_group.add_argument("--input-file", "-if", help="包含测试输入的文件路径(JSON格式)")
    
    output_group = parser.add_argument_group("单独指定输入输出 (与--test-cases互斥)")
    output_group.add_argument("--output", "-o", help="JSON格式的期望输出列表或单个期望输出字符串")
    output_group.add_argument("--output-file", "-of", help="包含期望输出的文件路径(JSON格式)")
    
    # 新增参数：是否启用并行执行
    parser.add_argument("--parallel", "-p", action="store_true", 
                        help="并行执行测试用例（多个测试用例时效率更高）")
    
    # 新增参数：内存限制
    parser.add_argument("--memory-limit", "-m", type=int, default=0,
                       help="设置内存限制 (MB)，超过限制将报告错误 (0表示不限制)")
    
    args = parser.parse_args()
    
    # 读取代码文件
    try:
        with open(args.code_file, 'r', encoding='utf-8') as f:
            code = f.read()
    except Exception as e:
        print(f"读取代码文件时出错: {e}")
        return
    
    inputs = []
    outputs = []
    
    # 优先处理结构化测试用例
    if args.test_cases or args.test_cases_file:
        test_cases_data = None
        
        if args.test_cases:
            try:
                test_cases_data = json.loads(args.test_cases)
            except json.JSONDecodeError as e:
                print(f"解析测试用例JSON时出错: {e}")
                return
        elif args.test_cases_file:
            try:
                with open(args.test_cases_file, 'r', encoding='utf-8') as f:
                    test_cases_data = json.load(f)
            except Exception as e:
                print(f"读取测试用例文件时出错: {e}")
                return
        
        if isinstance(test_cases_data, list):
            inputs, outputs = parse_structured_test_cases(test_cases_data)
        else:
            print("错误: 测试用例必须是一个列表")
            return
    # 如果没有提供结构化测试用例，则回退到旧的方式
    elif (args.input or args.input_file) and (args.output or args.output_file):
        # 获取测试输入
        if args.input:
            try:
                # 尝试解析为JSON
                inputs = json.loads(args.input)
                if not isinstance(inputs, list):
                    inputs = [inputs]
            except json.JSONDecodeError:
                # 如果不是有效的JSON，则视为单个测试用例
                inputs = [args.input]
        elif args.input_file:
            try:
                with open(args.input_file, 'r', encoding='utf-8') as f:
                    # 尝试作为JSON加载
                    try:
                        data = json.load(f)
                        if isinstance(data, list):
                            inputs = data
                        else:
                            inputs = [data]
                    except json.JSONDecodeError:
                        # 如果不是JSON，当作普通文本处理
                        f.seek(0)  # 回到文件开头
                        inputs = [f.read()]
            except Exception as e:
                print(f"读取输入文件时出错: {e}")
                return
        
        # 获取期望输出
        if args.output:
            try:
                # 尝试解析为JSON
                outputs = json.loads(args.output)
                if not isinstance(outputs, list):
                    outputs = [outputs]
            except json.JSONDecodeError:
                # 如果不是有效的JSON，则视为单个测试用例
                outputs = [args.output]
        elif args.output_file:
            try:
                with open(args.output_file, 'r', encoding='utf-8') as f:
                    # 尝试作为JSON加载
                    try:
                        data = json.load(f)
                        if isinstance(data, list):
                            outputs = data
                        else:
                            outputs = [data]
                    except json.JSONDecodeError:
                        # 如果不是JSON，当作普通文本处理
                        f.seek(0)  # 回到文件开头
                        outputs = [f.read()]
            except Exception as e:
                print(f"读取输出文件时出错: {e}")
                return
    else:
        parser.print_help()
        return
    
    # 确保输入和输出数量一致
    if len(inputs) != len(outputs):
        print(f"错误：测试输入数量({len(inputs)})与期望输出数量({len(outputs)})不匹配")
        return
    
    if len(inputs) == 0:
        print("错误: 没有找到测试用例")
        return
    
    # 运行测试用例
    print(f"代码评估工具 - 运行 {len(inputs)} 个测试用例")
    print("=" * 50)
    
    try:
        results = []
        
        # 根据参数决定是并行执行还是顺序执行
        if args.parallel and len(inputs) > 1:
            # 批量并行执行
            results = run_test_cases_batch(code, inputs, outputs)
        else:
            # 顺序执行
            for i, (test_input, expected_output) in enumerate(zip(inputs, outputs)):
                result = run_test_case(code, test_input, expected_output, i+1)
                results.append(result)
        
        # 输出测试摘要
        passed = sum(1 for r in results if r['correct'])
        total = len(results)
        
        # 检测内存和超时问题
        memory_issues = sum(1 for r in results if r.get('error') and 'MemoryError' in str(r.get('error', '')))
        timeout_issues = sum(1 for r in results if r.get('error') and '超时' in str(r.get('error', '')))
        
        print("\n" + "=" * 50)
        print(f"测试摘要: 通过 {passed}/{total} ({passed/total*100:.1f}%)")
        
        if memory_issues > 0:
            print(f"内存溢出问题: {memory_issues}个测试用例")
        if timeout_issues > 0:
            print(f"超时问题: {timeout_issues}个测试用例")
        
        if passed != total:
            print("\n失败的测试用例:")
            for i, result in enumerate(results):
                if not result['correct']:
                    error_type = ""
                    if result.get('error'):
                        if 'MemoryError' in str(result.get('error')):
                            error_type = " (内存溢出)"
                        elif '超时' in str(result.get('error')):
                            error_type = " (执行超时)"
                    print(f"  - 测试用例 #{i+1}{error_type}")
        print("output_format:", [r.get('output_format') for r in results][0])
    finally:
        # 确保在任何情况下都清理进程池
        cleanup_process_pool()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"程序执行过程中出现错误: {e}")
        traceback.print_exc()
        
        # 确保进程池被清理
        cleanup_process_pool()
        
        # 确保所有子进程被终止
        for p in multiprocessing.active_children():
            try:
                p.terminate()
                p.join(timeout=1)
            except:
                pass