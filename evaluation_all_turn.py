import os
import re
import json
import ast
import time
import traceback
import subprocess
from tqdm import tqdm  # 导入tqdm进度条库
import importlib.util
from typing import Dict, Any, List, Union, Tuple, Optional
import sys
import io
import psutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 导入评估模块
def import_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# 获取当前目录路径
current_dir = os.path.dirname(os.path.abspath(__file__))

# 尝试导入各语言的评估模块
try:
    # 修改前: os.path.join(current_dir, "new_try", "evaluation.py")
    # 修改后:
    evaluation_py = import_module_from_path("evaluation", os.path.join(current_dir, "evaluation.py"))
    print("成功导入Python评估模块")
except Exception as e:
    print(f"导入Python评估模块失败: {e}")
    evaluation_py = None

try:
    # 修改前: os.path.join(current_dir, "new_try", "evaluation_c.py")
    # 修改后:
    evaluation_c = import_module_from_path("evaluation_c", os.path.join(current_dir, "evaluation_c.py"))
    print("成功导入C++评估模块")
except Exception as e:
    print(f"导入C++评估模块失败: {e}")
    evaluation_c = None

try:
    # 修改前: os.path.join(current_dir, "new_try", "evaluation_java.py")
    # 修改后:
    evaluation_java = import_module_from_path("evaluation_java", os.path.join(current_dir, "evaluation_java.py"))
    print("成功导入Java评估模块")
except Exception as e:
    print(f"导入Java评估模块失败: {e}")
    evaluation_java = None

change_cases = [
    ('keyword_variable_include', ['Kindly revise your code to incorporate {name} as a variable identifier.', 'Please refactor your code to include {name} as a variable name.', 'Could you modify your code to use {name} as a variable name?', 'We recommend updating your code to utilize {name} as a variable name.', 'It would be appreciated if you could rewrite your code with {name} as a variable name.']),
    ('keyword_variable_number', ['Please revise your code to position {name} as the {number}{suffix} variable in the sequence.', 'Kindly refactor your code to assign {name} as the {number}{suffix} variable in the list.', 'Could you update your code to ensure {name} is the {number}{suffix} variable in the order?', 'We recommend modifying your code to make {name} the {number}{suffix} variable in the structure.', 'It would be appreciated if you could adjust your code to set {name} as the {number}{suffix} variable.']),
    ('keyword_variable_type', ['Please modify the code so that the {number}{suffix} variable declared (when reading the source code top-to-bottom, left-to-right) is explicitly defined with the type {type}.', 'Kindly refactor the code to ensure that the {number}{suffix} variable declared (when reading the source code top-to-bottom, left-to-right) is explicitly defined with the type {type}.', 'Could you update the code to guarantee that the {number}{suffix} variable declared (when reading the source code top-to-bottom, left-to-right) is explicitly defined with the type {type}?', 'We recommend modifying the code to make sure that the {number}{suffix} variable declared (when reading the source code top-to-bottom, left-to-right) is explicitly defined with the type {type}.', 'It would be appreciated if you could adjust the code to ensure that the {number}{suffix} variable declared (when reading the source code top-to-bottom, left-to-right) is explicitly defined with the type {type}.']),
    ('keyword_for', ['Please revise your code to incorporate at least one for loop for iteration.', 'Kindly update your code to include a for loop as part of the implementation.', 'Could you modify your code to ensure it contains at least one for loop?', 'We recommend refactoring your code to integrate a for loop into the logic.', 'It would be appreciated if you could adjust your code to include at least one for loop.']),
    ('keyword_for_not', ['Please revise your code to exclude any for loops in the implementation.', 'Kindly update your code to ensure it does not contain any for loops.', 'Could you modify your code to avoid using for loops entirely?', 'We recommend refactoring your code to remove any for loops from the logic.', 'It would be appreciated if you could adjust your code to omit for loops.']),
    ('keyword_while', ['Please revise your code to incorporate at least one while loop for iterative processing.', 'Kindly update your code to include a while loop as part of the implementation.', 'Could you modify your code to ensure it contains at least one while loop?', 'We recommend refactoring your code to integrate a while loop into the logic.', 'It would be appreciated if you could adjust your code to include at least one while loop.']),
    ('keyword_while_not', ['Please revise your code to exclude any while loops in the implementation.', 'Kindly update your code to ensure it does not contain any while loops.', 'Could you modify your code to avoid using while loops entirely?', 'We recommend refactoring your code to remove any while loops from the logic.', 'It would be appreciated if you could adjust your code to omit while loops.']),
    ('keyword_if', ['Please revise your code to incorporate at least one if statement for conditional logic.', 'Kindly update your code to include an if statement as part of the implementation.', 'Could you modify your code to ensure it contains at least one if statement?', 'We recommend refactoring your code to integrate an if statement into the logic.', 'It would be appreciated if you could adjust your code to include at least one if statement.']),
    ('keyword_if_not', ['Please revise your code to exclude any if statements in the implementation.', 'Kindly update your code to ensure it does not contain any if statements.', 'Could you modify your code to avoid using if statements entirely?', 'We recommend refactoring your code to remove any if statements from the logic.', 'It would be appreciated if you could adjust your code to omit if statements.']),
    ('keyword_function', ['Please revise your code to incorporate exactly {number} {function_form} in the implementation.', 'Kindly update your code to include {number} {function_form} as part of the logic.', 'Could you modify your code to ensure it contains exactly {number} {function_form}?', 'We recommend refactoring your code to integrate {number} {function_form} into the implementation.', 'It would be appreciated if you could adjust your code to include exactly {number} {function_form}.']),
    ('keyword_function_not', ['Please revise your code to exclude any function in the implementation.', 'Kindly update your code to ensure it does not contain any function.', 'Could you modify your code to avoid using function entirely?', 'We recommend refactoring your code to remove any function from the logic.', 'It would be appreciated if you could adjust your code to omit function.']),
    ('keyword_function_one', ['Please revise your code to incorporate {function_form} in the implementation.', 'Kindly update your code to include {function_form} as part of the logic.', 'Could you modify your code to ensure it contains {function_form}?', 'We recommend refactoring your code to integrate {function_form} into the implementation.', 'It would be appreciated if you could adjust your code to include {function_form}.']),
    ('keyword_class', ['Please revise your code to incorporate exactly {number} {class_form} in the implementation.', 'Kindly update your code to include {number} {class_form} as part of the structure.', 'Could you modify your code to ensure it contains {number} {class_form}?', 'We recommend refactoring your code to integrate {number} {class_form} into the design.', 'It would be appreciated if you could adjust your code to include {number} {class_form}.']),
    ('keyword_class_not', ['Please revise your code to exclude any class in the implementation.', 'Kindly update your code to ensure it does not contain any class.', 'Could you modify your code to avoid using class entirely?', 'We recommend refactoring your code to remove any class from the logic.', 'It would be appreciated if you could adjust your code to omit class.']),
    ('keyword_class_one', ['Please revise your code to incorporate {class_form} in the implementation.', 'Kindly update your code to include {class_form} as part of the structure.', 'Could you modify your code to ensure it contains {class_form}?', 'We recommend refactoring your code to integrate {class_form} into the design.', 'It would be appreciated if you could adjust your code to include {class_form}.']),
    ('built_in_function', ['Please revise your code to exclusively utilize built-in functions, avoiding any external library functions.', 'Kindly update your code to restrict function usage to only those that are built-in, excluding any external libraries.', 'Could you modify your code to use only built-in functions and avoid external libraries?', 'We recommend refactoring your code to rely solely on built-in functions and not external libraries.', 'It would be appreciated if you could adjust your code to use only built-in functions.']),
    ('coding_language', ['Please revise your code to be written in {language}.', 'Kindly update your code to conform to the {language} programming language.', 'Could you modify your code to be implemented in {language}?', 'We recommend refactoring your code to be written in {language}.', 'It would be appreciated if you could adjust your code to be written in {language}.']),
    ('coding_style', ['Please revise your code and ensure it contains no comments.', 'Kindly update your code to exclude any comments in the implementation.', 'Could you modify your code to remove all comments?', 'We recommend refactoring your code to omit any comments entirely.', 'It would be appreciated if you could adjust your code to be free of comments.']),
    ('coding_style_include', ['Please revise your code and ensure it contains comments.', 'Kindly update your code to include comments in the implementation.', 'Could you modify your code to add comments?', 'We recommend refactoring your code to include comments for clarity.', 'It would be appreciated if you could adjust your code to have comments.']),
    ('time_limit', ['Please revise your code to ensure it executes within {time} milliseconds.', 'Kindly update your code to optimize its runtime to be within {time} ms.', 'Could you modify your code to guarantee its execution time does not exceed {time} milliseconds?', 'We recommend refactoring your code to achieve a runtime of {time} ms or less.', 'It would be appreciated if you could adjust your code to run within {time} milliseconds.']),
    ('storage_limit', ['Please revise your code to ensure its memory usage remains below {storage} kilobytes.', 'Kindly update your code to optimize its memory consumption to less than {storage} KB.', 'Could you modify your code to guarantee its memory usage does not exceed {storage} kilobytes?', 'We recommend refactoring your code to limit its memory footprint to under {storage} KB.', 'It would be appreciated if you could adjust your code to use less than {storage} KB of memory.']),
    ('output_format', ['Please revise your code to ensure the output adheres to the {format} format.', 'Kindly update your code to generate output strictly in the {format} format.', 'Could you modify your code to guarantee the output conforms to the {format} format?', 'We recommend refactoring your code to produce output in the {format} format.', 'It would be appreciated if you could adjust your code to output data in the {format} format.']),
    ('global_variable', ['Please revise your code to use at least one global variable.', 'Kindly update your code to include a global variable in the implementation.', 'Could you modify your code to ensure it contains a global variable?', 'We recommend refactoring your code to integrate a global variable into the logic.', 'It would be appreciated if you could adjust your code to include a global variable.']),
    ('global_variable_not', ['Please revise your code to exclude any global variables in the implementation.', 'Kindly update your code to ensure it does not contain any global variables.', 'Could you modify your code to avoid using global variables entirely?', 'We recommend refactoring your code to remove any global variables from the logic.', 'It would be appreciated if you could adjust your code to omit global variables.']),
    ('constant_variable', ['Please revise your code to use at least one constant variable.', 'Kindly update your code to include a constant variable in the implementation.', 'Could you modify your code to ensure it contains a constant variable?', 'We recommend refactoring your code to integrate a constant variable into the logic.', 'It would be appreciated if you could adjust your code to include a constant variable.']),
    ('constant_variable_not', ['Please revise your code to exclude any constant variables in the implementation.', 'Kindly update your code to ensure it does not contain any constant variables.', 'Could you modify your code to avoid using constant variables entirely?', 'We recommend refactoring your code to remove any constant variables from the logic.', 'It would be appreciated if you could adjust your code to omit constant variables.']),
    ('code_lines', ['Please revise your code to contain at most {number} lines of code.', 'Kindly update your code to limit the number of lines to {number}.', 'Could you modify your code to ensure it does not exceed {number} lines?', 'We recommend refactoring your code to reduce the number of lines to {number}.', 'It would be appreciated if you could adjust your code to have at most {number} lines.']),
    ('function_parameters_max', ['All Your function should have at most {number} parameters.', 'Please revise your code to ensure that all functions have at most {number} parameters.', 'Kindly update your code to limit the number of parameters in each function to {number}.', 'Could you modify your code to ensure that no function has more than {number} parameters?', 'We recommend refactoring your code to restrict all functions to a maximum of {number} parameters.', 'It would be appreciated if you could adjust your code to ensure that all functions have at most {number} parameters.']),
    ('function_parameters_min', ['All Your function should have at least {number} parameters.', 'Please revise your code to ensure that all functions have at least {number} parameters.', 'Kindly update your code to require a minimum of {number} parameters in each function.', 'Could you modify your code to ensure that no function has fewer than {number} parameters?', 'We recommend refactoring your code to restrict all functions to a minimum of {number} parameters.', 'It would be appreciated if you could adjust your code to ensure that all functions have at least {number} parameters.'])
]

