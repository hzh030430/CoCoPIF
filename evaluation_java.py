import sys
import time
import io
import traceback
import psutil
import contextlib
import argparse
import json
import os
import tempfile
import subprocess
import shutil
import ast
import re
import signal
import threading
from typing import Dict, Any, List, Union

def normalize_output(output):
    """标准化输出字符串，处理引号和其他可能的格式差异，并检测输出格式"""
    output = output.strip()
    
    # 检测输出格式
    format_detected = "direct"  # 默认格式为直接输出
    if output.startswith('{') and output.endswith('}'):
        format_detected = '{ output }'
    elif output.startswith('[') and output.endswith(']'):
        format_detected = '[ output ]'
    elif output.startswith('(') and output.endswith(')'):
        format_detected = '( output )'
    else:
        format_detected = 'direct'
    
    # 如果是上述格式之一，移除首尾符号
    if format_detected != "direct":
        output = output[1:-1].strip()
    
    try:
        # 如果是合法的JSON字符串，解析并重新序列化以规范化格式
        parsed = json.loads(f'"{output}"')  # 添加引号以使其成为合法的JSON字符串
        return parsed, format_detected
    except:
        pass
    
    # 如果不是JSON，返回原始字符串和检测到的格式
    return output, format_detected

def smart_compare(actual, expected):
    """智能比较两个输出字符串，处理常见的格式差异"""
    actual_normalized, format_actual = normalize_output(actual)
    expected_normalized, format_expected = normalize_output(expected)
    
    if actual_normalized == expected_normalized:
        return True
    
    if actual_normalized.replace('"', '').replace("'", '') == expected_normalized.replace('"', '').replace("'", ''):
        return True
    
    try:
        actual_num = float(actual_normalized)
        expected_num = float(expected_normalized)
        return abs(actual_num - expected_num) < 1e-6
    except:
        pass
    
    if actual_normalized.replace('"', "'") == expected_normalized.replace('"', "'"):
        return True
    
    try:
        actual_obj = ast.literal_eval(actual_normalized)
        expected_obj = ast.literal_eval(expected_normalized)
        return actual_obj == expected_obj
    except:
        pass
    
    return False

def extract_class_name(java_code):
    """从Java代码中提取公共类名"""
    # 使用正则表达式查找public class声明
    match = re.search(r'public\s+class\s+(\w+)', java_code)
    if match:
        return match.group(1)
    
    # 如果没有public class，尝试查找普通class声明
    match = re.search(r'class\s+(\w+)', java_code)
    if match:
        return match.group(1)
    
    # 默认类名
    return "Program"

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

