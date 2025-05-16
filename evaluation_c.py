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
import signal
import threading
from typing import Dict, Any, List, Union

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
    actual_normalized, format_actual = normalize_output(actual)
    expected_normalized, format_expected = normalize_output(expected)

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

def detect_language(code):
    """
    自动检测代码是C还是C++
    
    Args:
        code: 要检测的代码字符串
        
    Returns:
        检测到的语言: "cpp" 或 "c"
    """
    # 常见的C++特有头文件
    cpp_headers = [
        "iostream", "vector", "string", "algorithm", "queue", "stack", 
        "list", "map", "set", "unordered_map", "unordered_set", 
        "deque", "bitset", "array", "tuple", "memory", "thread", 
        "chrono", "functional", "future", "mutex", "complex",
        "iterator", "numeric", "iomanip", "fstream", "sstream"
    ]
    
    # C和C++都可用但格式不同的头文件
    cpp_style_headers = [
        "cstdio", "cmath", "cstring", "cstdlib", "cctype", "ctime",
        "cassert", "cerrno", "cfloat", "ciso646", "climits", "clocale",
        "csetjmp", "csignal", "cstdarg", "cstddef", "cstdint", "cwchar", "cwctype"
    ]
    
    # 检查C++特有语法
    cpp_features = [
        "class ", "template", "namespace", "std::", "using namespace",
        "public:", "private:", "protected:", "virtual ", "operator",
        "new ", "delete ", "cout", "cin", "endl", "::", "->*", ".*",
        "try", "catch", "throw", "static_cast", "dynamic_cast", "const_cast",
        "reinterpret_cast", "typeid", "nullptr"
    ]
    
    # 检查C++头文件
    for header in cpp_headers:
        if f"#include <{header}>" in code or f'#include "{header}"' in code:
            return "cpp"
    
    # 检查C++风格的C头文件
    for header in cpp_style_headers:
        if f"#include <{header}>" in code or f'#include "{header}"' in code:
            return "cpp"
    
    # 检查C++特有语法特性
    for feature in cpp_features:
        if feature in code:
            return "cpp"
    
    # 默认为C
    return "c"

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

def safe_communicate(proc, input_str, max_size=10*1024*1024):
    """安全地与进程通信，避免内存溢出和编码问题"""
    output = ""
    stderr_data = ""
    
    try:
        # 检查进程是否仍在运行
        if proc.poll() is not None:
            return f"[进程已结束，返回码: {proc.returncode}]", f"[进程已结束]"
        
        # 尝试写入输入数据（使用更健壮的方法）
        if input_str:
            # 确保输入以换行符结束
            if not input_str.endswith('\n'):
                input_str += '\n'
                
            try:
                # 使用字节模式写入，避免编码问题
                if hasattr(proc.stdin, 'buffer'):
                    encoded_input = input_str.encode('utf-8', errors='replace')
                    proc.stdin.buffer.write(encoded_input)
                    proc.stdin.buffer.flush()
                else:
                    # 分块写入（小块以避免缓冲区问题）
                    chunk_size = 1024  # 更小的块
                    for i in range(0, len(input_str), chunk_size):
                        if proc.poll() is not None:  # 再次检查进程状态
                            break
                        chunk = input_str[i:i+chunk_size]
                        proc.stdin.write(chunk)
                        proc.stdin.flush()
                        time.sleep(0.001)  # 微小暂停，避免缓冲区问题
            except IOError as e:
                # 特殊处理 Broken pipe
                if "Broken pipe" in str(e) or "pipe" in str(e).lower():
                    stderr_data = f"[注意: 输入管道已关闭: {e}]"
                # 特殊处理 Invalid argument
                elif "Invalid argument" in str(e):
                    stderr_data = f"[注意: 可能存在编码问题: {e}]"
                    # 尝试使用临时文件重定向输入
                    return _try_file_redirection(proc, input_str, max_size)
                else:
                    return f"[写入stdin失败: {e}]", f"[写入stdin失败: {e}]"
            except Exception as e:
                return f"[写入stdin异常: {e}]", f"[写入stdin异常: {e}]"
        
        # 无论写入是否成功，都尝试关闭stdin并读取输出
        try:
            proc.stdin.close()
        except:
            pass
        
        # 读取输出
        try:
            # 使用select或非阻塞读取处理stdout
            total_read = 0
            timeout = 10
            start_time = time.time()
            
            while proc.poll() is None or proc.stdout.readable():
                # 检查超时
                if time.time() - start_time > timeout:
                    return output + "\n... [读取超时]", stderr_data + "\n... [读取超时]"
                
                try:
                    # 尝试读取，如果没有数据则短暂等待
                    if hasattr(proc.stdout, 'readable') and not proc.stdout.readable():
                        break
                    
                    # 读取一块数据
                    chunk = proc.stdout.read(8192)
                    if not chunk:
                        # 如果进程已结束且没有更多数据，退出循环
                        if proc.poll() is not None:
                            break
                        # 否则短暂等待再试
                        time.sleep(0.05)
                        continue
                    
                    output += chunk
                    total_read += len(chunk)
                    
                    # 检查是否超出最大大小
                    if total_read > max_size:
                        output += "\n... [输出被截断，超过限制大小]"
                        break
                except Exception as e:
                    stderr_data += f"\n读取stdout时出错: {str(e)}"
                    break
            
            # 尝试读取stderr
            try:
                stderr_data = proc.stderr.read() or ""
                if len(stderr_data) > max_size:
                    stderr_data = stderr_data[:max_size] + "\n... [stderr被截断]"
            except Exception as e:
                stderr_data += f"\n读取stderr时出错: {str(e)}"
        
        except Exception as e:
            stderr_data += f"\n读取输出时出错: {str(e)}"
        
        return output, stderr_data
    
    except MemoryError:
        return "[内存溢出：无法处理输出]", "[内存溢出：无法处理stderr]"
    except Exception as e:
        return f"[与进程通信时发生错误: {str(e)}]", f"[与进程通信时发生错误: {str(e)}]"