class CodeEvaluator:
    """代码评估类，用于对不同语言的代码进行功能和结构评估"""
    
    def __init__(self):
        """初始化评估器"""
        # 将语言映射到对应的评估模块
        self.evaluators = {
            "python": evaluation_py,
            "c++": evaluation_c,
            "java": evaluation_java
        }
        
        # 语言别名，用于标准化
        self.language_aliases = {
            "python": "python",
            "py": "python",
            "c++": "c++", 
            "cpp": "c++",
            "c": "c++",  # C和C++使用相同的评估器
            "java": "java"
        }
    
    def normalize_language(self, language: str) -> str:
        """标准化语言名称"""
        if not language:
            return "python"  # 默认为Python
        
        language = language.lower()
        return self.language_aliases.get(language, language)
    
    def _get_file_extension(self, language):
        """
        获取给定编程语言的文件扩展名。
        """
        extension_map = {
            "python": "py",
            "javascript": "js",
            "java": "java",
            "c++": "cpp",
            "cpp": "cpp",
            "c": "c",
            "ruby": "rb",
            "go": "go",
            "php": "php",
            "swift": "swift",
            "rust": "rs",
            "typescript": "ts",
            "kotlin": "kt",
            "csharp": "cs",
            "c#": "cs",
            # 根据需要添加更多映射
        }
        
        # 使用小写语言名称与映射表匹配
        normalized_language = language.lower()
        
        # 返回映射的扩展名或默认值
        return extension_map.get(normalized_language, "txt")
    
    def run_code(self, code: str, language: str, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """运行代码并评估结果"""
        import tempfile
        import json
        import subprocess
        import sys
        import os
        import re
        import traceback
        import threading
        import time
        
        # 添加全局超时控制
        global_result = {"success": False, "error": "执行超时（超过60秒）", "results": []}
        global_process_finished = threading.Event()
        
        def run_with_timeout():
            nonlocal global_result
            try:
                norm_language = self.normalize_language(language)
                
                # 检查是否有对应语言的评估器
                if norm_language not in self.evaluators or self.evaluators[norm_language] is None:
                    global_result = {
                        "success": False, 
                        "error": f"不支持的语言: {language}",
                        "results": []
                    }
                    return
                
                # 获取评估器模块文件路径
                current_dir = os.path.dirname(os.path.abspath(__file__))
                evaluator_paths = {
                    # 修改前: os.path.join(current_dir, "evaluation.py") 等
                    # 修改后:
                    "python": os.path.join(current_dir, "evaluation.py"),
                    "c++": os.path.join(current_dir, "evaluation_c.py"),
                    "java": os.path.join(current_dir, "evaluation_java.py")
                }
                
                # 准备测试用例
                standardized_test_cases = []
                for tc in test_cases:
                    # 处理不同格式的测试用例
                    if isinstance(tc, dict):
                        if 'input' in tc and 'output' in tc:
                            standardized_test_cases.append(tc)
                        elif 'inputs' in tc and 'outputs' in tc:
                            standardized_test_cases.append({
                                'input': tc['inputs'],
                                'output': tc['outputs']
                            })
                    elif isinstance(tc, (list, tuple)) and len(tc) >= 2:
                        standardized_test_cases.append({
                            'input': tc[0],
                            'output': tc[1]
                        })
                
                try:
                    # 定义固定的文件路径
                    code_dir = "code_files"  # 可以根据需要修改为您想要的路径
                    # 确保目录存在
                    if not os.path.exists(code_dir):
                        os.makedirs(code_dir)

                    # 将代码保存到固定文件
                    code_file = os.path.join(code_dir, f"code.{self._get_file_extension(norm_language)}")
                    with open(code_file, 'w', encoding='utf-8') as f:
                        f.write(code)

                    # 将测试用例保存到固定文件
                    test_cases_file = os.path.join(code_dir, "test_cases.json")
                    with open(test_cases_file, 'w', encoding='utf-8') as f:
                        json.dump(standardized_test_cases, f)
                    
                    # 特殊处理C/C++评估器
                    if norm_language == "c++":
                        # 获取评估器路径
                        evaluator_path = evaluator_paths["c++"]
                        
                        cmd = [
                            sys.executable,  # 当前Python解释器路径
                            evaluator_path,
                            code_file,
                            "--test-cases-file", test_cases_file
                        ]
                        
                        # 执行命令，添加超时限制
                        process = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            check=False,
                            timeout=60  # 设置30秒超时
                        )

                        # 解析结果
                        if process.returncode == 0:
                            # 尝试从输出中提取JSON结果
                            output_lines = process.stdout.strip().split("\n")
                            results_data = None
                            
                            for line in output_lines:
                                if line.startswith("{") and line.endswith("}"):
                                    try:
                                        results_data = json.loads(line)
                                        break
                                    except:
                                        pass
                            
                            if results_data:
                                global_result = results_data
                            else:
                                # 如果没有找到JSON格式结果，手动构建结果
                                all_passed = "所有测试通过" in process.stdout
                                global_result = {
                                    "success": all_passed,
                                    "results": [{"correct": all_passed, "output": process.stdout}],
                                    "error": None
                                }
                        else:
                            # 执行失败
                            global_result = {
                                "success": False,
                                "results": [],
                                "error": process.stderr,
                                "exception": process.stderr
                            }
                        
                    elif norm_language == "python":
                        # 获取评估器路径
                        evaluator_path = evaluator_paths["python"]
                        
                        # 构建命令行
                        cmd = [
                            sys.executable,  # 当前Python解释器路径
                            evaluator_path,
                            code_file,
                            "--test-cases-file", test_cases_file
                        ]
                        
                        # 执行命令，添加超时限制
                        process = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            check=False,
                            timeout=90  # 设置30秒超时
                        )
                        
                        # 解析结果
                        if process.returncode == 0:
                            # 尝试从输出中提取JSON结果
                            output_lines = process.stdout.strip().split("\n")
                            results_data = None
                            
                            for line in output_lines:
                                if line.startswith("{") and line.endswith("}"):
                                    try:
                                        results_data = json.loads(line)
                                        break
                                    except:
                                        pass
                            
                            if results_data:
                                global_result = results_data
                            else:
                                # 如果没有找到JSON格式结果，手动构建结果
                                all_passed = "所有测试通过" in process.stdout
                                global_result = {
                                    "success": all_passed,
                                    "results": [{"correct": all_passed, "output": process.stdout}],
                                    "error": None
                                }
                        else:
                            # 执行失败
                            global_result = {
                                "success": False,
                                "results": [],
                                "error": process.stderr,
                                "exception": process.stderr
                            }
                    
                    elif norm_language == "java":
                        # 获取评估器路径
                        evaluator_path = evaluator_paths["java"]
                        
                        # 构建命令行
                        cmd = [
                            sys.executable,  # 当前Python解释器路径
                            evaluator_path,
                            code_file,
                            "--test-cases-file", test_cases_file
                        ]
                        
                        # 执行命令，添加超时限制
                        process = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            check=False,
                            timeout=90  # 设置30秒超时
                        )
                        
                        # 解析结果
                        if process.returncode == 0:
                            # 尝试从输出中提取JSON结果
                            output_lines = process.stdout.strip().split("\n")
                            results_data = None
                            
                            for line in output_lines:
                                if line.startswith("{") and line.endswith("}"):
                                    try:
                                        results_data = json.loads(line)
                                        break
                                    except:
                                        pass
                            
                            if results_data:
                                global_result = results_data
                            else:
                                # 如果没有找到JSON格式结果，手动构建结果
                                all_passed = "所有测试通过" in process.stdout
                                global_result = {
                                    "success": all_passed,
                                    "results": [{"correct": all_passed, "output": process.stdout}],
                                    "error": None
                                }
                        else:
                            # 执行失败
                            global_result = {
                                "success": False,
                                "results": [],
                                "error": process.stderr,
                                "exception": process.stderr
                            }
                
                except subprocess.TimeoutExpired:
                    global_result = {
                        "success": False,
                        "error": "评估器超时（超过30秒）",
                        "results": [{"correct": False, "output": "评估器执行超时", "error": "执行超时"}]
                    }
                except Exception as e:
                    global_result = {
                        "success": False,
                        "error": f"运行代码时出错: {str(e)}",
                        "results": [],
                        "exception": traceback.format_exc()
                    }
                    
                # 标记进程已完成
                global_process_finished.set()
                
            except Exception as e:
                global_result = {
                    "success": False,
                    "error": f"运行代码时出错: {str(e)}",
                    "results": [],
                    "exception": traceback.format_exc()
                }
                global_process_finished.set()
        
        # 创建并启动执行线程
        execution_thread = threading.Thread(target=run_with_timeout)
        execution_thread.daemon = True
        execution_thread.start()
        
        # 等待执行完成或超时
        if not global_process_finished.wait(timeout=90):  # 全局超时60秒
            print("警告: 代码评估总时间超过60秒，强制终止")
            return {
                "success": False,
                "error": "执行超时（总评估时间超过60秒）",
                "results": [{"correct": False, "output": "评估时间超过60秒", "error": "总评估超时"}]
            }
        
        return global_result
        
    def evaluate_variable_include(self, code: str, variable_name: str, language: str) -> bool:
        """检查代码是否包含指定的变量名"""
        language = self.normalize_language(language)
        if language == "python":
            try:
                tree = ast.parse(code)
                variables = set()
                
                # 提取所有变量名
                for node in ast.walk(tree):
                    # 变量赋值
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                        variables.add(node.id)
                    # 函数参数
                    elif isinstance(node, ast.arg):
                        variables.add(node.arg)
                    # 列表推导式变量
                    elif isinstance(node, ast.ListComp):
                        for generator in node.generators:
                            if isinstance(generator.target, ast.Name):
                                variables.add(generator.target.id)
                    # with语句变量
                    elif isinstance(node, ast.withitem) and isinstance(node.optional_vars, ast.Name):
                        variables.add(node.optional_vars.id)
                    # except语句变量
                    elif isinstance(node, ast.ExceptHandler) and node.name:
                        variables.add(node.name)
                    # 导入别名
                    elif isinstance(node, ast.alias) and node.asname:
                        variables.add(node.asname)
                    
                #print(variables)
                #print(variable_name)
                return variable_name in variables
                
            except Exception as e:
                print(f"Python变量检测错误: {str(e)}")
                return False
        
        elif language == "java":
            try:
                import javalang
                tree = javalang.parse.parse(code)
                variables = set()
                
                # 收集变量声明
                for path, node in tree.filter(javalang.tree.VariableDeclarator):
                    variables.add(node.name)
                
                # 收集方法参数
                for path, node in tree.filter(javalang.tree.FormalParameter):
                    variables.add(node.name)
                    
                # 收集异常处理参数
                for path, node in tree.filter(javalang.tree.CatchClauseParameter):
                    variables.add(node.name)
                    
                # 收集for循环变量
                for path, node in tree.filter(javalang.tree.ForControl):
                    if hasattr(node, 'variable') and node.variable:
                        for var in node.variable.declarators:
                            variables.add(var.name)
                
                print(f"Java 变量: {variables}")
                print(f"Java 检查: {variable_name}")
                
                return variable_name in variables
            except Exception as e:
                print(f"Java变量检测错误: {str(e)}")
                return False
                
        elif language == "c++":
            try:
                # 首先移除注释和字符串字面量以避免误判
                code_no_comments = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
                code_no_comments = re.sub(r'/\*.*?\*/', '', code_no_comments, flags=re.DOTALL)
                code_no_comments = re.sub(r'"[^"]*"', '', code_no_comments)
                code_no_comments = re.sub(r"'[^']*'", '', code_no_comments)
                
                # 变量声明模式扩展
                variables = set()
                
                # 1. 标准变量声明
                c_types = '(int|char|bool|float|double|void|' + \
                        'int8_t|uint8_t|int16_t|uint16_t|int32_t|uint32_t|int64_t|uint64_t|' + \
                        'unsigned int|signed int|long int|short int|long long|unsigned long|signed long|' + \
                        'unsigned char|signed char|long double|' + \
                        'string|vector|array|map|set|list|deque|queue|stack|pair|tuple|' + \
                        'size_t|ptrdiff_t|auto|wchar_t)'
                
                # 简单声明 (类型 变量)
                var_decls = re.findall(r'\b' + c_types + r'\s+([a-zA-Z_][a-zA-Z0-9_]*)\b', code_no_comments)
                variables.update(var_decls)
                
                # 指针和引用
                ptr_decls = re.findall(r'\b' + c_types + r'\s*[\*&]+\s*([a-zA-Z_][a-zA-Z0-9_]*)\b', code_no_comments)
                variables.update(ptr_decls)
                
                # 多变量声明 (int a, b, c)
                multi_decls = re.findall(r'\b' + c_types + r'\s+[a-zA-Z_][a-zA-Z0-9_]*(?:\s*,\s*([a-zA-Z_][a-zA-Z0-9_]*))+\b', 
                                    code_no_comments)
                for multi_decl in multi_decls:
                    comma_vars = re.findall(r',\s*([a-zA-Z_][a-zA-Z0-9_]*)', multi_decl)
                    variables.update(comma_vars)
                
                # 2. 函数参数
                for match in re.finditer(r'\([^)]*\)', code_no_comments):
                    param_str = match.group(0)[1:-1]  # 移除括号
                    # 匹配参数声明
                    params = re.findall(r'\b' + c_types + r'\s+([a-zA-Z_][a-zA-Z0-9_]*)\b', param_str)
                    variables.update(params)
                    
                # 3. for循环变量
                for_vars = re.findall(r'for\s*\(\s*' + c_types + r'\s+([a-zA-Z_][a-zA-Z0-9_]*)\b', code_no_comments)
                variables.update(for_vars)
                
                print(f"C++ 变量: {variables}")
                print(f"C++ 检查: {variable_name}")
                
                return variable_name in variables
            except Exception as e:
                print(f"C++ 变量检测错误: {e}")
                return False
    
    def evaluate_variable_number(self, code: str, variable_name: str, position: int, language: str) -> bool:
        """检查变量是否在指定位置"""
        language = self.normalize_language(language)
        if language == "python":
            try:
                tree = ast.parse(code)
                variables = []
                
                # 按顺序获取变量声明
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                variables.append(target.id)
                
                # 检查变量是否在正确位置（1索引）
                return (position-1 < len(variables) and variables[position-1] == variable_name)
            except:
                return False
        
        elif language == "java":
            try:
                import javalang
                tree = javalang.parse.parse(code)
                variables = []
                
                # 收集变量声明
                for _, node in tree.filter(javalang.tree.VariableDeclarator):
                    variables.append(node.name)
                
                # 检查位置
                return (position-1 < len(variables) and variables[position-1] == variable_name)
            except:
                return False
                
        elif language == "c++":
            # 使用完整的C++类型列表
            c_types = (
                # 基本类型
                'int|char|bool|float|double|void|'
                # 特定大小类型
                'int8_t|uint8_t|int16_t|uint16_t|int32_t|uint32_t|int64_t|uint64_t|'
                # 修饰类型
                'unsigned int|signed int|long int|short int|long long|unsigned long|signed long|'
                'unsigned char|signed char|long double|'
                # 常见标准类型
                'string|vector|array|map|set|list|deque|queue|stack|pair|tuple|'
                # 其他常见类型
                'size_t|ptrdiff_t|auto|wchar_t'
            )
            var_declarations = re.findall(r'\b(?:' + c_types + r')\s+([a-zA-Z_][a-zA-Z0-9_]*)\b', code)
            return (position-1 < len(var_declarations) and var_declarations[position-1] == variable_name)
        
        return False
    
    def evaluate_variable_type(self, code: str, position: int, var_type: str, language: str) -> bool:
        """检查指定位置的变量是否为指定类型"""
        language = self.normalize_language(language)
        if language == "python":
            try:
                tree = ast.parse(code)
                variables = []
                
                # 寻找带类型注解的变量声明
                for node in ast.walk(tree):
                    if isinstance(node, ast.AnnAssign):  # 类型注解赋值
                        if isinstance(node.target, ast.Name):
                            var_name = node.target.id
                            if isinstance(node.annotation, ast.Name):
                                annotation = node.annotation.id
                                variables.append((var_name, annotation))
                            elif isinstance(node.annotation, ast.Subscript):
                                # 处理如List[int]这样的情况
                                if isinstance(node.annotation.value, ast.Name):
                                    annotation = node.annotation.value.id
                                    variables.append((var_name, annotation))
                
                # 对于没有类型注解的变量，从值推断类型
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                var_name = target.id
                                if isinstance(node.value, ast.Constant):
                                    if isinstance(node.value.value, int):
                                        variables.append((var_name, "int"))
                                    elif isinstance(node.value.value, float):
                                        variables.append((var_name, "float"))
                                    elif isinstance(node.value.value, str):
                                        variables.append((var_name, "str"))
                                    elif node.value.value in (True, False):
                                        variables.append((var_name, "bool"))
                                    elif node.value.value is None:
                                        variables.append((var_name, "None"))
                                elif isinstance(node.value, ast.List):
                                    variables.append((var_name, "list"))
                                elif isinstance(node.value, ast.Dict):
                                    variables.append((var_name, "dict"))
                
                # 检查位置上的变量是否为正确类型
                if position-1 < len(variables):
                    actual_type = variables[position-1][1].lower()
                    return actual_type == var_type.lower()
                return False
            except Exception as e:
                print(f"Python类型评估错误: {e}")
                return False
        
        elif language == "java":
            try:
                import javalang
                tree = javalang.parse.parse(code)
                variables = []
                
                # 收集变量声明及其类型
                for _, field_decl in tree.filter(javalang.tree.FieldDeclaration):
                    for declarator in field_decl.declarators:
                        variables.append((declarator.name, field_decl.type.name))
                
                # 也检查局部变量声明
                for _, local_var in tree.filter(javalang.tree.LocalVariableDeclaration):
                    for declarator in local_var.declarators:
                        variables.append((declarator.name, local_var.type.name))
                
                # 检查位置
                if position-1 < len(variables):
                    actual_type = variables[position-1][1].lower()
                    return actual_type == var_type.lower()
                return False
            except Exception as e:
                print(f"Java类型评估错误: {e}")
                return False
                
        elif language == "c++":
            # 使用完整的C++类型列表
            c_types = (
                # 基本类型
                'int|char|bool|float|double|void|'
                # 特定大小类型
                'int8_t|uint8_t|int16_t|uint16_t|int32_t|uint32_t|int64_t|uint64_t|'
                # 修饰类型
                'unsigned int|signed int|long int|short int|long long|unsigned long|signed long|'
                'unsigned char|signed char|long double|'
                # 常见标准类型
                'string|vector|array|map|set|list|deque|queue|stack|pair|tuple|'
                # 其他常见类型
                'size_t|ptrdiff_t|auto|wchar_t'
            )
            var_declarations = re.findall(r'\b(' + c_types + r')\s+([a-zA-Z_][a-zA-Z0-9_]*)\b', code)
            if position-1 < len(var_declarations):
                actual_type = var_declarations[position-1][0].lower()
                return actual_type == var_type.lower()
            return False
        
        return False
    
    def evaluate_loop_presence(self, code: str, loop_type: str, should_exist: bool, language: str) -> bool:
        """检查代码中是否存在指定类型的循环"""
        language = self.normalize_language(language)
        if language == "python":
            try:
                tree = ast.parse(code)
                has_loop = False
                
                for node in ast.walk(tree):
                    if loop_type == "for" and isinstance(node, ast.For):
                        has_loop = True
                        break
                    elif loop_type == "while" and isinstance(node, ast.While):
                        has_loop = True
                        break
                
                return has_loop == should_exist
            except:
                return False
        
        elif language == "java":
            try:
                import javalang
                tree = javalang.parse.parse(code)
                has_loop = False
                
                if loop_type == "for":
                    for _, node in tree.filter((javalang.tree.ForStatement, javalang.tree.ForControl)):
                        has_loop = True
                        break
                elif loop_type == "while":
                    for _, node in tree.filter(javalang.tree.WhileStatement):
                        has_loop = True
                        break
                
                return has_loop == should_exist
            except:
                return False
                
        elif language == "c++":
            try:
                # 首先移除注释和字符串字面量以避免误判
                # 移除单行注释
                code_no_comments = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
                # 移除多行注释
                code_no_comments = re.sub(r'/\*.*?\*/', '', code_no_comments, flags=re.DOTALL)
                # 移除字符串字面量
                code_no_comments = re.sub(r'"[^"]*"', '', code_no_comments)
        
                has_loop = False
                if loop_type == "for":
                    # 匹配传统for循环和基于范围的for循环
                    has_for_loop = bool(re.search(r'\bfor\s*\(', code_no_comments))
                    has_range_for = bool(re.search(r'\bfor\s*\([^)]*\s*:\s*', code_no_comments))
                    has_loop = has_for_loop or has_range_for
                elif loop_type == "while":
                    # 匹配while和do-while循环
                    has_while_loop = bool(re.search(r'\bwhile\s*\(', code_no_comments))
                    has_do_while_loop = bool(re.search(r'\bdo\s*{.*?}\s*while\s*\(', code_no_comments, re.DOTALL))
                    has_loop = has_while_loop or has_do_while_loop
        
                return has_loop == should_exist
            except:
                return False
        
        return False
    
    def evaluate_if_presence(self, code: str, should_exist: bool, language: str) -> bool:
        """检查代码中是否存在if语句"""
        language = self.normalize_language(language)
        if language == "python":
            try:
                tree = ast.parse(code)
                has_if = any(isinstance(node, ast.If) for node in ast.walk(tree))
                return has_if == should_exist
            except:
                return False
        
        elif language == "java":
            try:
                import javalang
                tree = javalang.parse.parse(code)
                has_if = False
                for _, node in tree.filter(javalang.tree.IfStatement):
                    has_if = True
                    break
                return has_if == should_exist
            except:
                return False
                
        elif language == "c++":
            try:
                # 首先移除注释和字符串字面量以避免误判
                code_no_comments = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
                code_no_comments = re.sub(r'/\*.*?\*/', '', code_no_comments, flags=re.DOTALL)
                code_no_comments = re.sub(r'"[^"]*"', '', code_no_comments)
                
                has_if = bool(re.search(r'\bif\s*\(', code_no_comments))
                return has_if == should_exist
            except:
                return False
        
        return False
    
    def evaluate_function_count(self, code: str, count: int, language: str) -> bool:
        """检查代码中是否包含指定数量的函数"""
        language = self.normalize_language(language)
        if language == "python":
            try:
                tree = ast.parse(code)
                function_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
                return function_count == count
            except:
                return False
        
        elif language == "java":
            try:
                import javalang
                tree = javalang.parse.parse(code)
                method_count = sum(1 for _, node in tree.filter(javalang.tree.MethodDeclaration))
                return method_count == count
            except:
                return False
                
        elif language == "c++":
            try:
                # 首先移除注释和字符串字面量以避免误判
                code_no_comments = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
                code_no_comments = re.sub(r'/\*.*?\*/', '', code_no_comments, flags=re.DOTALL)
                code_no_comments = re.sub(r'"[^"]*"', '', code_no_comments)
        
                # 全面的C++类型列表，用于返回值
                c_types = (
                    # 基本类型
                    'int|char|bool|float|double|void|'
                    # 特定大小类型
                    'int8_t|uint8_t|int16_t|uint16_t|int32_t|uint32_t|int64_t|uint64_t|'
                    # 修饰类型
                    'unsigned int|signed int|long int|short int|long long|unsigned long|signed long|'
                    'unsigned char|signed char|long double|'
                    # 常见标准类型
                    'string|vector|array|map|set|list|deque|queue|stack|pair|tuple|'
                    # 其他常见类型
                    'size_t|ptrdiff_t|auto|wchar_t'
                )
        
                # 统计各种形式的函数声明
        
                # 常规带返回类型的函数（大括号在同一行）
                regular_functions = re.findall(r'\b(?:' + c_types + r')\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*{', code_no_comments)
        
                # 常规带返回类型的函数（大括号在下一行）
                next_line_functions = re.findall(r'\b(?:' + c_types + r')\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*(?:\w*\s*)*\n\s*{', code_no_comments)
        
                # 构造函数声明（无返回类型）
                constructors = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)::\1\s*\([^)]*\)\s*{', code_no_comments)
        
                # 析构函数
                destructors = re.findall(r'\b~([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*{', code_no_comments)
        
                # 模板函数
                template_functions = re.findall(r'template\s*<[^>]*>\s*(?:' + c_types + r')\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*{', code_no_comments)
        
                # 运算符重载
                operator_overloads = re.findall(r'operator\s*(?:\+|\-|\*|\/|\%|\^|\&|\||\~|\!|\=|\<|\>|\+=|\-=|\*=|\/=|\%=|\^=|\&=|\|=|\<\<|\>\>|\<\<=|\>\>=|\=\=|\!=|\<\=|\>\=|\<\<|\>\>|\+\+|\-\-|\->|\(\)|\[\])\s*\([^)]*\)\s*{', code_no_comments)
        
                # 计算函数总数
                function_count = len(regular_functions) + len(next_line_functions) + len(constructors) + len(destructors) + len(template_functions) + len(operator_overloads)
        
                return function_count == count
            except Exception as e:
                print(f"C++函数计数错误: {e}")
                return False
        
        return False
    
    def evaluate_function_not(self, code: str, language: str) -> bool:
        """检查代码中是否不包含函数"""
        language = self.normalize_language(language)
        if language == "python":
            try:
                tree = ast.parse(code)
                function_count = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))
                return function_count == 0
            except Exception as e:
                print(f"Python函数检测错误: {e}")
                return False
        
        elif language == "java":
            try:
                import javalang
                tree = javalang.parse.parse(code)
                method_count = sum(1 for _, node in tree.filter(javalang.tree.MethodDeclaration))
                return method_count == 0
            except Exception as e:
                print(f"Java函数检测错误: {e}")
                return False
                
        elif language == "c++":
            try:
                # 移除注释和字符串字面量以避免误判
                code_no_comments = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
                code_no_comments = re.sub(r'/\*.*?\*/', '', code_no_comments, flags=re.DOTALL)
                code_no_comments = re.sub(r'"[^"]*"', '', code_no_comments)
                code_no_comments = re.sub(r"'[^']*'", '', code_no_comments)
        
                # 正则表达式模式集，用于检测各种形式的函数
                patterns = [
                    # 标准函数，大括号同一行
                    r'\b(?:int|char|bool|float|double|void|[a-zA-Z_][a-zA-Z0-9_:]*)\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)\s*{',
                    # 标准函数，大括号另起一行
                    r'\b(?:int|char|bool|float|double|void|[a-zA-Z_][a-zA-Z0-9_:]*)\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)\s*(?:const|override|final|noexcept)?\s*(?:\n|\r\n?)\s*{',
                    # 构造函数
                    r'\b[a-zA-Z_][a-zA-Z0-9_]*\s*::\s*[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)\s*(?::\s*[^{]*)?{',
                    # 析构函数
                    r'\b~[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)\s*{',
                    # 运算符重载
                    r'operator\s*(?:\+|\-|\*|\/|%|\^|\&|\||\~|\!|\=|\<|\>|<<|>>|\+=|\-=|\*=|\/=|%=|\^=|\&=|\|=|\<\<=|\>\>=|\=\=|\!=|\<\=|\>\=|\[\]|\(\)|\-\>|\-\>\*)\s*\([^)]*\)\s*{',
                    # Lambda 函数
                    r'\[\s*(?:[a-zA-Z0-9_,=&\*\s]*)\]\s*(?:\([^)]*\))?\s*(?:->.*?)?\s*\{'
                ]
        
                # 检查是否匹配任何函数模式
                for pattern in patterns:
                    if re.search(pattern, code_no_comments, re.MULTILINE):
                        return False  # 找到了函数
        
                return True  # 没有找到函数
            except Exception as e:
                print(f"C++函数检测错误: {e}")
                return False
        
        return False
    
    def evaluate_class_count(self, code: str, count: int, language: str) -> bool:
        """检查代码中是否包含指定数量的类"""
        language = self.normalize_language(language)
        if language == "python":
            try:
                tree = ast.parse(code)
                class_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
                return class_count == count
            except:
                return False
        
        elif language == "java":
            try:
                import javalang
                tree = javalang.parse.parse(code)
                class_count = sum(1 for _, node in tree.filter(javalang.tree.ClassDeclaration))
                return class_count == count
            except:
                return False
                
        elif language == "c++":
            try:
                # 首先移除注释和字符串字面量以避免误判
                code_no_comments = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
                code_no_comments = re.sub(r'/\*.*?\*/', '', code_no_comments, flags=re.DOTALL)
                code_no_comments = re.sub(r'"[^"]*"', '', code_no_comments)
        
                # 统计不同形式的类声明
        
                # 常规类声明
                regular_classes = re.findall(r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:{|:|$|\n)', code_no_comments)
        
                # 模板类声明
                template_classes = re.findall(r'template\s*<[^>]*>\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)', code_no_comments)
        
                # 也统计struct声明（在C++中与类本质相同）
                struct_classes = re.findall(r'\bstruct\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:{|:|$|\n)', code_no_comments)
        
                # 过滤前向声明（以分号结尾而没有大括号）
                forward_decls = re.findall(r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*;', code_no_comments)
        
                # 计算总数（排除前向声明）
                real_classes = set(regular_classes + template_classes + struct_classes) - set(forward_decls)
                class_count = len(real_classes)
        
                return class_count == count
            except:
                return False
        
        return False
    
    def evaluate_class_not(self, code: str, language: str) -> bool:
        """检查代码中是否不包含类"""
        language = self.normalize_language(language)
        if language == "python":
            try:
                tree = ast.parse(code)
                class_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
                return class_count == 0
            except Exception as e:
                print(f"Python类检测错误: {e}")
                return False
        
        elif language == "java":
            try:
                import javalang
                tree = javalang.parse.parse(code)
                class_count = sum(1 for _, node in tree.filter(javalang.tree.ClassDeclaration))
                # 也检查接口声明
                interface_count = sum(1 for _, node in tree.filter(javalang.tree.InterfaceDeclaration))
                return class_count == 0 and interface_count == 0
            except Exception as e:
                print(f"Java类检测错误: {e}")
                return False
                
        elif language == "c++":
            try:
                # 首先移除注释和字符串字面量以避免误判
                code_no_comments = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
                code_no_comments = re.sub(r'/\*.*?\*/', '', code_no_comments, flags=re.DOTALL)
                code_no_comments = re.sub(r'"[^"]*"', '', code_no_comments)
                code_no_comments = re.sub(r"'[^']*'", '', code_no_comments)
        
                # 检查各种类声明模式
                patterns = [
                    # 类声明 - 大括号在同一行
                    r'\b(class|struct)\s+[a-zA-Z_][a-zA-Z0-9_]*\s*(?:\s*:\s*(?:public|protected|private)\s+[a-zA-Z_][a-zA-Z0-9_:]*\s*)?\s*{',
                    # 类声明 - 大括号在下一行
                    r'\b(class|struct)\s+[a-zA-Z_][a-zA-Z0-9_]*\s*(?:\s*:\s*(?:public|protected|private)\s+[a-zA-Z_][a-zA-Z0-9_:]*\s*)?\s*(?:\n|\r\n?)\s*{',
                    # 模板类声明
                    r'template\s*<[^>]*>\s*(?:class|struct)\s+[a-zA-Z_][a-zA-Z0-9_]*'
                ]
        
                # 过滤前向声明
                forward_decls = re.findall(r'\b(?:class|struct)\s+[a-zA-Z_][a-zA-Z0-9_]*\s*;', code_no_comments)
                
                # 检查是否有实际的类定义（非前向声明）
                for pattern in patterns:
                    if re.search(pattern, code_no_comments):
                        return False  # 找到了类
        
                return True  # 没有找到类
            except Exception as e:
                print(f"C++类检测错误: {e}")
                return False
        
        return False
    
    def evaluate_has_no_comments(self, code: str, language: str) -> bool:
        """检查代码中是否不含注释"""
        language = self.normalize_language(language)
        
        # 先移除字符串字面量以避免误判
        if language == "python":
            # 移除三引号字符串和常规字符串
            code_no_strings = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
            code_no_strings = re.sub(r"'''.*?'''", '', code_no_strings, flags=re.DOTALL)
            code_no_strings = re.sub(r'"[^"]*"', '', code_no_strings)
            code_no_strings = re.sub(r"'[^']*'", '', code_no_strings)
            
            # 检查注释
            has_comment = bool(re.search(r'#', code_no_strings))
            return not has_comment
        
        elif language in ["java", "c++"]:
            # 移除字符串字面量
            code_no_strings = re.sub(r'"[^"]*"', '', code)
            
            # 检查单行和多行注释
            has_single_line_comment = bool(re.search(r'//', code_no_strings))
            has_multi_line_comment = bool(re.search(r'/\*.*?\*/', code_no_strings, flags=re.DOTALL))
            
            return not (has_single_line_comment or has_multi_line_comment)
        
        return False
    
    def evaluate_has_comments(self, code: str, language: str) -> bool:
        """检查代码中是否包含注释"""
        language = self.normalize_language(language)
        
        if language == "python":
            # 先检查是否存在 # 注释
            code_no_strings = re.sub(r'"[^"]*"', '', code)  # 移除普通双引号字符串
            code_no_strings = re.sub(r"'[^']*'", '', code_no_strings)  # 移除普通单引号字符串
            if re.search(r'#', code_no_strings):
                return True
            
            # 检查是否存在文档注释（docstrings）
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    # 检查模块、类和函数的文档字符串
                    if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and ast.get_docstring(node):
                        return True
            except:
                # 如果代码解析失败，回退到简单的正则表达式检测
                # 检查可能的文档字符串模式
                docstring_patterns = [
                    r'^\s*[\']{3}[\s\S]*?[\']{3}',  # 模块级文档字符串
                    r'^\s*[\"]{3}[\s\S]*?[\"]{3}',
                    r'def\s+\w+\s*\([^)]*\)\s*:\s*\n\s*[\']{3}[\s\S]*?[\']{3}',  # 函数文档字符串
                    r'def\s+\w+\s*\([^)]*\)\s*:\s*\n\s*[\"]{3}[\s\S]*?[\"]{3}',
                    r'class\s+\w+[^:]*:\s*\n\s*[\']{3}[\s\S]*?[\']{3}',  # 类文档字符串
                    r'class\s+\w+[^:]*:\s*\n\s*[\"]{3}[\s\S]*?[\"]{3}'
                ]
                for pattern in docstring_patterns:
                    if re.search(pattern, code, re.MULTILINE):
                        return True
                        
            return False
        
        elif language in ["java", "c++"]:
            # 移除字符串字面量
            code_no_strings = re.sub(r'"[^"]*"', '', code)
            code_no_strings = re.sub(r"'[^']*'", '', code_no_strings)
            
            # 检查单行和多行注释
            has_single_line_comment = bool(re.search(r'//', code_no_strings))
            has_multi_line_comment = bool(re.search(r'/\*.*?\*/', code_no_strings, flags=re.DOTALL))
            
            return has_single_line_comment or has_multi_line_comment
        
        return False
    
    def evaluate_built_in_only(self, code: str, language: str) -> bool:
        """检查代码是否只使用内置函数（不导入外部库）"""
        language = self.normalize_language(language)
        
        if language == "python":
            try:
                tree = ast.parse(code)
                has_imports = any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree))
                return not has_imports
            except:
                return False
        
        elif language == "java":
            # 检查import语句
            has_imports = bool(re.search(r'\bimport\s+(?!java\.)[a-zA-Z0-9_.]+;', code))
            return not has_imports
                
        elif language == "c++":
            # 检查非标准库的include
            includes = re.findall(r'#include\s*<([^>]+)>', code)
            standard_headers = {
                'iostream', 'string', 'vector', 'map', 'set', 'algorithm', 'cmath',
                'cstdlib', 'ctime', 'cstring', 'cassert', 'queue', 'stack', 'deque'
            }
            return all(header in standard_headers for header in includes)
        
        return False
    
    def evaluate_global_variable(self, code: str, language: str) -> bool:
        """检查代码是否包含至少一个全局变量"""
        language = self.normalize_language(language)
        
        if language == "python":
            try:
                tree = ast.parse(code)
                # 在Python中，全局变量是在模块级别定义的变量
                # 获取所有函数和类定义
                func_and_class_names = set()
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        func_and_class_names.add(node.name)
                
                # 查找全局变量赋值
                global_vars = set()
                for node in tree.body:
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and target.id not in func_and_class_names:
                                global_vars.add(target.id)
                
                return len(global_vars) > 0
            except Exception as e:
                print(f"Python全局变量检测错误: {e}")
                return False
                
        elif language == "java":
            try:
                import javalang
                tree = javalang.parse.parse(code)
                
                # 在Java中查找类级别的静态字段
                for _, field_decl in tree.filter(javalang.tree.FieldDeclaration):
                    if 'static' in field_decl.modifiers:
                        return True
                
                return False
            except Exception as e:
                print(f"Java全局变量检测错误: {e}")
                return False
                
        elif language == "c++":
            try:
                # 首先移除注释和字符串字面量
                code_no_comments = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
                code_no_comments = re.sub(r'/\*.*?\*/', '', code_no_comments, flags=re.DOTALL)
                code_no_comments = re.sub(r'"[^"]*"', '', code_no_comments)
                
                # 获取所有函数定义
                func_pattern = r'\b(?:void|int|char|bool|float|double|auto|string|vector|[a-zA-Z_][a-zA-Z0-9_]*)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*{[^}]*}'
                functions = re.findall(func_pattern, code_no_comments, re.DOTALL)
                
                # 获取所有类定义
                class_pattern = r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)'
                classes = re.findall(class_pattern, code_no_comments)
                
                # 在函数和类之外查找变量声明
                lines = code_no_comments.split('\n')
                in_func_or_class = False
                brace_count = 0
                
                for line in lines:
                    # 检查是否进入函数或类定义
                    if re.search(r'[{]', line):
                        brace_count += 1
                        if brace_count == 1 and not in_func_or_class:
                            in_func_or_class = True
                    
                    # 检查是否离开函数或类定义
                    if re.search(r'[}]', line):
                        brace_count -= 1
                        if brace_count == 0:
                            in_func_or_class = False
                    
                    # 如果不在函数或类内，查找变量声明
                    if not in_func_or_class and brace_count == 0:
                        # 排除函数原型、include和using语句
                        if (not re.search(r'#include|using\s+namespace|^\s*$', line) and 
                            re.search(r'\b(?:int|char|bool|float|double|auto|string|vector|[a-zA-Z_][a-zA-Z0-9_]*)\s+[a-zA-Z_][a-zA-Z0-9_]*\s*(?:=|;)', line)):
                            return True
                
                return False
            except Exception as e:
                print(f"C++全局变量检测错误: {e}")
                return False
        
        return False

    def evaluate_no_global_variable(self, code: str, language: str) -> bool:
        """检查代码是否不包含全局变量"""
        # 直接使用evaluate_global_variable的相反结果
        return not self.evaluate_global_variable(code, language)

    def evaluate_constant_variable(self, code: str, language: str) -> bool:
        """检查代码是否包含至少一个常量变量"""
        language = self.normalize_language(language)
        
        if language == "python":
            try:
                tree = ast.parse(code)
                
                # 在Python中，常量通常是全大写的变量
                has_constant = False
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                # 检查变量名是否全大写
                                if target.id.isupper() and len(target.id) > 1:
                                    has_constant = True
                                    break
                        
                        # 另一种检查方式：检查是否使用了Final类型标注
                        if hasattr(node, 'annotation') and isinstance(node.annotation, ast.Subscript):
                            if (isinstance(node.annotation.value, ast.Name) and 
                                node.annotation.value.id == 'Final'):
                                has_constant = True
                                break
                
                return has_constant
            except Exception as e:
                print(f"Python常量检测错误: {e}")
                return False
                
        elif language == "java":
            try:
                import javalang
                tree = javalang.parse.parse(code)
                
                # 在Java中查找使用final修饰符的字段
                for _, field_decl in tree.filter(javalang.tree.FieldDeclaration):
                    if 'final' in field_decl.modifiers:
                        return True
                
                return False
            except Exception as e:
                print(f"Java常量检测错误: {e}")
                return False
                
        elif language == "c++":
            try:
                # 首先移除注释和字符串字面量
                code_no_comments = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
                code_no_comments = re.sub(r'/\*.*?\*/', '', code_no_comments, flags=re.DOTALL)
                code_no_comments = re.sub(r'"[^"]*"', '', code_no_comments)
                
                # 查找使用const关键字的变量声明
                const_pattern = r'\bconst\s+(?:int|char|bool|float|double|auto|string|vector|[a-zA-Z_][a-zA-Z0-9_]*)\s+[a-zA-Z_][a-zA-Z0-9_]*'
                has_const = bool(re.search(const_pattern, code_no_comments))
                
                # 查找使用#define定义的常量
                define_pattern = r'#define\s+([A-Z_][A-Z0-9_]*)'
                has_define = bool(re.search(define_pattern, code_no_comments))
                
                # 查找使用constexpr的常量
                constexpr_pattern = r'\bconstexpr\s+(?:int|char|bool|float|double|auto|string|[a-zA-Z_][a-zA-Z0-9_]*)\s+[a-zA-Z_][a-zA-Z0-9_]*'
                has_constexpr = bool(re.search(constexpr_pattern, code_no_comments))
                
                return has_const or has_define or has_constexpr
            except Exception as e:
                print(f"C++常量检测错误: {e}")
                return False
        
        return False

    def evaluate_function_parameters(self, code_block: str, language: str):
        coding_language = language.lower()
        parameter_counts = []

        try:
            # 移除注释和字符串，避免干扰参数列表的解析
            code_to_check = code_block
            if coding_language == "python":
                code_to_check = re.sub(r'"""[\s\S]*?"""', '', code_to_check)
                code_to_check = re.sub(r"'''[\s\S]*?'''", '', code_to_check)
                code_to_check = re.sub(r'"[^"]*"', '', code_to_check)
                code_to_check = re.sub(r"'[^']*'", '', code_to_check)
                code_to_check = re.sub(r'#.*$', '', code_to_check, flags=re.MULTILINE)
            elif coding_language in ["c++", "java"]:
                code_to_check = re.sub(r'/\*[\s\S]*?\*/', '', code_to_check)
                code_to_check = re.sub(r'//.*$', '', code_to_check, flags=re.MULTILINE)
                code_to_check = re.sub(r'"[^"]*"', '', code_to_check)
                code_to_check = re.sub(r"'[^']*'", '', code_to_check)

            # 正则表达式查找函数定义和参数列表
            if coding_language == "python":
                # 匹配 def func_name(params):
                pattern = r'\bdef\s+\w+\s*\((.*?)\)\s*:'
                matches = re.findall(pattern, code_to_check, re.DOTALL) # re.DOTALL 让 . 匹配换行符
            elif coding_language == "c++":
                # 匹配 return_type func_name(params) { 或 ; (排除 main)
                pattern = r'\b(?:void|int|float|double|char|bool|std::string|auto)\s+(\w+)(?!main\b)\s*\((.*?)\)\s*(?:{|;)'
                matches = [match[1] for match in re.findall(pattern, code_to_check, re.DOTALL)] # 只取参数部分
            elif coding_language == "java":
                # 匹配 modifier type func_name(params) { (排除 main)
                pattern = r'\b(?:public|private|protected)?\s*(?:static|final|abstract)?\s*(?:void|int|float|double|char|boolean|String|[\w<>\[\]]+)\s+(\w+)(?!main\b)\s*\((.*?)\)\s*{'
                matches = [match[1] for match in re.findall(pattern, code_to_check, re.DOTALL)] # 只取参数部分
            else:
                matches = []

            # 计算每个函数的参数数量
            for param_str in matches:
                param_str = param_str.strip()
                # 处理 C++/Java 中的 void 参数
                if coding_language in ["c++", "java"] and param_str.lower() == 'void':
                    parameter_counts.append(0)
                elif not param_str:
                    parameter_counts.append(0)
                else:
                    # 按逗号分割参数，并过滤掉可能的空字符串（例如，如果参数列表以逗号结尾）
                    # 简单处理，不考虑复杂类型中的逗号 (如 templates, function pointers)
                    params = [p for p in param_str.split(',') if p.strip()]
                    parameter_counts.append(len(params))

            # 返回最大值和最小值
            if not parameter_counts:
                return (0, 0)
            else:
                return (max(parameter_counts), min(parameter_counts))

        except re.error as e:
            print(f"Regex error in check_function_parameters: {e}")
            return (0, 0) # Return default on error
        except Exception as e:
            print(f"Error in check_function_parameters: {e}")
            return (0, 0)
    def evaluate_code_lines(self, code: str, max_lines: int) -> bool:
        """检查代码行数是否不超过指定行数"""
        # 按换行符分割代码，然后去除注释行和空行
        lines = code.strip().split('\n')
        
        # 过滤掉空行
        non_empty_lines = [line for line in lines if line.strip()]
        
        # 返回是否符合最大行数限制
        return len(non_empty_lines) <= max_lines
    
    def evaluate_requirements(self, code: str, case_type: str, params: Dict[str, Any], language: str, runtime_result) -> Dict[str, Any]:
        """评估代码是否满足case_type中指定的要求"""
        result = {"success": False, "requirement_met": False, "details": ""}
        
        try:
            if case_type == "keyword_variable_include":
                variable_name = params.get("name", "")
                #print(code)
                #print(variable_name)
                result["requirement_met"] = self.evaluate_variable_include(code, variable_name, language)
                result["details"] = f"变量 {variable_name} {'已找到' if result['requirement_met'] else '未找到'}"
                
            elif case_type == "keyword_variable_number":
                variable_name = params.get("name", "")
                position = params.get("number", 1)
                result["requirement_met"] = self.evaluate_variable_number(code, variable_name, position, language)
                result["details"] = f"变量 {variable_name} {'位于' if result['requirement_met'] else '不在'} 位置 {position}"
                
            elif case_type == "keyword_variable_type":
                position = params.get("number", 1)
                var_type = params.get("type", "")
                result["requirement_met"] = self.evaluate_variable_type(code, position, var_type, language)
                result["details"] = f"位置 {position} 的变量 {'是' if result['requirement_met'] else '不是'} {var_type} 类型"
                
            elif case_type == "keyword_for":
                result["requirement_met"] = self.evaluate_loop_presence(code, "for", True, language)
                result["details"] = f"for循环 {'已找到' if result['requirement_met'] else '未找到'}"
                
            elif case_type == "keyword_for_not":
                result["requirement_met"] = self.evaluate_loop_presence(code, "for", False, language)
                result["details"] = f"for循环 {'不存在' if result['requirement_met'] else '存在'} (符合要求)"
                
            elif case_type == "keyword_while":
                result["requirement_met"] = self.evaluate_loop_presence(code, "while", True, language)
                result["details"] = f"while循环 {'已找到' if result['requirement_met'] else '未找到'}"
                
            elif case_type == "keyword_while_not":
                result["requirement_met"] = self.evaluate_loop_presence(code, "while", False, language)
                result["details"] = f"while循环 {'不存在' if result['requirement_met'] else '存在'} (符合要求)"
                
            elif case_type == "keyword_if":
                result["requirement_met"] = self.evaluate_if_presence(code, True, language)
                result["details"] = f"if语句 {'已找到' if result['requirement_met'] else '未找到'}"
                
            elif case_type == "keyword_if_not":
                result["requirement_met"] = self.evaluate_if_presence(code, False, language)
                result["details"] = f"if语句 {'不存在' if result['requirement_met'] else '存在'} (符合要求)"
                
            elif case_type == "keyword_function":
                count = params.get("number", 1)
                result["requirement_met"] = self.evaluate_function_count(code, count, language)
                result["details"] = f"找到 {'恰好' if result['requirement_met'] else '不是恰好'} {count} 个函数"
            
            elif case_type == "keyword_function_not":
                result["requirement_met"] = self.evaluate_function_not(code, language)
                result["details"] = f"函数 {'不存在' if result['requirement_met'] else '存在'} (符合要求)"
            elif case_type == "keyword_function_one":
                result["requirement_met"] = self.evaluate_function_count(code, 1, language)
                result["details"] = f"找到 {'恰好' if result['requirement_met'] else '不是恰好'} 1 个函数"
            elif case_type == "keyword_class":
                count = params.get("number", 1)
                result["requirement_met"] = self.evaluate_class_count(code, count, language)
                result["details"] = f"找到 {'恰好' if result['requirement_met'] else '不是恰好'} {count} 个类"
            
            elif case_type == "keyword_class_not":
                result["requirement_met"] = self.evaluate_class_not(code, language)
                result["details"] = f"类 {'不存在' if result['requirement_met'] else '存在'} (符合要求)"
            elif case_type == "keyword_class_one":
                result["requirement_met"] = self.evaluate_class_count(code, 1, language)
                result["details"] = f"找到 {'恰好' if result['requirement_met'] else '不是恰好'} 1 个类"
            elif case_type == "coding_style":
                result["requirement_met"] = self.evaluate_has_no_comments(code, language)
                result["details"] = f"代码 {'没有注释' if result['requirement_met'] else '包含注释'}"
            
            elif case_type == "coding_style_include":
                result["requirement_met"] = self.evaluate_has_comments(code, language)
                result["details"] = f"代码 {'包含注释' if result['requirement_met'] else '没有注释'}"
            elif case_type == "built_in_function":
                result["requirement_met"] = self.evaluate_built_in_only(code, language)
                result["details"] = f"代码 {'仅使用内置函数' if result['requirement_met'] else '使用了外部库'}"
                
            elif case_type == "coding_language":
                # 如果代码能在指定语言中编译/运行，则该要求固有地满足
                target_language = params.get("language", "").lower()
                result["requirement_met"] = self.normalize_language(language) == self.normalize_language(target_language)
                result["details"] = f"代码使用语言: {language.capitalize()}"
                
            # 新增的四种评估类型
            elif case_type == "global_variable":
                result["requirement_met"] = self.evaluate_global_variable(code, language)
                result["details"] = f"全局变量 {'已找到' if result['requirement_met'] else '未找到'}"
                
            elif case_type == "global_variable_not":
                result["requirement_met"] = self.evaluate_no_global_variable(code, language)
                result["details"] = f"代码 {'不包含全局变量' if result['requirement_met'] else '包含全局变量'}"
                
            elif case_type == "constant_variable":
                result["requirement_met"] = self.evaluate_constant_variable(code, language)
                result["details"] = f"常量变量 {'已找到' if result['requirement_met'] else '未找到'}"
                
            elif case_type == "constant_variable_not":
                result["requirement_met"] = not self.evaluate_constant_variable(code, language)
                result["details"] = f"代码 {'不包含常量变量' if result['requirement_met'] else '包含常量变量'}"
            elif case_type == "code_lines":
                max_lines = params.get("number", 10)
                result["requirement_met"] = self.evaluate_code_lines(code, max_lines)
                result["details"] = f"代码行数 {'不超过' if result['requirement_met'] else '超过'} {max_lines} 行"
            
            elif case_type == "function_parameters_min":
                min_params = params.get("number", 0)
                result["requirement_met"] = self.evaluate_function_parameters(code, language)[1] >= min_params
                result["details"] = f"函数参数最小数量 {'满足' if result['requirement_met'] else '不满足'} {min_params}"
            
            elif case_type == "function_parameters_max":
                max_params = params.get("number", 0)
                result["requirement_met"] = self.evaluate_function_parameters(code, language)[0] <= max_params
                result["details"] = f"函数参数最大数量 {'满足' if result['requirement_met'] else '不满足'} {max_params}"
            
            elif case_type == "time_limit":
                # 从参数中获取时间限制
                time_limit = params.get("time", 0)
                # 从 runtime_result 中获取最大执行时间
                max_execution_time = runtime_result['max_time']
                # 判断是否满足时间限制
                result["requirement_met"] = max_execution_time <= time_limit
                result["details"] = f"最大执行时间为 {max_execution_time} ms，要求时间限制为 {time_limit} ms"

            elif case_type == "storage_limit":
                # 从参数中获取存储限制
                storage_limit = params.get("storage", 0)
                # 从 runtime_result 中获取最大内存使用
                max_memory_usage = runtime_result['max_memory']
                # 判断是否满足存储限制
                result["requirement_met"] = max_memory_usage <= storage_limit
                result["details"] = f"最大内存使用为 {max_memory_usage} KB，要求存储限制为 {storage_limit} KB"

            elif case_type == "output_format":
                # 保持原逻辑
                require_format = runtime_result['output_format']
                # 从参数中获取格式要求
                expected_format = params.get("format", "")
                # 判断是否满足格式要求
                result["requirement_met"] = require_format == expected_format
                result["details"] = f"输出格式为 {require_format}，要求格式为 {expected_format}"
            else:
                result["details"] = f"未知的要求类型: {case_type}"
                
            result["success"] = True
        except Exception as e:
            result["success"] = False
            result["details"] = f"评估 {case_type} 时出错: {str(e)}"
            
        return result
    
    def extract_params_from_prompt(self, prompt: str, case_type: str) -> Dict[str, Any]:
        """根据case_type从提示中提取参数"""
        params = {}
        
        # 先检查全局change_cases列表中是否有匹配的模板
        if change_cases:
            for case, templates in change_cases:
                if case == case_type:
                    for template in templates:
                        # 尝试通过与模板比较提取参数
                        template_params = self.extract_params_from_template(prompt, template, case_type)
                        if template_params:
                            return template_params
        
        # 回退到正则表达式提取
        if case_type == "keyword_variable_include":
            match = re.search(r'(?:incorporate|include|use|utilize|with)\s+(\w+)\s+as', prompt)
            if match:
                params["name"] = match.group(1)
                
        elif case_type == "keyword_variable_number":
            name_match = re.search(r'(?:position|assign|ensure|make|set)\s+(\w+)\s+as', prompt)
            pos_match = re.search(r'the\s+(\d+)(?:st|nd|rd|th)', prompt)
            if name_match and pos_match:
                params["name"] = name_match.group(1)
                params["number"] = int(pos_match.group(1))
                
        elif case_type == "keyword_variable_type":
            pos_match = re.search(r'the\s+(\d+)(?:st|nd|rd|th)', prompt)
            type_match = re.search(r'(?:as|a|of type)\s+(\w+)(?:\s+variable|\s+var)?', prompt)
            if pos_match and type_match:
                params["number"] = int(pos_match.group(1))
                params["type"] = type_match.group(1)
                
        elif case_type == "keyword_function":
            num_match = re.search(r'(?:exactly|precisely)?\s+(\d+)\s+(\w+)', prompt)
            if num_match:
                params["number"] = int(num_match.group(1))
                params["function_form"] = num_match.group(2)  # "function" 或 "functions"
                
        elif case_type == "keyword_class":
            num_match = re.search(r'(?:exactly|precisely)?\s+(\d+)\s+(\w+)', prompt)
            if num_match:
                params["number"] = int(num_match.group(1))
                params["class_form"] = num_match.group(2)  # "class" 或 "classes"
                
        elif case_type == "coding_language":
            lang_match = re.search(r'(?:in|to|using)\s+(\w+\+*\+*)', prompt)
            if lang_match:
                params["language"] = lang_match.group(1)
                
        elif case_type == "time_limit":
            time_match = re.search(r'within\s+(\d+)\s+(?:ms|milliseconds)', prompt)
            if time_match:
                params["time"] = int(time_match.group(1))
                
        elif case_type == "storage_limit":
            storage_match = re.search(r'(?:below|less than)\s+(\d+)\s+(?:KB|kilobytes)', prompt)
            if storage_match:
                params["storage"] = int(storage_match.group(1))
                
        elif case_type == "output_format":
            format_match = re.search(r'format\s+(?:of|is)\s+([\{\[\(][^)]*[\}\]\)])', prompt)
            if format_match:
                params["format"] = format_match.group(1)
                
        return params
    
    def extract_params_from_template(self, prompt: str, template: str, case_type: str) -> Dict[str, Any]:
        """通过与模板比较来提取参数"""
        params = {}
        
        # 模板使用{param}格式作为占位符
        # 从模板中提取所有参数名
        param_names = re.findall(r'\{([^}]+)\}', template)
        
        # 如果模板中没有参数，返回空字典
        if not param_names:
            return params
        
        # 从模板创建正则表达式模式，转义特殊字符并替换占位符
        pattern = re.escape(template)
        for param in param_names:
            # 将\{param\}替换为(?P<param>.+?)
            pattern = pattern.replace('\\{' + param + '\\}', f'(?P<{param}>.+?)')
        
        # 尝试用模式匹配提示
        match = re.search(pattern, prompt)
        if match:
            # 提取命名组
            for param in param_names:
                if param in match.groupdict():
                    # 转换数值
                    value = match.group(param)
                    if param in ['number', 'time', 'storage']:
                        try:
                            params[param] = int(value)
                        except ValueError:
                            params[param] = value
                    else:
                        params[param] = value
        
        return params