def evaluate_java_code(code: str, test_input: str, expected_output: str) -> Dict[str, Any]:
    """编译并执行给定的Java代码并评估其性能和正确性"""
    result = {
        'correct': False,
        'execution_time': 0,
        'memory_usage': 0,
        'peak_memory_usage': 0,  # 添加峰值内存使用
        'output': '',
        'error': None,
        'compilation_error': None,
        'memory_overflow': False,  # 添加内存溢出标志
        'output_format': None
    }
    
    # 检查是否安装了Java编译器
    javac_path = shutil.which("javac")
    java_path = shutil.which("java")
    
    if not javac_path:
        result['compilation_error'] = "找不到Java编译器(javac)。请确保Java JDK已安装并添加到系统PATH环境变量中。"
        result['error'] = "编译环境错误: 找不到Java编译器"
        return result
    
    if not java_path:
        result['compilation_error'] = "找不到Java运行时(java)。请确保Java JDK已安装并添加到系统PATH环境变量中。"
        result['error'] = "编译环境错误: 找不到Java运行时"
        return result
    
    # 从代码中提取类名
    class_name = extract_class_name(code)
    
    # 创建临时目录用于编译
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建源代码文件 (注意类名与文件名必须一致)
        source_file = os.path.join(temp_dir, f"{class_name}.java")
        
        # 写入源代码文件
        with open(source_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # 编译Java代码，设置编译超时
        compile_command = [javac_path, source_file]
        try:
            compile_process = subprocess.run(
                compile_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=False,
                timeout=30  # 编译超时设置为30秒
            )
            
            # 检查编译错误
            if compile_process.returncode != 0:
                result['compilation_error'] = compile_process.stderr
                result['error'] = f"编译错误: {compile_process.stderr}"
                return result
        except subprocess.TimeoutExpired:
            result['compilation_error'] = "编译超时: 编译时间超过30秒"
            result['error'] = "编译超时"
            return result
        except Exception as e:
            result['compilation_error'] = str(e)
            result['error'] = f"编译异常: {str(e)}"
            return result
            
        # 准备运行程序
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024  # 初始内存 (KB)
        
        # 运行程序并计时
        start_time = time.time()
        
        # 添加杀死进程的命令, 处理平台差异
        kill_cmd = "kill -9 %p" if os.name != 'nt' else "taskkill /F /PID %p"
        
        # 使用Popen而不是run，这样可以直接获取进程对象
        # 注意: 移除了HeapDumpOnOutOfMemoryError参数
        run_command = [
            java_path, 
            "-Xmx512m",  # 限制最大堆内存
            "-XX:+ExitOnOutOfMemoryError",  # 发生OOM时自动退出
            f"-XX:OnOutOfMemoryError={kill_cmd}",  # 在OOM发生时执行kill命令
            "-cp", 
            temp_dir, 
            class_name
        ]
        
        java_proc = None
        timer = None
        
        # 定义变量来存储Java进程内存监控信息
        peak_memory = 0
        memory_monitor_stop = threading.Event()
        memory_overflow_detected = threading.Event()  # 用于在线程间通信内存溢出状态
        
        # 定义内存监控函数
        def monitor_memory_usage():
            nonlocal peak_memory
            while not memory_monitor_stop.is_set() and java_proc and java_proc.poll() is None:
                try:
                    proc = psutil.Process(java_proc.pid)
                    mem_info = proc.memory_info()
                    current_memory = mem_info.rss / 1024  # KB
                    peak_memory = max(peak_memory, current_memory)
                    
                    # 如果内存使用超过阈值，立即终止进程
                    # 设置为450MB，稍低于JVM限制，以便主动拦截
                    if current_memory > 450 * 1024:  # 450MB
                        print(f"内存使用超过阈值 (450MB)，立即终止进程: {java_proc.pid}")
                        memory_overflow_detected.set()  # 设置内存溢出标志
                        kill_process_tree(java_proc.pid)
                        break
                except Exception as e:
                    # 忽略进程监控错误
                    pass
                time.sleep(0.1)  # 每100ms检查一次
        
        try:
            # 使用Popen启动进程，并创建一个新的进程组（在Unix系统上有用）
            if os.name != 'nt':  # 非Windows系统
                java_proc = subprocess.Popen(
                    run_command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    preexec_fn=os.setsid  # 在新进程组中启动
                )
            else:  # Windows系统
                java_proc = subprocess.Popen(
                    run_command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP  # Windows上的新进程组
                )
            
            # 启动内存监控线程
            memory_thread = threading.Thread(target=monitor_memory_usage)
            memory_thread.daemon = True
            memory_thread.start()
            
            # 设置更强的超时控制 - 使用定时器
            def timeout_handler():
                """超时处理函数，强制终止进程"""
                nonlocal java_proc
                if java_proc and java_proc.poll() is None:
                    print(f"定时器触发强制终止Java进程 (PID: {java_proc.pid})")
                    # 使用我们的函数终止整个进程树
                    kill_process_tree(java_proc.pid)
            
            # 设置超时定时器（比communicate超时稍长一些，作为备份）
            timer = threading.Timer(11, timeout_handler)
            timer.daemon = True
            timer.start()
            
            # 传递输入并等待结果
            try:
                outs, errs = java_proc.communicate(input=test_input, timeout=10)
                
                # 取消定时器
                if timer and timer.is_alive():
                    timer.cancel()
                
                execution_time = (time.time() - start_time) * 1000  # 转换为毫秒
                
                # 检查内存监控线程是否检测到内存溢出
                if memory_overflow_detected.is_set():
                    result['memory_overflow'] = True
                    result['error'] = "内存溢出错误: 程序使用内存超过限制 (450MB)"
                    result['output'] = "内存溢出"
                    result['execution_time'] = execution_time
                    return result  # 提前返回结果
                
                # 获取输出
                if java_proc.returncode != 0:
                    if "OutOfMemoryError" in errs:
                        result['error'] = f"内存溢出错误: {errs}"
                        result['output'] = "内存溢出"  # 统一输出
                        result['memory_overflow'] = True  # 设置内存溢出标志
                        return result  # 提前返回结果
                    else:
                        result['error'] = f"运行时错误 (返回码 {java_proc.returncode}): {errs}"
                        result['output'] = outs
                else:
                    result['output'] = outs.strip()
                
                expected_output = expected_output.strip()
                
                # 标准化输出并检测格式
                actual_normalized, output_format = normalize_output(result['output'])
                expected_normalized, _ = normalize_output(expected_output.strip())
                
                # 使用智能比较检查结果
                result['correct'] = smart_compare(result['output'], expected_output)
                result['execution_time'] = execution_time
                result['output_format'] = output_format
                
                # 测量内存使用（执行后）
                end_memory = process.memory_info().rss / 1024  # 最终内存 (KB)
                result['memory_usage'] = end_memory - start_memory
            
            except subprocess.TimeoutExpired:
                # 在超时发生时，保持之前的处理方式
                raise
                
        except subprocess.TimeoutExpired:
            # 超时处理 - 直接终止我们启动的进程
            result['error'] = "运行超时: 程序执行时间超过10秒"
            result['output'] = "运行超时"
            result['execution_time'] = 10000  # 设为最大超时时间
            
            if java_proc:
                print(f"TimeoutExpired: 终止超时Java进程 (PID: {java_proc.pid})")
                # 通过多种方式终止进程
                
                # 1. 使用自定义函数递归终止进程树
                kill_success = kill_process_tree(java_proc.pid)
                
                # 2. 如果上面的方法失败，尝试操作系统特定的命令
                if not kill_success or java_proc.poll() is None:
                    try:
                        if os.name == 'nt':  # Windows
                            subprocess.run(['taskkill', '/F', '/T', '/PID', str(java_proc.pid)], 
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
                        else:  # Unix
                            # 尝试发送SIGKILL信号到进程组
                            try:
                                pgid = os.getpgid(java_proc.pid)
                                os.killpg(pgid, signal.SIGKILL)
                            except:
                                # 如果找不到进程组，直接杀死进程
                                try:
                                    os.kill(java_proc.pid, signal.SIGKILL)
                                except:
                                    pass
                    except Exception as e:
                        print(f"使用系统命令终止进程失败: {e}")
                
                # 3. 最后尝试使用进程对象的kill方法
                try:
                    if java_proc.poll() is None:
                        java_proc.kill()
                        java_proc.wait(timeout=2)
                except:
                    pass
                
                # 日志输出进程终止结果
                if java_proc.poll() is None:
                    print("警告: 无法终止Java进程，进程可能仍在运行")
                else:
                    print(f"Java进程已终止，返回码: {java_proc.returncode}")
                
                # 清理资源
                try:
                    if java_proc.stdin:
                        java_proc.stdin.close()
                    if java_proc.stdout:
                        java_proc.stdout.close()
                    if java_proc.stderr:
                        java_proc.stderr.close()
                except:
                    pass
            
        except Exception as e:
            result['error'] = f"执行异常: {str(e)}"
            result['output'] = traceback.format_exc()
            
            # 确保在异常情况下也终止Java进程
            if java_proc and java_proc.poll() is None:
                kill_process_tree(java_proc.pid)
        
        finally:
            # 确保停止内存监控线程
            memory_monitor_stop.set()
            if 'memory_thread' in locals() and memory_thread.is_alive():
                memory_thread.join(timeout=1)
                
            # 将监控的内存峰值添加到结果中
            result['peak_memory_usage'] = peak_memory
            
            # 确保在所有情况下都取消定时器
            if timer and timer.is_alive():
                timer.cancel()
                
            # 确保在所有情况下都检查并尝试终止潜在的遗留进程
            if java_proc and java_proc.poll() is None:
                print(f"Finally块: 尝试终止可能的遗留Java进程 (PID: {java_proc.pid})")
                kill_process_tree(java_proc.pid)
                
                # 如果kill_process_tree不成功，尝试使用操作系统命令
                if java_proc.poll() is None:
                    try:
                        if os.name == 'nt':
                            subprocess.run(['taskkill', '/F', '/T', '/PID', str(java_proc.pid)],
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
                        else:
                            try:
                                os.kill(java_proc.pid, signal.SIGKILL)
                            except:
                                pass
                    except:
                        pass
                
                # 最后检查是否确实终止了进程
                if java_proc.poll() is None:
                    print("严重警告: 所有终止进程的尝试均失败")
    
    return result

def run_test_case(code: str, test_input: str, expected_output: str, case_id: int = None) -> Dict[str, Any]:
    """运行测试用例并打印结果"""
    if case_id is not None:
        print(f"\n测试用例 #{case_id}:")
    else:
        print("正在评估代码...")
        
    result = evaluate_java_code(code, test_input, expected_output)
    
    if result['compilation_error']:
        print("编译失败")
        print("\n--- 编译错误 ---")
        print(result['compilation_error'])
        return result
    
    print(f"正确性: {'通过' if result['correct'] else '失败'}")
    print(f"执行时间: {result['execution_time']:.2f} 毫秒")
    print(f"内存使用: {result['memory_usage']:.2f} KB")
    
    # 添加峰值内存使用的输出
    if result.get('peak_memory_usage', 0) > 0:
        print(f"峰值内存: {result['peak_memory_usage']:.2f} KB")
    
    # 内存溢出的特殊处理
    if result.get('memory_overflow', False):
        print("\n--- 内存溢出 ---")
        print("程序使用的内存超出限制，已强制终止")
    elif not result['correct']:
        print("\n--- 实际输出 ---")
        print(result['output'])
        print("\n--- 期望输出 ---")
        print(expected_output)
        print("\n--- 输出比较 ---")
        print(f"直接比较: {result['output'] == expected_output}")
        print(f"标准化比较: {normalize_output(result['output'])[0] == normalize_output(expected_output)[0]}")
        print(f"移除引号比较: {result['output'].replace('\"', '').replace('\'', '') == expected_output.replace('\"', '').replace('\'', '')}")
    
    if result['error'] and not result.get('memory_overflow', False):
        print("\n--- 错误信息 ---")
        print(result['error'])
        
    return result

def parse_structured_test_cases(data):
    """解析结构化测试用例"""
    inputs = []
    outputs = []
    
    for test_case in data:
        if isinstance(test_case, dict) and 'input' in test_case and 'output' in test_case:
            inputs.append(test_case['input'])
            outputs.append(test_case['output'])
    
    return inputs, outputs

def main():
    """主函数，处理命令行参数"""
    parser = argparse.ArgumentParser(description="Java代码评估工具")
    parser.add_argument("code_file", help="要评估的Java代码文件路径")
    
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
    
    # 运行所有测试用例
    print(f"Java代码评估工具 - 运行 {len(inputs)} 个测试用例")
    print("=" * 50)
    
    results = []
    for i, (test_input, expected_output) in enumerate(zip(inputs, outputs)):
        result = run_test_case(code, test_input, expected_output, i+1)
        results.append(result)
    
    # 输出测试摘要
    passed = sum(1 for r in results if r['correct'])
    total = len(results)
    
    memory_issues = sum(1 for r in results if r.get('memory_overflow', False) or (r.get('error') and 'OutOfMemoryError' in str(r.get('error', ''))))
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
                if result.get('memory_overflow', False):
                    error_type = " (内存溢出)"
                elif result.get('error'):
                    if 'OutOfMemoryError' in str(result.get('error')):
                        error_type = " (内存溢出)"
                    elif '超时' in str(result.get('error')):
                        error_type = " (执行超时)"
                print(f"  - 测试用例 #{i+1}{error_type}")
    print("output_format:", [r.get('output_format') for r in results][0])

if __name__ == "__main__":
    main()