# 辅助函数-使用临时文件作为输入
def _try_file_redirection(proc, input_str, max_size):
    """尝试使用临时文件重定向代替管道写入"""
    try:
        # 终止当前进程
        if proc and proc.poll() is None:
            kill_process_tree(proc.pid)
        
        # 创建临时文件并写入输入
        with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8') as f:
            f.write(input_str)
            temp_path = f.name
        
        # 重新启动进程，使用文件重定向
        new_proc = subprocess.Popen(
            [proc.args, "<", temp_path],
            shell=True,  # 使用shell处理重定向
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # 等待进程完成，最多10秒
        try:
            output, stderr = new_proc.communicate(timeout=10)
            return output, stderr
        except subprocess.TimeoutExpired:
            kill_process_tree(new_proc.pid)
            return "[执行超时]", "[执行超时]"
        finally:
            # 删除临时文件
            try:
                os.unlink(temp_path)
            except:
                pass
    
    except Exception as e:
        return f"[文件重定向尝试失败: {e}]", f"[文件重定向尝试失败: {e}]"

def evaluate_code(code: str, test_input: str, expected_output: str, language: str = "auto") -> Dict[str, Any]:
    """
    编译并执行给定的C/C++代码并评估其性能和正确性
    
    Args:
        code: 要执行的代码字符串
        test_input: 测试输入
        expected_output: 期望的输出
        language: 编程语言，"c"、"cpp"或"auto"（自动检测）
        
    Returns:
        包含评估结果的字典
    """
    result = {
        'correct': False,
        'execution_time': 0,
        'memory_usage': 0,
        'output': '',
        'error': None,
        'compilation_error': None,
        'output_format': None
    }
    
    # 如果是自动检测模式，检测代码语言
    if language.lower() == "auto":
        language = detect_language(code)
        print(f"自动检测到代码语言: {language}")
    
    # 根据语言选择编译器和文件扩展名
    if language.lower() == "cpp":
        compiler_name = "g++"
        file_extension = ".cpp"
    else:  # 默认为C
        compiler_name = "gcc"
        file_extension = ".c"
    
    # 检查是否安装了编译器
    compiler_path = shutil.which(compiler_name)
    if not compiler_path:
        result['compilation_error'] = f"找不到{compiler_name}编译器。请确保{compiler_name}已安装并添加到系统PATH环境变量中。"
        result['error'] = f"编译环境错误: 找不到{compiler_name}编译器"
        return result
    
    # 创建临时目录用于编译
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建源代码文件
        source_file = os.path.join(temp_dir, f"program{file_extension}")
        executable = os.path.join(temp_dir, "program.exe")
        
        # 写入源代码文件
        with open(source_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # 编译代码
        compile_command = [compiler_path, source_file, "-o", executable]
        
        # 如果代码是C++，添加适当的标志
        if language.lower() == "cpp":
            compile_command.append("-std=c++17")  # 使用C++17标准
        
        try:
            compile_process = subprocess.run(
                compile_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',     # 明确指定编码
                errors='replace',     # 遇到解码错误时替换字符而不是报错
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
        
        # 使用Popen而不是run，这样可以直接获取进程对象
        proc = None
        timer = None
        
        try:
            # 使用Popen启动进程，适应不同的操作系统环境
            if os.name != 'nt':  # 非Windows系统
                proc = subprocess.Popen(
                    executable,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    preexec_fn=os.setsid,  # 在新进程组中启动（Unix系统）
                    bufsize=1024 * 1024  # 限制输出缓冲区为1MB
                )
            else:  # Windows系统
                proc = subprocess.Popen(
                    executable,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,  # Windows上的新进程组
                    bufsize=1024 * 1024  # 限制输出缓冲区为1MB
                )
            
            # 设置更强的超时控制 - 使用定时器
            def timeout_handler():
                """超时处理函数，强制终止进程"""
                nonlocal proc
                if proc and proc.poll() is None:
                    print(f"定时器触发强制终止进程 (PID: {proc.pid})")
                    # 使用函数终止整个进程树
                    kill_process_tree(proc.pid)
            
            # 设置超时定时器（比communicate超时稍长一些，作为备份）
            timer = threading.Timer(11, timeout_handler)
            timer.daemon = True
            timer.start()
            
            # 使用安全的通信函数替代communicate
            try:
                outs, errs = safe_communicate(proc, test_input)
            except MemoryError:
                result['error'] = "内存溢出: 程序输出数据量过大"
                result['output'] = "内存溢出"
                result['execution_time'] = (time.time() - start_time) * 1000
                
                # 确保终止进程
                if proc and proc.poll() is None:
                    kill_process_tree(proc.pid)
                
                # 取消定时器
                if timer and timer.is_alive():
                    timer.cancel()
                    
                return result
            
            # 取消定时器
            if timer and timer.is_alive():
                timer.cancel()
            
            execution_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            # 获取输出
            if proc.returncode != 0:
                result['error'] = f"运行时错误 (返回码 {proc.returncode}): {errs}"
                result['output'] = outs
            else:
                result['output'] = outs.strip()
            
            expected_output = expected_output.strip()
            
            # 标准化输出并检测格式
            actual_normalized, output_format = normalize_output(result['output'])
            expected_normalized, _ = normalize_output(expected_output.strip())
            
            # 使用智能比较检查结果
            result['correct'] = smart_compare(result['output'], expected_output)
            result['output_format'] = output_format  # 记录检测到的输出格式
            result['execution_time'] = execution_time
            
            # 测量内存使用（执行后）
            end_memory = process.memory_info().rss / 1024  # 最终内存 (KB)
            result['memory_usage'] = end_memory - start_memory
            
        except subprocess.TimeoutExpired:
            # 超时处理 - 直接终止我们启动的进程
            result['error'] = "运行超时: 程序执行时间超过10秒"
            result['output'] = "运行超时"
            result['execution_time'] = 10000  # 设为最大超时时间
            
            if proc:
                print(f"TimeoutExpired: 终止超时进程 (PID: {proc.pid})")
                # 通过多种方式终止进程
                
                # 1. 使用自定义函数递归终止进程树
                kill_success = kill_process_tree(proc.pid)
                
                # 2. 如果上面的方法失败，尝试操作系统特定的命令
                if not kill_success or proc.poll() is None:
                    try:
                        if os.name == 'nt':  # Windows
                            subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], 
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
                        else:  # Unix
                            # 尝试发送SIGKILL信号到进程组
                            try:
                                pgid = os.getpgid(proc.pid)
                                os.killpg(pgid, signal.SIGKILL)
                            except:
                                # 如果找不到进程组，直接杀死进程
                                try:
                                    os.kill(proc.pid, signal.SIGKILL)
                                except:
                                    pass
                    except Exception as e:
                        print(f"使用系统命令终止进程失败: {e}")
                
                # 3. 最后尝试使用进程对象的kill方法
                try:
                    if proc.poll() is None:
                        proc.kill()
                        proc.wait(timeout=2)
                except:
                    pass
                
                # 日志输出进程终止结果
                if proc.poll() is None:
                    print("警告: 无法终止进程，进程可能仍在运行")
                else:
                    print(f"进程已终止，返回码: {proc.returncode}")
                
                # 清理资源
                try:
                    if proc.stdin:
                        proc.stdin.close()
                    if proc.stdout:
                        proc.stdout.close()
                    if proc.stderr:
                        proc.stderr.close()
                except:
                    pass
        
        except MemoryError:
            result['error'] = "内存溢出: 程序输出数据量过大"
            result['output'] = "内存溢出"
            result['execution_time'] = (time.time() - start_time) * 1000
            
            # 确保终止进程
            if proc and proc.poll() is None:
                kill_process_tree(proc.pid)
                
        except Exception as e:
            result['error'] = f"执行异常: {str(e)}"
            result['output'] = traceback.format_exc()
            
            # 确保在异常情况下也终止进程
            if proc and proc.poll() is None:
                kill_process_tree(proc.pid)
        
        finally:
            # 确保在所有情况下都取消定时器
            if timer and timer.is_alive():
                timer.cancel()
                
            # 确保在所有情况下都检查并尝试终止潜在的遗留进程
            if proc and proc.poll() is None:
                print(f"Finally块: 尝试终止可能的遗留进程 (PID: {proc.pid})")
                kill_process_tree(proc.pid)
                
                # 如果kill_process_tree不成功，尝试使用操作系统命令
                if proc.poll() is None:
                    try:
                        if os.name == 'nt':
                            subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
                        else:
                            try:
                                os.kill(proc.pid, signal.SIGKILL)
                            except:
                                pass
                    except:
                        pass
    
    return result

def run_test_case(code: str, test_input: str, expected_output: str, case_id: int = None) -> Dict[str, Any]:
    """运行测试用例并打印结果"""
    if case_id is not None:
        print(f"\n测试用例 #{case_id}:")
    else:
        print("正在评估代码...")
        
    result = evaluate_code(code, test_input, expected_output)
    
    if result['compilation_error']:
        print("编译失败")
        print("\n--- 编译错误 ---")
        print(result['compilation_error'])
        return result
    
    print(f"正确性: {'通过' if result['correct'] else '失败'}")
    print(f"执行时间: {result['execution_time']:.2f} 毫秒")
    print(f"内存使用: {result['memory_usage']:.2f} KB")
    
    if not result['correct']:
        # 截断过长的输出以避免打印大量数据
        max_output_length = 1000  # 限制为1000字符
        truncated_output = result['output']
        if len(truncated_output) > max_output_length:
            truncated_output = truncated_output[:max_output_length] + "... [输出被截断]"
        
        truncated_expected = expected_output
        if len(expected_output) > max_output_length:
            truncated_expected = expected_output[:max_output_length] + "... [输出被截断]"
        
        print("\n--- 实际输出 ---")
        print(truncated_output)  # 使用截断后的输出
        print("\n--- 期望输出 ---")
        print(truncated_expected)
        print("\n--- 输出比较 ---")
        print(f"直接比较: {result['output'] == expected_output}")
        print(f"标准化比较: {normalize_output(result['output']) == normalize_output(expected_output)}")
        print(f"移除引号比较: {result['output'].replace('\"', '').replace('\'', '') == expected_output.replace('\"', '').replace('\'', '')}")
    
    if result['error']:
        print("\n--- 错误信息 ---")
        print(result['error'])
        
    return result

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

def main():
    """主函数，处理命令行参数"""
    parser = argparse.ArgumentParser(description="C/C++代码评估工具")
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
    
    # 运行所有测试用例
    language_display = "auto"
    detected_lang = detect_language(code)
    language_display = f"自动检测为{detected_lang.upper()}"
    
    print(f"代码评估工具 - 语言: {language_display} - 运行 {len(inputs)} 个测试用例")
    print("=" * 50)
    
    results = []
    for i, (test_input, expected_output) in enumerate(zip(inputs, outputs)):
        result = run_test_case(code, test_input, expected_output, i+1)
        results.append(result)
    
    # 输出测试摘要
    passed = sum(1 for r in results if r['correct'])
    total = len(results)
    
    print("\n" + "=" * 50)
    print(f"测试摘要: 通过 {passed}/{total} ({passed/total*100:.1f}%)")
    print("output_format:", [r.get('output_format') for r in results][0])
    if passed != total:
        print("\n失败的测试用例:")
        for i, result in enumerate(results):
            if not result['correct']:
                print(f"  - 测试用例 #{i+1}")

if __name__ == "__main__":
    main()