import gc
import json
from tqdm import tqdm
def evaluate_jsonl_file(input_file: str, output_file: str, chunk_size: int = 1):
    """评估JSONL文件中的代码样本，一行一行处理以减少内存占用"""
    evaluator = CodeEvaluator()
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f, \
             open(output_file, 'a', encoding='utf-8') as outfile:  # 打开输出文件用于写入
            
            # 获取文件总行数，用于进度条显示
            total_lines = sum(1 for _ in open(input_file, 'r', encoding='utf-8'))
            
            start_line = 369
            end_line = min(total_lines, 401)
            
            # 重新打开文件，跳到起始位置
            f.seek(0)
            for _ in range(start_line):
                f.readline()  # 跳过前start_line行
            
            # 使用tqdm显示进度
            for line_num in tqdm(range(start_line, end_line), desc="评估进度", unit="line", ncols=100):
                # 在每行评测前清理内存和进程
                gc.collect()
                
                if line_num == 632:
                    print("跳过632行")
                    continue
                
                # 在Windows上尝试强制释放内存
                if sys.platform == 'win32':
                    try:
                        import ctypes
                        ctypes.windll.kernel32.SetProcessWorkingSetSize(-1, -1)
                    except Exception as e:
                        print(f"内存释放尝试失败: {e}")
                
                # 清理任何潜在的僵尸子进程
                try:
                    import subprocess
                    if sys.platform != 'win32':  # Unix/Linux/Mac
                        subprocess.call(["ps", "-ef", "|", "grep", "python", "|", "grep", "-v", "grep", "|", "awk", "'{print $2}'", "|", "xargs", "kill", "-9"], shell=True)
                except Exception as e:
                    print(f"进程清理尝试失败: {e}")
                
                line = f.readline()
                if not line:
                    break  # 如果已经到文件末尾，则退出循环
                
                try:
                    print(f"\n正在处理第 {line_num} 行...")
                    data = json.loads(line.strip())
                    question_id = data.get("question_id", f"question_{line_num}")
                    code = data.get("model_response_turn0_code", "")
                    language = data.get("model_response_turn0_code_languages", "Python")

                    if not code:
                        result = {
                            "question_id": question_id,
                            "turns": [],
                            "overall_success": False
                        }
                        runtime_turn = {
                            "turn": 0,
                            "type": "runtime_evaluation",
                            "success": False,
                            "details": {
                                "error": "代码为空",
                            }
                        }
                        result["turns"].append(runtime_turn)
                    else:
                        code = code[0]
                        language = language[0]
                        test_cases = []
                        if "decoded_private_test_cases" in data:
                            try:
                                test_cases = data["decoded_private_test_cases"]
                            except:
                                test_cases = []
                        
                        runtime_result = evaluator.run_code(code, language, test_cases)
                        gc.collect()  # 运行代码后立即清理内存
                        
                        result = {
                            "question_id": question_id,
                            "turns": []
                        }
                        
                        def parse_test_results(output_text):
                            # 提取成功/失败信息
                            success_pattern = r"测试摘要: 通过 (\d+)/(\d+)"
                            success_match = re.search(success_pattern, output_text)
                            
                            if success_match:
                                passed = int(success_match.group(1))
                                total = int(success_match.group(2))
                                success = passed == total
                            else:
                                success = False
                            
                            # 提取所有内存使用值
                            memory_pattern = r"内存使用: ([\d.]+) KB"
                            memory_values = [float(x) for x in re.findall(memory_pattern, output_text)]
                            max_memory = max(memory_values) if memory_values else 0
                            
                            # 提取所有执行时间
                            time_pattern = r"执行时间: ([\d.]+) 毫秒"
                            time_values = [float(x) for x in re.findall(time_pattern, output_text)]
                            max_time = max(time_values) if time_values else 0
                            
                            #提取输出格式(output_format: direct/'{ output }')
                            format_pattern = r"(?:输出格式|output_format):\s+(direct|\{.*?\})"
                            format_value = re.search(format_pattern, output_text)
                            output_format = format_value.group(1) if format_value else None
                            
                            # 提取通过/总数
                            passed_tests = passed if success_match else 0
                            total_tests = total if success_match else 0
                            
                            return {
                                "success": success,
                                "max_memory": max_memory,
                                "max_time": max_time,
                                "passed_tests": passed_tests,
                                "total_tests": total_tests,
                                "output_format": output_format
                            }
                        
                        # 假设runtime_result中有个results数组，且第一个元素包含输出
                        parsed_info = parse_test_results(runtime_result.get("results", [{}])[0].get("output", ""))
                        runtime_turn = {
                            "turn": 0,
                            "type": "runtime_evaluation",
                            "success": parsed_info["success"],
                            "details": {
                                "error": runtime_result.get("error"),
                                "compilation_error": runtime_result.get("compilation_error"),
                                "memory_usage": parsed_info["max_memory"],
                                "execution_time": parsed_info["max_time"],
                                "test_summary": {
                                    "passed": parsed_info["passed_tests"],
                                    "total": parsed_info["total_tests"],
                                    "pass_rate": parsed_info["passed_tests"] / parsed_info["total_tests"] if parsed_info["total_tests"] > 0 else 0
                                }
                            }
                        }
                        
                        result["turns"].append(runtime_turn)
                    
                    turn_count = 1
                    
                    while f"turn{turn_count}_kwargs" in data and f"turn{turn_count}_prompt" in data and f"turn{turn_count}_params" in data:
                        last_runtime_result = None  # 跟踪最后一个成功的runtime结果
                        case_type = data[f"turn{turn_count}_kwargs"]
                        prompt = data[f"turn{turn_count}_prompt"]
                        requirement_result = []
                        for i in range(len(case_type)):
                            # 从提示中提取参数
                            params = data[f"turn{turn_count}_params"][i]
                            turn_code = data.get(f"model_response_turn{turn_count}_code", "")
                            turn_language = data.get(f"model_response_turn{turn_count}_code_languages", language)
                            
                            if not turn_code:
                                # 如果代码为空，跳过评估
                                turn_result = {
                                    "turn": turn_count,
                                    "type": case_type[i],
                                    "prompt": prompt[i],
                                    "parameters": params,
                                    "success": False,
                                    "details": "代码为空",
                                    "language_type": 0
                                }

                                result["turns"].append(turn_result)
                                turn_count += 1
                                continue
                            else:
                                # 如过参数中有language，使用参数中的language
                                if "language" in params:
                                    language = params["language"]
                                
                                turn_code = turn_code[0]
                                turn_language = turn_language[0]
                                
                                if not last_runtime_result:
                                    # 清理一次内存再运行代码
                                    gc.collect()
                                    requirement_runtime_result = evaluator.run_code(turn_code, turn_language, test_cases)
                                    last_runtime_result = requirement_runtime_result  # 更新最后一个runtime结果
                                    gc.collect()  # 代码运行后再次清理
                                
                                # 获取输出文本
                                output_text = ""
                                if last_runtime_result.get("results") and len(last_runtime_result.get("results")) > 0:
                                    output_text = last_runtime_result["results"][0].get("output", "")

                                # 使用parse_test_results获取解析信息
                                parsed_info = parse_test_results(output_text)
                                
                                # 评估要求
                                requirement_result.append(evaluator.evaluate_requirements(turn_code, case_type[i], params, turn_language, parsed_info))
                                
                            # 在现有的turn_result上添加runtime_turn
                            turn_result = {
                                "turn": turn_count,
                                "type": case_type,
                                "prompt": prompt,
                                "parameters": params,
                                "success": [r.get("requirement_met", False) for r in requirement_result],
                                "details": [r.get("details", "") for r in requirement_result],
                                "language_type": language == turn_language,
                                "runtime_turn": {
                                    "turn": 0,
                                    "type": "runtime_evaluation",
                                    "success": parsed_info["success"],
                                    "details": {
                                        "error": requirement_runtime_result.get("error"),
                                        "compilation_error": requirement_runtime_result.get("compilation_error"),
                                        "memory_usage": parsed_info["max_memory"],
                                        "execution_time": parsed_info["max_time"],
                                        "test_summary": {
                                            "passed": parsed_info["passed_tests"],
                                            "total": parsed_info["total_tests"],
                                            "pass_rate": parsed_info["passed_tests"] / parsed_info["total_tests"] 
                                                        if parsed_info["total_tests"] > 0 else 0
                                        }
                                    }
                                }
                            }

                        result["turns"].append(turn_result)
                        gc.collect()  # 每个turn结束后清理一次内存
                        
                        turn_count += 1
                        if turn_count == 6:
                            break
                    
                    initial_runtime_success = result["turns"][0].get("success", False) if result["turns"] else False
                    requirements_success = True
                    
                    for turn in result["turns"][1:]:  # 跳过第一个runtime_turn
                        # 检查要求是否满足
                        if not turn.get("success", False):
                            requirements_success = False
                            break
                        # 检查每个turn中的runtime_turn是否成功
                        if "runtime_turn" in turn and not turn["runtime_turn"].get("success", False):
                            requirements_success = False
                            break
                    
                    result["overall_success"] = initial_runtime_success and requirements_success
                    
                    # 立即将结果写入输出文件并刷新缓冲区
                    outfile.write(json.dumps(result, ensure_ascii=False) + '\n')
                    outfile.flush()  # 强制写入磁盘
                    
                    print(f"完成第{line_num}行评估，内存使用情况：{get_memory_usage_mb():.2f} MB")
                except Exception as e:
                    print(f"处理第{line_num}行时出错: {e}")
                    traceback.print_exc()
                    # 立即将错误结果写入输出文件
                    outfile.write(json.dumps({
                        "question_id": f"question_{line_num}",
                        "error": str(e),
                        "overall_success": False,
                        "turns": []
                    }, ensure_ascii=False) + '\n')
                    outfile.flush()  # 强制写入磁盘
                    continue
                
                # 每行处理完后，强制进行全面清理
                gc.collect()
                if sys.platform == 'win32':
                    try:
                        import ctypes
                        ctypes.windll.kernel32.SetProcessWorkingSetSize(-1, -1)
                    except:
                        pass
            
        # 打印摘要
        with open(output_file, 'r', encoding='utf-8') as f:
            results = [json.loads(line.strip()) for line in f]
        success_count = sum(1 for r in results if r.get("overall_success", False))
        print(f"评估完成。结果已保存到 {output_file}")
        print(f"成功率: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)" if results else "无结果")
        
        # 打印每轮的成功率统计
        turn_success = {}
        for result in results:
            for turn in result.get("turns", []):
                turn_num = turn.get("turn")
                if turn_num is not None:
                    if turn_num not in turn_success:
                        turn_success[turn_num] = {"success": 0, "total": 0}
                    turn_success[turn_num]["total"] += 1
                    
                    # Check both requirement success and runtime success
                    requirement_success = turn.get("success", False)
                    runtime_success = True  # Default to True for turns that might not have runtime checks
                    
                    # Check runtime success if available
                    if "runtime_turn" in turn:
                        runtime_success = turn["runtime_turn"].get("success", False)
                    
                    # Only count as successful if both requirement and runtime checks pass
                    if requirement_success and runtime_success:
                        turn_success[turn_num]["success"] += 1

        # 按轮次排序并打印
        for turn_num in sorted(turn_success.keys()):
            stats = turn_success[turn_num]
            success_rate = stats["success"] / stats["total"] * 100 if stats["total"] > 0 else 0
            print(f"第{turn_num}轮: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
                
    except Exception as e:
        print(f"处理文件时出错: {e}")
        traceback.print_exc()

# 添加一个函数来获取当前进程的内存使用情况
def get_memory_usage_mb():
    """获取当前进程的内存使用情况（MB）"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    return memory_info.rss / 1024 / 1024  # 转换为MB

import argparse

if __name__ == "__main__":
    # Create argument parser
    parser = argparse.ArgumentParser(description="Evaluate code generation results")
    parser.add_argument("--input_file", type=str, 
                        default=r'F:\dataset\new_try\output\real_experiment\ex_result_gemma-3-27b_filter.jsonl',
                        help="Path to input JSONL file")
    parser.add_argument("--output_file", type=str,
                        default=r'F:\dataset\new_try\output\real_experiment\ex_result_gemma-3-27b_eval.jsonl',
                        help="Path to output JSONL file")
    parser.add_argument("--shutdown", action="store_true",
                        help="Shutdown computer after evaluation")
    
    # Parse arguments
    args = parser.parse_args()
    
    print("开始评估...")
    evaluate_jsonl_file(args.input_file, args.output_file)
    
    # Only shutdown if requested
    if args.shutdown:
        os.system("shutdown /s /t 60")  # Windows shutdown with 60-second timer