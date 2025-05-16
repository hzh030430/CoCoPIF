import json
import os
from typing import List, Dict, Any, Optional
import argparse
from tqdm import tqdm
from openai import OpenAI
import random
import re
import sys
import copy
import ast
import clang.cindex
import javalang
import concurrent.futures # Added import
from functools import partial # Added import

path_to_libclang = r"C:\Program Files\LLVM\bin\libclang.dll" # <--- 仔细检查并修改这里！！！

if os.path.exists(path_to_libclang):
    try:
        clang.cindex.Config.set_library_file(path_to_libclang)
        print(f"信息: 成功通过代码设置 libclang 路径: {path_to_libclang}")
    except Exception as e_cfg:
        print(f"错误: 尝试通过代码设置 libclang 路径时出错: {e_cfg}")
        print("请确保路径正确且文件未损坏。")
        # sys.exit(1) # 如果设置失败，可以选择退出脚本
else:
    print(f"错误: 在指定路径未找到 libclang.dll: {path_to_libclang}")
    print("请确认 LLVM 是否已安装，并且上述路径指向了正确的 libclang.dll 文件。")

change_cases = [
    ['keyword_for', ['Please revise your code to incorporate at least one for loop for iteration.', 'Kindly update your code to include a for loop as part of the implementation.', 'Could you modify your code to ensure it contains at least one for loop?', 'We recommend refactoring your code to integrate a for loop into the logic.', 'It would be appreciated if you could adjust your code to include at least one for loop.']],
    ['keyword_for_not', ['Please revise your code to exclude any for loops in the implementation.', 'Kindly update your code to ensure it does not contain any for loops.', 'Could you modify your code to avoid using for loops entirely?', 'We recommend refactoring your code to remove any for loops from the logic.', 'It would be appreciated if you could adjust your code to omit for loops.']],
    ['keyword_while', ['Please revise your code to incorporate at least one while loop for iterative processing.', 'Kindly update your code to include a while loop as part of the implementation.', 'Could you modify your code to ensure it contains at least one while loop?', 'We recommend refactoring your code to integrate a while loop into the logic.', 'It would be appreciated if you could adjust your code to include at least one while loop.']],
    ['keyword_while_not', ['Please revise your code to exclude any while loops in the implementation.', 'Kindly update your code to ensure it does not contain any while loops.', 'Could you modify your code to avoid using while loops entirely?', 'We recommend refactoring your code to remove any while loops from the logic.', 'It would be appreciated if you could adjust your code to omit while loops.']],
    ['keyword_if', ['Please revise your code to incorporate at least one if statement for conditional logic.', 'Kindly update your code to include an if statement as part of the implementation.', 'Could you modify your code to ensure it contains at least one if statement?', 'We recommend refactoring your code to integrate an if statement into the logic.', 'It would be appreciated if you could adjust your code to include at least one if statement.']],
    ['keyword_if_not', ['Please revise your code to exclude any if statements in the implementation.', 'Kindly update your code to ensure it does not contain any if statements.', 'Could you modify your code to avoid using if statements entirely?', 'We recommend refactoring your code to remove any if statements from the logic.', 'It would be appreciated if you could adjust your code to omit if statements.']],
    ['keyword_function', ['Please revise your code to incorporate exactly {number} {function_form} in the implementation.', 'Kindly update your code to include {number} {function_form} as part of the logic.', 'Could you modify your code to ensure it contains exactly {number} {function_form}?', 'We recommend refactoring your code to integrate {number} {function_form} into the implementation.', 'It would be appreciated if you could adjust your code to include exactly {number} {function_form}.']],
    ['keyword_function_not', ['Please revise your code to exclude any function in the implementation.', 'Kindly update your code to ensure it does not contain any function.', 'Could you modify your code to avoid using function entirely?', 'We recommend refactoring your code to remove any function from the logic.', 'It would be appreciated if you could adjust your code to omit function.']],
    ['keyword_function_one', ['Please revise your code to incorporate {function_form} in the implementation.', 'Kindly update your code to include {function_form} as part of the logic.', 'Could you modify your code to ensure it contains {function_form}?', 'We recommend refactoring your code to integrate {function_form} into the implementation.', 'It would be appreciated if you could adjust your code to include {function_form}.']],
    ['keyword_class', ['Please revise your code to incorporate exactly {number} {class_form} in the implementation.', 'Kindly update your code to include {number} {class_form} as part of the structure.', 'Could you modify your code to ensure it contains {number} {class_form}?', 'We recommend refactoring your code to integrate {number} {class_form} into the design.', 'It would be appreciated if you could adjust your code to include {number} {class_form}.']],
    ['keyword_class_not', ['Please revise your code to exclude any class in the implementation.', 'Kindly update your code to ensure it does not contain any class.', 'Could you modify your code to avoid using class entirely?', 'We recommend refactoring your code to remove any class from the logic.', 'It would be appreciated if you could adjust your code to omit class.']],
    ['keyword_class_one', ['Please revise your code to incorporate {class_form} in the implementation.', 'Kindly update your code to include {class_form} as part of the structure.', 'Could you modify your code to ensure it contains {class_form}?', 'We recommend refactoring your code to integrate {class_form} into the design.', 'It would be appreciated if you could adjust your code to include {class_form}.']],
    ['built_in_function', ['Please revise your code to exclusively utilize built-in functions, avoiding any external library functions.', 'Kindly update your code to restrict function usage to only those that are built-in, excluding any external libraries.', 'Could you modify your code to use only built-in functions and avoid external libraries?', 'We recommend refactoring your code to rely solely on built-in functions and not external libraries.', 'It would be appreciated if you could adjust your code to use only built-in functions.']],
    ['coding_style', ['Please revise your code and ensure it contains no comments.', 'Kindly update your code to exclude any comments in the implementation.', 'Could you modify your code to remove all comments?', 'We recommend refactoring your code to omit any comments entirely.', 'It would be appreciated if you could adjust your code to be free of comments.']],
    ['coding_style_include', ['Please revise your code and ensure it contains comments.', 'Kindly update your code to include comments in the implementation.', 'Could you modify your code to add comments?', 'We recommend refactoring your code to include comments for clarity.', 'It would be appreciated if you could adjust your code to have comments.']],
    ['global_variable', ['Please revise your code to use at least one global variable.', 'Kindly update your code to include a global variable in the implementation.', 'Could you modify your code to ensure it contains a global variable?', 'We recommend refactoring your code to integrate a global variable into the logic.', 'It would be appreciated if you could adjust your code to include a global variable.']],
    ['global_variable_not', ['Please revise your code to exclude any global variables in the implementation.', 'Kindly update your code to ensure it does not contain any global variables.', 'Could you modify your code to avoid using global variables entirely?', 'We recommend refactoring your code to remove any global variables from the logic.', 'It would be appreciated if you could adjust your code to omit global variables.']],
    ['constant_variable', ['Please revise your code to use at least one constant variable.', 'Kindly update your code to include a constant variable in the implementation.', 'Could you modify your code to ensure it contains a constant variable?', 'We recommend refactoring your code to integrate a constant variable into the logic.', 'It would be appreciated if you could adjust your code to include a constant variable.']],
    ['constant_variable_not', ['Please revise your code to exclude any constant variables in the implementation.', 'Kindly update your code to ensure it does not contain any constant variables.', 'Could you modify your code to avoid using constant variables entirely?', 'We recommend refactoring your code to remove any constant variables from the logic.', 'It would be appreciated if you could adjust your code to omit constant variables.']],
    ['code_lines', ['Please revise your code to contain at most {number} lines of code.', 'Kindly update your code to limit the number of lines to {number}.', 'Could you modify your code to ensure it does not exceed {number} lines?', 'We recommend refactoring your code to reduce the number of lines to {number}.', 'It would be appreciated if you could adjust your code to have at most {number} lines.']],
    ['keyword_variable_include', ['Kindly revise your code to incorporate {name} as a variable identifier.', 'Please refactor your code to include {name} as a variable name.', 'Could you modify your code to use {name} as a variable name?', 'We recommend updating your code to utilize {name} as a variable name.', 'It would be appreciated if you could rewrite your code with {name} as a variable name.']],
    ['keyword_variable_number', ['Please revise your code to position {name} as the {number}{suffix} variable in the sequence.', 'Kindly refactor your code to assign {name} as the {number}{suffix} variable in the list.', 'Could you update your code to ensure {name} is the {number}{suffix} variable in the order?', 'We recommend modifying your code to make {name} the {number}{suffix} variable in the structure.', 'It would be appreciated if you could adjust your code to set {name} as the {number}{suffix} variable.']],
    ['keyword_variable_type', ['Please modify the code so that the {number}{suffix} variable declared (when reading the source code top-to-bottom, left-to-right) is explicitly defined with the type {type}.', 'Kindly refactor the code to ensure that the {number}{suffix} variable declared (when reading the source code top-to-bottom, left-to-right) is explicitly defined with the type {type}.', 'Could you update the code to guarantee that the {number}{suffix} variable declared (when reading the source code top-to-bottom, left-to-right) is explicitly defined with the type {type}?', 'We recommend modifying the code to make sure that the {number}{suffix} variable declared (when reading the source code top-to-bottom, left-to-right) is explicitly defined with the type {type}.', 'It would be appreciated if you could adjust the code to ensure that the {number}{suffix} variable declared (when reading the source code top-to-bottom, left-to-right) is explicitly defined with the type {type}.']],
    ['coding_language', ['Please revise your code to be written in {language}.', 'Kindly update your code to conform to the {language} programming language.', 'Could you modify your code to be implemented in {language}?', 'We recommend refactoring your code to be written in {language}.', 'It would be appreciated if you could adjust your code to be written in {language}.']],
    ['function_parameters_max', ['All Your function should have at most {number} parameters.', 'Please revise your code to ensure that all functions have at most {number} parameters.', 'Kindly update your code to limit the number of parameters in each function to {number}.', 'Could you modify your code to ensure that no function has more than {number} parameters?', 'We recommend refactoring your code to restrict all functions to a maximum of {number} parameters.', 'It would be appreciated if you could adjust your code to ensure that all functions have at most {number} parameters.']],
    ['function_parameters_min', ['All Your function should have at least {number} parameters.', 'Please revise your code to ensure that all functions have at least {number} parameters.', 'Kindly update your code to require a minimum of {number} parameters in each function.', 'Could you modify your code to ensure that no function has fewer than {number} parameters?', 'We recommend refactoring your code to restrict all functions to a minimum of {number} parameters.', 'It would be appreciated if you could adjust your code to ensure that all functions have at least {number} parameters.']]
]

basic_cases = [
    ['time_limit', ['Please revise your code to ensure it executes within {time} milliseconds.', 'Kindly update your code to optimize its runtime to be within {time} ms.', 'Could you modify your code to guarantee its execution time does not exceed {time} milliseconds?', 'We recommend refactoring your code to achieve a runtime of {time} ms or less.', 'It would be appreciated if you could adjust your code to run within {time} milliseconds.']],
    ['storage_limit', ['Please revise your code to ensure its memory usage remains below {storage} kilobytes.', 'Kindly update your code to optimize its memory consumption to less than {storage} KB.', 'Could you modify your code to guarantee its memory usage does not exceed {storage} kilobytes?', 'We recommend refactoring your code to limit its memory footprint to under {storage} KB.', 'It would be appreciated if you could adjust your code to use less than {storage} KB of memory.']],
    ['output_format', ['Please revise your code to ensure the output adheres to the {format} format.', 'Kindly update your code to generate output strictly in the {format} format.', 'Could you modify your code to guarantee the output conforms to the {format} format?', 'We recommend refactoring your code to produce output in the {format} format.', 'It would be appreciated if you could adjust your code to output data in the {format} format.']]
]

def extract_code_from_text(text):
    # 用于保存所有提取的代码块及其语言信息
    extracted_codes = []
    
    # 查找所有代码块
    pos = 0
    while True:
        # 查找代码块开始标记
        start_marker_pos = text.find("```", pos)
        if start_marker_pos == -1:
            break
            
        # 寻找语言标识符，它紧跟在```之后
        language_start = start_marker_pos + 3
        language_end = text.find("\n", language_start)
        if language_end == -1:
            pos = start_marker_pos + 3
            continue
            
        language = text[language_start:language_end].strip()
        
        # 代码块内容的起始位置
        code_start = language_end + 1
        
        # 寻找代码块结束标记
        code_end = text.find("```", code_start)
        if code_end == -1:
            break
            
        code_block = text[code_start:code_end].strip()

        # 检查代码块中的分隔符行
        lines = code_block.split('\n')
        for i, line in enumerate(lines):
            # 打印调试信息
            #print(f"调试信息: '{line}'")
            
            # 使用正则表达式匹配分隔符行（由多个'-'组成）
            if re.match(r"^-+$", line.strip()):  # 匹配任意数量的连续 `-`
                print(f"发现分隔符行: {line.strip()}")
                # 找到了分隔符行，只保留之前的内容
                code_block = '\n'.join(lines[:i]).strip()
                break

        # 保存代码块和语言信息
        extracted_codes.append({
            "language": language,
            "code": code_block
        })
                
        # 更新位置以查找下一个代码块
        pos = code_end + 3
        
    return extracted_codes

def check_loop(code_block, coding_language):
    if coding_language.lower() == "python":
        if "for" in code_block and "while" in code_block:
            return 3
        elif "for" in code_block:
            return 1
        elif "while" in code_block:
            return 2
        return 0
    elif coding_language.lower() == "c++":
        if "for" in code_block and "while" in code_block:
            return 3
        elif "for" in code_block:
            return 1
        elif "while" in code_block:
            return 2
        return 0
    elif coding_language.lower() == "java":
        if "for" in code_block and "while" in code_block:
            return 3
        elif "for" in code_block:
            return 1
        elif "while" in code_block:
            return 2
        return 0
    else:
        return False
    
def check_if(code_block, coding_language):
    """检查代码中是否包含 if 语句"""
    coding_language = coding_language.lower()
    
    # 先移除字符串字面量和注释，以避免误判
    if coding_language == "python":
        # 移除字符串和注释
        code_no_strings = re.sub(r'"[^"]*"', '', code_block)
        code_no_strings = re.sub(r"'[^']*'", '', code_no_strings)
        code_no_strings = re.sub(r'#.*$', '', code_no_strings, flags=re.MULTILINE)
        
        # 使用单词边界检查真正的 if 语句
        return 1 if re.search(r'\bif\b', code_no_strings) else 0
        
    elif coding_language in ["c++", "java"]:
        # 移除字符串和注释
        code_no_strings = re.sub(r'"[^"]*"', '', code_block)
        code_no_strings = re.sub(r"'[^']*'", '', code_no_strings)
        code_no_strings = re.sub(r'//.*$', '', code_no_strings, flags=re.MULTILINE)
        code_no_strings = re.sub(r'/\*[\s\S]*?\*/', '', code_no_strings)
        
        # 使用单词边界检查真正的 if 语句
        return 1 if re.search(r'\bif\b', code_no_strings) else 0
    
    # 对于不支持的语言，统一返回0
    return 0

def check_function(code_block, coding_language):
    lang = coding_language.lower()
    processed_code = code_block
    count = 0

    try:
        # Preprocessing to remove comments and strings remains the same
        if lang == "python":
            processed_code = re.sub(r'"""[\s\S]*?"""', '', processed_code)
            processed_code = re.sub(r"'''[\s\S]*?'''", '', processed_code)
            processed_code = re.sub(r'"[^"]*"', '', processed_code)
            processed_code = re.sub(r"'[^']*'", '', processed_code)
            processed_code = re.sub(r'#.*$', '', processed_code, flags=re.MULTILINE)
        elif lang in ["c++", "java"]:
            processed_code = re.sub(r'/\*[\s\S]*?\*/', '', processed_code)
            processed_code = re.sub(r'//.*$', '', processed_code, flags=re.MULTILINE)
            processed_code = re.sub(r'"(?:\\.|[^"\\])*"', '', processed_code)
            if lang == "java" or lang == "c++":
                 processed_code = re.sub(r"'(?:\\.|[^'\\])'", '', processed_code)
    except re.error as e:
        print(f"Regex error during preprocessing for {lang}: {e}")
        return 0

    try:
        if lang == "python":
            # Python: Count 'def' statements (includes methods within classes)
            matches = re.findall(r'\bdef\s+\w+\s*\((?:[^)]*)\)\s*:', processed_code)
            count = len(matches)

        elif lang == "c++":
            pattern = r'\b(?!if|while|for|switch|class|struct|enum|union|namespace|template\b)\b(?:[\w\*&:]+)\s+([\w~]+)\s*\((?:[^)]*)\)\s*(?:const)?\s*{'
            matches = re.findall(pattern, processed_code)
            count = len(matches)

        elif lang == "java":
            # Removed the negative lookbehind (?<!\bmain)
            method_pattern = r'\b(?:public|private|protected)?\s*(?:static|final|abstract|synchronized)?\s*(?:[\w<>\[\]\.\s]+)\s+(\w+)\s*\((?:[^)]*)\)\s*(?:throws\s+[\w\.\s,]+)?\s*{'
            method_matches = re.findall(method_pattern, processed_code)
            count = len(method_matches) # Only count methods, not constructors

        else:
            # Unsupported language
            return 0

    except re.error as e:
        print(f"Regex error during counting for {lang}: {e}")
        return 0

    return count



def check_class(code_block, coding_language):
    coding_language = coding_language.lower()
    if coding_language == "python":
        # 查找所有 Python 类定义
        matches = re.findall(r'\bclass\s+\w+\s*:', code_block)
        return len(matches)
    elif coding_language == "c++" or coding_language == "cpp":
        # 查找所有 C++ 类定义
        # 匹配 class keyword 后跟类名和 {
        matches = re.findall(r'\bclass\s+\w+\s*(?::\s*(?:public|private|protected)\s+\w+\s*)?{', code_block)
        return len(matches)
    elif coding_language == "java":
        # 查找所有 Java 类定义
        # 匹配可选的访问修饰符、abstract，然后是 class 关键字、类名和 {
        matches = re.findall(r'\b(?:public|private|protected)?\s*(?:abstract|final)?\s*class\s+\w+\s*(?:extends\s+\w+)?\s*(?:implements\s+\w+(?:\s*,\s*\w+)*)?\s*{', code_block)
        return len(matches)
    else:
        # 对于不支持的语言，返回 0
        return 0

def check_built_in_function(code_block, coding_language):
    coding_language = coding_language.lower()
    if coding_language == "python":
        # 检查是否有非内置库的 import 语句
        allowed_libraries = [
            'os', 'sys', 'math', 'random', 'datetime', 'json', 're', 'urllib', 
            'http', 'email', 'collections', 'itertools', 'functools', 'contextlib',
            'abc', 'io', 'time', 'logging', 'threading', 'multiprocessing', 'socket',
            'asyncio', 'enum', 'typing', 'copy', 'pprint', 'string', 'decimal',
            'fractions', 'zlib', 'gzip', 'bz2', 'lzma', 'zipfile', 'tarfile', 'csv',
            'configparser', 'getopt', 'argparse', 'platform', 'gc', 'weakref',
            'warnings', 'dis', 'pdb', 'unittest', 'doctest', 'venv', 'base64',
            'hashlib', 'hmac', 'secrets', 'uuid', 'graphlib', 'dataclasses',
            'codecs'
        ]
        # 查找所有导入的库
        import_lines = re.findall(r'^(?:import\s+(\S+)|from\s+(\S+)\s+import)', code_block, re.MULTILINE)
        imported_libs = []
        for match in import_lines:
            if match[0]:
                imported_libs.append(match[0])
            elif match[1]:
                imported_libs.append(match[1])

        # 检查导入的库是否都在 allowed_libraries 中
        for lib in imported_libs:
            if lib not in allowed_libraries:
                return False  # 发现了不允许的库
        return True  # 所有导入的库都在允许列表中
    elif coding_language == "c++" or coding_language == "cpp":
        # 检查 include 语句，只允许标准库
        includes = re.findall(r'#include\s*<([^>]+)>', code_block)
        standard_headers = {
            'iostream', 'string', 'vector', 'map', 'set', 'algorithm', 'cmath',
            'cstdlib', 'ctime', 'cstring', 'cassert', 'queue', 'stack', 'deque'
        }
        return all(header in standard_headers for header in includes)
    elif coding_language == "java":
        # 检查 import 语句，只允许 java. 包
        import_statements = re.findall(r'import\s+([^;]+);', code_block)
        for import_stmt in import_statements:
            if not import_stmt.startswith('java.'):
                return False
        return True
    else:
        return False

def check_comment(code_block, coding_language):
    coding_language = coding_language.lower()
    if coding_language == "python":
        if re.search(r'(?<![\'"]).*#.*', code_block):
            return 1
        return 0
    elif coding_language == "c++" or coding_language == "cpp":
        if re.search(r'//.*|/\*[\s\S]*?\*/', code_block):
            return 1
        return 0
    elif coding_language == "java":
        if re.search(r'//.*|/\*[\s\S]*?\*/', code_block):
            return 1
        return 0
    else:
        return 0

def check_global_variable(code_block, coding_language):
    coding_language = coding_language.lower()
    if coding_language == "python":
        if re.search(r'^(?!(?:\s*def|\s*class)\s+\w+\s*\(?:\w+\s*,\s*\w+\)?\s*:).*?\b\w+\s*=\s*.*', code_block, re.MULTILINE | re.DOTALL):
            return 1
        return 0
    elif coding_language == "c++" or coding_language == "cpp":
        if re.search(r'^(?!(?:\s*\}|\s*\{.*)\s*;?)(?:\s*extern)?\s*(?:int|float|double|char|bool|std::string)\s+\w+\s*=', code_block, re.MULTILINE):
            return 1
        return 0
    elif coding_language == "java":
        if re.search(r'\b(?:public|private|protected)?\s+static\s+(?:int|float|double|char|boolean|String)\s+\w+\s*=', code_block):
            return 1
        return 0
    else:
        return 0

def check_constant_variable(code_block, coding_language):
    coding_language = coding_language.lower()
    if coding_language == "c++":
        if re.search(r'\bconst\s+(?:int|float|double|char|bool|std::string)\s+\w+\s*=', code_block):
            return 1
        return 0
    elif coding_language == "java":
        if re.search(r'\bfinal\s+(?:int|float|double|char|boolean|String)\s+\w+\s*=', code_block):
            return 1
        return 0
    else:
        return 0

def check_keyword_variable_include(code_block, coding_language, keyword):
    coding_language = coding_language.lower()
    pattern = r'\b' + re.escape(keyword) + r'\b'
    code_to_check = code_block

    try:
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

        else:
            # 对于不支持的语言，直接在原始代码中查找
            pass

        # 在处理过的代码中查找关键词
        if re.search(pattern, code_to_check):
            return 1
        return 0

    except re.error as e:
        print(f"Regex error in check_keyword_variable_include for keyword '{keyword}': {e}")
        return 0 # Return 0 on regex error

def check_keyword_variable_number(code_block, coding_language, keyword, number):
    coding_language = coding_language.lower()
    # Store tuples of (lineno, col_offset, name)
    declarations_with_loc = []

    try:
        if coding_language == "python":
            try:
                tree = ast.parse(code_block)
                for node in ast.walk(tree):
                    loc = (float('inf'), float('inf')) # Default location

                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                # Use target's location
                                if hasattr(target, 'lineno'):
                                    loc = (target.lineno, target.col_offset)
                                    declarations_with_loc.append((loc[0], loc[1], target.id))
                            elif isinstance(target, (ast.Tuple, ast.List)): # Handle tuple/list unpacking
                                for elt in target.elts:
                                    if isinstance(elt, ast.Name):
                                        if hasattr(elt, 'lineno'):
                                            loc = (elt.lineno, elt.col_offset)
                                            declarations_with_loc.append((loc[0], loc[1], elt.id))
                    elif isinstance(node, ast.AnnAssign):
                        if isinstance(node.target, ast.Name):
                            if hasattr(node.target, 'lineno'):
                                loc = (node.target.lineno, node.target.col_offset)
                                declarations_with_loc.append((loc[0], loc[1], node.target.id))
                    elif isinstance(node, ast.For):
                        # Handle loop variables
                        target_node = node.target
                        if isinstance(target_node, ast.Name):
                             if hasattr(target_node, 'lineno'):
                                 loc = (target_node.lineno, target_node.col_offset)
                                 declarations_with_loc.append((loc[0], loc[1], target_node.id))
                        elif isinstance(target_node, (ast.Tuple, ast.List)):
                             for elt in target_node.elts:
                                 if isinstance(elt, ast.Name):
                                     if hasattr(elt, 'lineno'):
                                         loc = (elt.lineno, elt.col_offset)
                                         declarations_with_loc.append((loc[0], loc[1], elt.id))
                    # Function/Lambda parameters
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                         args_node = node.args
                         for arg in args_node.args:
                             if hasattr(arg, 'lineno'):
                                 loc = (arg.lineno, arg.col_offset)
                                 declarations_with_loc.append((loc[0], loc[1], arg.arg))
                         for arg in args_node.posonlyargs:
                              if hasattr(arg, 'lineno'):
                                 loc = (arg.lineno, arg.col_offset)
                                 declarations_with_loc.append((loc[0], loc[1], arg.arg))
                         for arg in args_node.kwonlyargs:
                              if hasattr(arg, 'lineno'):
                                 loc = (arg.lineno, arg.col_offset)
                                 declarations_with_loc.append((loc[0], loc[1], arg.arg))
                         if args_node.vararg:
                              arg = args_node.vararg
                              if hasattr(arg, 'lineno'):
                                 loc = (arg.lineno, arg.col_offset)
                                 declarations_with_loc.append((loc[0], loc[1], arg.arg))
                         if args_node.kwarg:
                              arg = args_node.kwarg
                              if hasattr(arg, 'lineno'):
                                 loc = (arg.lineno, arg.col_offset)
                                 declarations_with_loc.append((loc[0], loc[1], arg.arg))
                    # Add other declaration types if needed (e.g., withitem, comprehension targets)

            except SyntaxError as e:
                print(f"Python AST parsing error in check_keyword_variable_number: {e}")
                return 0 # Cannot parse, assume failure

        elif coding_language == "c++" or coding_language == "cpp":
            try:
                index = clang.cindex.Index.create()
                tu = index.parse('temp_source.cpp', args=['-std=c++11'],
                                 unsaved_files=[('temp_source.cpp', code_block)],
                                 options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)

                for node in tu.cursor.walk_preorder():
                    # Capture variable declarations and parameters
                    if node.kind in [clang.cindex.CursorKind.VAR_DECL,
                                     clang.cindex.CursorKind.PARM_DECL,
                                     clang.cindex.CursorKind.FIELD_DECL]:
                        if node.spelling and node.location and node.location.file and node.location.file.name == 'temp_source.cpp': # Ensure it has a name and is from our temp file
                            loc = (node.location.line, node.location.column)
                            declarations_with_loc.append((loc[0], loc[1], node.spelling))

            except clang.cindex.LibclangError as e:
                 print(f"Clang C++ parsing error in check_keyword_variable_number: {e}")
                 return 0
            except FileNotFoundError:
                 print("Error: libclang not found. Ensure LLVM/Clang is installed and accessible.")
                 print("You might need to set the CLANG_LIBRARY_PATH environment variable or use clang.cindex.Config.set_library_path().")
                 return 0
            except Exception as e:
                 print(f"Unexpected error during C++ AST processing in check_keyword_variable_number: {e}")
                 return 0

        elif coding_language == "java":
            try:
                tree = javalang.parse.parse(code_block)

                # Collect Field Declarations
                for _, node in tree.filter(javalang.tree.FieldDeclaration):
                    for declarator in node.declarators:
                        if declarator.position:
                            loc = (declarator.position.line, declarator.position.column)
                            declarations_with_loc.append((loc[0], loc[1], declarator.name))

                # Collect Local Variable Declarations
                for _, node in tree.filter(javalang.tree.LocalVariableDeclaration):
                     for declarator in node.declarators:
                         if declarator.position:
                             loc = (declarator.position.line, declarator.position.column)
                             declarations_with_loc.append((loc[0], loc[1], declarator.name))

                # Collect Formal Parameters (Methods/Constructors)
                for _, node in tree.filter(javalang.tree.FormalParameter):
                     if node.position:
                         loc = (node.position.line, node.position.column)
                         declarations_with_loc.append((loc[0], loc[1], node.name))

            except (javalang.tokenizer.LexerError, javalang.parser.JavaSyntaxError, javalang.tokenizer.EndOfInput) as e:
                print(f"Javalang Java parsing error in check_keyword_variable_number: {e}")
                return 0
            except Exception as e:
                 print(f"Unexpected error during Java AST processing in check_keyword_variable_number: {e}")
                 return 0

        else:
            # Unsupported language for AST analysis
            print(f"Unsupported language for AST-based variable check: {coding_language}")
            return 0 # Fallback or error

        if not declarations_with_loc:
            # print(f"Debug: No declarations found for {coding_language}")
            return 0

        # Sort declarations by line number, then column offset
        declarations_with_loc.sort()

        # Extract sorted variable names
        sorted_variables = [name for line, col, name in declarations_with_loc]

        # Perform the check using the sorted list
        index = number - 1
        if 0 <= index < len(sorted_variables):
            declared_name = sorted_variables[index]
            # print(f"Debug: Sorted variables: {sorted_variables}")
            # print(f"Debug: Checking index {index} ('{declared_name}') against keyword '{keyword}'")
            if declared_name == keyword:
                return 1
        # else:
            # print(f"Debug: Number {number} is out of range for sorted declarations (count: {len(sorted_variables)})")

        return 0

    except Exception as e:
        print(f"General error in check_keyword_variable_number: {e}")
        return 0
    
def check_variable_type_at_position(code_block, coding_language, expected_type, number):
    coding_language = coding_language.lower()
    # Store tuples of (lineno, col_offset, name, declared_type)
    declarations_with_loc_and_type = []

    try:
        if coding_language == "python":
            try:
                tree = ast.parse(code_block)
                for node in ast.walk(tree):
                    loc = (float('inf'), float('inf'))
                    var_name = None
                    type_str = None

                    # Check for annotated assignments
                    if isinstance(node, ast.AnnAssign):
                        if isinstance(node.target, ast.Name):
                            if hasattr(node.target, 'lineno'):
                                loc = (node.target.lineno, node.target.col_offset)
                                var_name = node.target.id
                                type_str = ast.unparse(node.annotation) if node.annotation else None
                    # Check for annotated function arguments
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                         args_node = node.args
                         for arg in args_node.args:
                             if arg.annotation and hasattr(arg, 'lineno'):
                                 loc = (arg.lineno, arg.col_offset)
                                 var_name = arg.arg
                                 type_str = ast.unparse(arg.annotation)
                                 if var_name and type_str:
                                     declarations_with_loc_and_type.append((loc[0], loc[1], var_name, type_str))
                         # Add other arg types if needed (posonly, kwonly, vararg, kwarg) and if they can be annotated

                    if var_name and type_str and loc != (float('inf'), float('inf')):
                         # Avoid adding function args twice if already handled above
                         if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            declarations_with_loc_and_type.append((loc[0], loc[1], var_name, type_str))

            except SyntaxError as e:
                print(f"Python AST parsing error in check_variable_type: {e}")
                return 0 # Cannot parse, assume failure

        elif coding_language == "c++" or coding_language == "cpp":
            try:
                index = clang.cindex.Index.create()
                # Use detailed parsing to potentially find locals if needed later, though type info might be complex
                tu = index.parse('temp_type.cpp', args=['-std=c++11'],
                                 unsaved_files=[('temp_type.cpp', code_block)],
                                 options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)

                for node in tu.cursor.walk_preorder():
                    if node.kind in [clang.cindex.CursorKind.VAR_DECL,
                                     clang.cindex.CursorKind.PARM_DECL,
                                     clang.cindex.CursorKind.FIELD_DECL]:
                        # Ensure the declaration is from the user's code block
                        if node.spelling and node.location and node.location.file and node.location.file.name == 'temp_type.cpp':
                            loc = (node.location.line, node.location.column)
                            var_name = node.spelling
                            var_type = node.type.spelling
                            # Basic cleanup
                            var_type = var_type.replace('const ', '').strip()
                            declarations_with_loc_and_type.append((loc[0], loc[1], var_name, var_type))

            except clang.cindex.LibclangError as e:
                 print(f"Clang C++ parsing error in check_variable_type: {e}")
                 return 0
            except FileNotFoundError:
                 print("Error: libclang not found. Ensure LLVM/Clang is installed and accessible.")
                 return 0
            except Exception as e:
                 print(f"Unexpected error during C++ AST processing in check_variable_type: {e}")
                 return 0

        elif coding_language == "java":
            try:
                tree = javalang.parse.parse(code_block)

                # Using filter might lose order, manually iterate if strict order is needed
                # This approach collects all possible declarations first

                # Fields
                for _, node in tree.filter(javalang.tree.FieldDeclaration):
                    var_type_node = node.type
                    if var_type_node:
                        base_type_name = var_type_node.name
                        if var_type_node.dimensions:
                            base_type_name += '[]' * len(var_type_node.dimensions)
                        for declarator in node.declarators:
                            if declarator.position:
                                loc = (declarator.position.line, declarator.position.column)
                                declarations_with_loc_and_type.append((loc[0], loc[1], declarator.name, base_type_name))

                # Local Variables
                for _, node in tree.filter(javalang.tree.LocalVariableDeclaration):
                    var_type_node = node.type
                    if var_type_node:
                        base_type_name = var_type_node.name
                        if var_type_node.dimensions:
                            base_type_name += '[]' * len(var_type_node.dimensions)
                        for declarator in node.declarators:
                            if declarator.position:
                                loc = (declarator.position.line, declarator.position.column)
                                declarations_with_loc_and_type.append((loc[0], loc[1], declarator.name, base_type_name))

                # Formal Parameters
                for _, node in tree.filter(javalang.tree.FormalParameter):
                     var_type_node = node.type
                     if var_type_node and node.position:
                         base_type_name = var_type_node.name
                         if var_type_node.dimensions:
                             base_type_name += '[]' * len(var_type_node.dimensions)
                         loc = (node.position.line, node.position.column)
                         declarations_with_loc_and_type.append((loc[0], loc[1], node.name, base_type_name))


            except (javalang.tokenizer.LexerError, javalang.parser.JavaSyntaxError, javalang.tokenizer.EndOfInput) as e:
                print(f"Javalang Java parsing error in check_variable_type: {e}")
                return 0
            except Exception as e:
                 print(f"Unexpected error during Java AST processing in check_variable_type: {e}")
                 return 0

        else:
            # Unsupported language
            print(f"Unsupported language for AST analysis: {coding_language}")
            return 0

        if not declarations_with_loc_and_type:
            # print(f"Debug: No declarations with type info found for {coding_language}")
            return 0

        # Sort declarations by line number, then column offset
        declarations_with_loc_and_type.sort()

        # Perform the check using the sorted list
        index = number - 1
        if 0 <= index < len(declarations_with_loc_and_type):
            _, _, _, declared_type = declarations_with_loc_and_type[index] # Get type from sorted list

            # --- Type Comparison Logic ---
            # Normalize expected type for comparison consistency if needed
            norm_expected_type = expected_type.strip()
            norm_declared_type = declared_type.strip()

            # Python: Direct comparison (assuming annotations are consistent)
            if coding_language == "python":
                if norm_declared_type == norm_expected_type:
                    return 1
                # Add more sophisticated checks if needed (e.g., handling Optional, Union)

            # Java: Handle simple vs fully qualified names, primitive vs wrapper might be needed
            elif coding_language == "java":
                if norm_declared_type == norm_expected_type:
                    return 1
                # Check if declared type is qualified and expected is simple
                if '.' in norm_declared_type and '.' not in norm_expected_type:
                    short_declared_type = norm_declared_type.split('.')[-1]
                    if short_declared_type == norm_expected_type:
                        return 1
                # Add checks for primitive vs wrapper if necessary (e.g., int vs Integer)

            # C++: Handle std:: namespace, const qualifiers (already partly handled), pointers/references
            elif coding_language == "c++" or coding_language == "cpp":
                 # Basic check
                 if norm_declared_type == norm_expected_type:
                     return 1
                 # Handle std::string vs string
                 std_norm_declared = norm_declared_type.replace("std::", "")
                 std_norm_expected = norm_expected_type.replace("std::", "")
                 if std_norm_declared == std_norm_expected:
                     return 1
                 # Add more robust C++ type comparison (pointers, references, typedefs etc.) if needed

            # Fallback direct comparison if language specific checks fail
            if norm_declared_type == norm_expected_type:
                 return 1

        # else:
            # print(f"Debug: Number {number} is out of range for sorted declarations with type (count: {len(declarations_with_loc_and_type)})")

        return 0

    except Exception as e:
        # Catch other potential errors during processing
        print(f"General error in check_variable_type_at_position: {e}")
        return 0

def check_function_parameters(code_block, coding_language):
    coding_language = coding_language.lower()
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
        elif coding_language == "c++" or coding_language == "cpp":
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


def check_case(response: str, params, kwargs):
    codes = extract_code_from_text(response)
    coding_language = codes[0]['language']
    code_block = codes[0]['code']
    available_cases = basic_cases.copy()
    #check loops in code_block
    loop_present = check_loop(code_block, coding_language)
    if loop_present:
        if loop_present == 1:
            available_cases += [change_cases[1],change_cases[2]]
        elif loop_present == 2:
            available_cases += [change_cases[0],change_cases[3]]
        elif loop_present == 3:
            available_cases += [change_cases[1],change_cases[3]]
    else:
        available_cases += [change_cases[0],change_cases[2]]
    if_present = check_if(code_block, coding_language)
    if if_present:
        available_cases += [change_cases[5]]
    else:
        available_cases += [change_cases[4]]
    function_present = check_function(code_block, coding_language)
    function_number = 0
    for i in range(len(kwargs)):
        if kwargs[i] == "keyword_function":
            function_number = params[i]["number"]
        elif kwargs[i] == "keyword_function_one":
            function_number = 1
        elif kwargs[i] == "keyword_function_not":
            function_number = 0
    if function_number:
        if function_present != function_number:
            available_cases += [item for item in [change_cases[6],change_cases[7],change_cases[8]] if item[0] in kwargs]
    class_number = 0
    class_present = check_class(code_block, coding_language)
    for i in range(len(kwargs)):
        if kwargs[i] == "keyword_class":
            class_number = params[i]["number"]
        elif kwargs[i] == "keyword_class_one":
            class_number = 1
        elif kwargs[i] == "keyword_class_not":
            class_number = 0
    if class_number:
        if class_present != class_number:
            available_cases += [item for item in [change_cases[9],change_cases[10],change_cases[11]] if item[0] in kwargs]
    built_in_present = check_built_in_function(code_block, coding_language)
    if not built_in_present:
        available_cases += [change_cases[12]]
    comments_present = check_comment(code_block, coding_language)
    if comments_present:
        available_cases += [change_cases[13]]
    else:
        available_cases += [change_cases[14]]
    global_variable_present = check_global_variable(code_block, coding_language)
    if global_variable_present:
        available_cases += [change_cases[16]]
    else:
        available_cases += [change_cases[15]]
    if(coding_language != "python"):
        constant_variable_present = check_constant_variable(code_block, coding_language)
        if constant_variable_present:
            available_cases += [change_cases[18]]
        else:
            available_cases += [change_cases[17]]
    code_lines_limit = 0
    for i in range(len(kwargs)):
        if kwargs[i] == "code_lines":
            code_lines_limit = params[i]["number"]
    code_lines = len(code_block.split('\n'))
    if code_lines_limit != 0:
        if code_lines > code_lines_limit:
            available_cases += [change_cases[19]]
    if "keyword_variable_include" in kwargs:
        keyword_variable = params[kwargs.index("keyword_variable_include")]["name"]
        if check_keyword_variable_include(code_block, coding_language, keyword_variable) == 0:
            available_cases += [change_cases[20]]
    if "keyword_variable_number" in kwargs:
        keyword_variable = params[kwargs.index("keyword_variable_number")]["name"]
        keyword_variable_number = params[kwargs.index("keyword_variable_number")]["number"]
        if check_keyword_variable_number(code_block, coding_language, keyword_variable, keyword_variable_number) == 0:
            available_cases += [change_cases[21]]
    if "keyword_variable_type" in kwargs:
        keyword_variable_type = params[kwargs.index("keyword_variable_type")]["type"]
        keyword_variable_number = params[kwargs.index("keyword_variable_type")]["number"]
        if check_variable_type_at_position(code_block, coding_language, keyword_variable_type, keyword_variable_number) == 0:
            available_cases += [change_cases[22]]
    if "coding_language" in kwargs:
        coding_language = params[kwargs.index("coding_language")]["language"]
        if codes[0]['language'].lower() == "c++" or codes[0]['language'].lower() == "cpp":
            codes[0]['language'] = "c++"
        if coding_language.lower() == "c++" or coding_language.lower() == "cpp":
            coding_language = "c++"
        if coding_language.lower() != codes[0]['language'].lower():
            print(coding_language)
            print(codes[0]['language'])
            available_cases += [change_cases[23]]
    if "function_parameters_min" in kwargs:
        function_parameters_min = params[kwargs.index("function_parameters_min")]["number"]
        code_parameters_min = check_function_parameters(code_block, coding_language)[1]
        if code_parameters_min < function_parameters_min:
            available_cases += [change_cases[24]]
    if "function_parameters_max" in kwargs:
        function_parameters_max = params[kwargs.index("function_parameters_max")]["number"]
        code_parameters_max = check_function_parameters(code_block, coding_language)[0]
        if code_parameters_max > function_parameters_max:
            available_cases += [change_cases[25]]
    
    return available_cases

def create_problem_prompt(problem_data: Dict[str, Any]) -> str:
    """Create an initial prompt from the problem data."""
    prompt = f"Problem: {problem_data.get('question_title', '')}\n\n"
    prompt += f"{problem_data.get('question_content', '')}\n\n"
    
    # Add test cases if available
    if 'public_test_cases' in problem_data:
        try:
            test_cases = json.loads(problem_data['public_test_cases'])
            if isinstance(test_cases, list) and len(test_cases) > 0:
                prompt += "Test Cases:\n"
                for i, tc in enumerate(test_cases):
                    prompt += f"Input {i+1}:\n{tc.get('input', '')}\n"
                    prompt += f"Output {i+1}:\n{tc.get('output', '')}\n\n"
        except (json.JSONDecodeError, TypeError):
            pass
    
    prompt += "Please write code to solve this problem."
    problem_data['prompt'] = prompt

# Define the function to interact with OpenAI API
def model_responses(prompt: List[Dict[str, str]], model: str, max_tokens: int = 500, 
                    temperature: float = 0, max_retries: int = 10, api_key: str = "your_api_key") -> Optional[str]:
    """Generate a response using OpenAI API."""
    retries = 0
    answer = None

    while retries < max_retries:
        try:
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )
            response = client.chat.completions.create(
                model=model,
                messages=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            #print(response)
            answer = response.choices[0].message.content
            # Skip if content is prohibited
            if answer == "PROHIBITED_CONTENT":
                print("Skipping prohibited content")
                return None
            #print(answer)
            return answer

        except Exception as e:
            print(f"调用失败: {str(e)}，将重试……")
            retries += 1
            if retries >= max_retries:
                print("达到最大重试次数，返回最后一次响应")
                return None

def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """Load data from a JSONL file."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

def save_jsonl(data: List[Dict[str, Any]], file_path: str) -> None:
    """Save data to a JSONL file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

def create_initial_prompt(item: Dict[str, Any]) -> List[Dict[str, str]]:
    """Create the initial prompt for a programming problem."""
    create_problem_prompt(item)
    # Format as a proper user prompt with context
    initial_prompt = [
        {"role": "system", "content": """
        You are a highly capable coding assistant tasked with generating complete, runnable code based on the provided problem description. Follow these guidelines strictly:
        1.Generate a complete, fully functional program that can be executed without errors.
        2.If the problem requires a Java program, include a main class with a public static void main() method.
        3.Use clear, concise, and well-structured code following standard programming practices for the specified language.
        If the problem involves input, handle it appropriately (e.g., reading from standard input using Scanner in Java, or equivalent in other languages).
        4.If no programming language is specified, default to Python for its simplicity and versatility.
        5.Ensure the code is robust and can handle all possible valid inputs, not just specific test cases, while adhering to the problem's constraints and requirements. 
         """
            },
        {"role": "user", "content": item['prompt'] + "\n\nImportant requirements:\n1. Write a COMPLETE Python program, not just a function.\n2. Include proper input handling code to read data directly (don't assume variables are pre-defined).3. Call your main function directly at the end of the program.\n4. Include all necessary imports.\n5. The program should be ready to run without any modifications.\n\nThe test cases are provided to help you understand the problem, but your solution must work for all valid inputs."}
    ]
    return initial_prompt

def create_turn_prompt(item: Dict[str, Any], turn_number: int, conversation_history: List[Dict[str, str]]) -> Optional[List[Dict[str, str]]]:
    """Create a prompt for a specific turn using the full conversation history."""
    turn_key = f"turn{turn_number}_prompt"
    
    if turn_key not in item:
        return None
    
    # Start with the full conversation history
    full_prompt = conversation_history.copy()
    
    # Add the new user turn with detailed context
    user_prompt = {"role": "user", "content": item[turn_key]}
    full_prompt.append(user_prompt)
    conversation_history.append(user_prompt)
    
    return full_prompt

def generate_random_variable_name() -> str:
    """Generate a random variable name."""
    prefixes = ['var', 'my', 'temp', 'data', 'result', 'value', 'count', 'index', 'item', 'element']
    return random.choice(prefixes) + str(random.randint(1, 100))

def generate_random_number(min_val=1, max_val=4) -> int:
    """Generate a random number within a range."""
    return random.randint(min_val, max_val)

def generate_random_type(language: str = "Python") -> str:
    """Generate a random variable type based on the programming language."""
    language = language.lower()
    
    # Language-specific type dictionaries
    types = {
        "python": ['int', 'float', 'str', 'list', 'dict', 'bool', 'set', 'tuple'],
        "java": ['int', 'double', 'String', 'ArrayList', 'HashMap', 'boolean', 'char', 'long'],
        "c++": ['int', 'double', 'string', 'vector', 'map', 'bool', 'char', 'long']
    }
    
    # Default to Python if language not in the dictionary
    return random.choice(types.get(language, types["python"]))

def generate_random_language(coding_language) -> str:
    """Generate a random programming language."""
    languages = ['Python', 'Java', 'C++']
    # Ensure the generated language is different from the coding_language
    if coding_language in languages:
        languages.remove(coding_language)
    return random.choice(languages)

def generate_random_time() -> int:
    """Generate a random time limit in milliseconds."""
    return random.randint(1000, 5000)

def generate_random_storage() -> int:
    """Generate a random storage limit in kb."""
    return random.randint(10240, 65536)

def generate_random_format() -> str:
    """Generate a random output format."""
    formats = [
        '{ output }',
        '[ output ]',
        '( output )',
    ]
    return random.choice(formats)

def get_ordinal_suffix(num: int) -> str:
    """Return the correct ordinal suffix (st, nd, rd, th)."""
    if 11 <= num % 100 <= 13:
        return "th"
    else:
        return {1: "st", 2: "nd", 3: "rd"}.get(num % 10, "th")

def create_turn_instruction(available_cases: List[tuple], item: Dict[str, Any], turn_number: int, response, result, turn_cases) -> None:
    """
    Create instruction for a specific turn by keeping all cases in turn_cases
    and generating parameters for each of them
    
    Args:
        available_cases: List of available case tuples (case_type, templates)
        item: The item dictionary to modify
        turn_number: Current turn number
        response: The previous model response
        selected: List of previously selected case types
        contradict: List of contradictory case type pairs
        result: Dictionary to store results
        turn_cases: List of cases to keep
    """
    codes = extract_code_from_text(response)
    coding_language = codes[0]['language']
    code_block = codes[0]['code']
    if turn_number != 1:
        params = item[f'turn{turn_number-1}_params']
        kwargs = item[f'turn{turn_number-1}_kwargs']
    # Check if we have any available cases
    if not available_cases:
        print(f"Warning: No available cases for turn {turn_number}")
        return
    
    # Keep only cases that are in turn_cases and are non-contradictory
    final_turn_cases = []
    for case in available_cases:
        if case in turn_cases:
            final_turn_cases.append(case)
    
    if turn_number == 1:
        result[f'turn{turn_number}_available'] = [case[0] for case in final_turn_cases]
    else:
        final_turn_cases = [case for case in final_turn_cases if case not in basic_cases]
        result[f'turn{turn_number}_available'] = [case[0] for case in final_turn_cases]
    
    # If we don't have any valid cases left, use the original available cases
    if not final_turn_cases:
        print(f"Success: No valid cases left for turn {turn_number}")
        return True
    
    # Process all cases instead of picking just one
    all_prompts = []
    all_case_types = []
    all_params = []  # Store all parameter dictionaries
    
    for case_type, templates in final_turn_cases:
        # Create a new parameters dictionary for each case
        if turn_number != 1:
            index = kwargs.index(case_type) if case_type in kwargs else -1
            if index == -1:
                print(f"Warning: {case_type} not found in kwargs for turn {turn_number}")
        params_dict = {}
        
        # Handle specific cases that need parameters
        if case_type == 'keyword_variable_include':
            if turn_number != 1:
                var_name = params[index]['name']
                params_dict['name'] = var_name
                #all_prompts.append(f"Your code did not include the variable '{var_name}'.")
            else:
                var_name = generate_random_variable_name()
                params_dict['name'] = var_name
            
        elif case_type == 'keyword_variable_number':
            if turn_number != 1:
                var_name = params[index]['name']
                number = params[index]['number']
                suffix = params[index]['suffix']
                params_dict['name'] = var_name
                params_dict['number'] = number
                params_dict['suffix'] = suffix
                #all_prompts.append(f"Your code did not include the variable '{var_name}' at position {number}{suffix}.")
            else:
                var_name = generate_random_variable_name()
                number = generate_random_number(1, 4)
                suffix = get_ordinal_suffix(number)
                params_dict['name'] = var_name
                params_dict['number'] = number
                params_dict['suffix'] = suffix
            
        elif case_type == 'keyword_variable_type':
            if turn_number != 1:
                number = params[index]['number']
                suffix = params[index]['suffix']
                var_type = params[index]['type']
                params_dict['number'] = number
                params_dict['suffix'] = suffix
                params_dict['type'] = var_type
                #all_prompts.append(f"Your code did not include the '{var_type}' variable at position {number}{suffix}.")
            else:
                number = generate_random_number(1, 4)
                suffix = get_ordinal_suffix(number)
                language = coding_language
                var_type = generate_random_type(language)
                params_dict['number'] = number
                params_dict['suffix'] = suffix
                params_dict['type'] = var_type
            
        elif case_type == 'keyword_function':
            if turn_number != 1:
                number = params[index]['number']
                function_form = params[index]['function_form']
                params_dict['number'] = number
                params_dict['function_form'] = function_form
                #all_prompts.append(f"Your code did not include {number} {function_form}.")
            else: 
                number = generate_random_number(2, 3)
                function_form = "function" if number == 1 else "functions"
                params_dict['number'] = number
                params_dict['function_form'] = function_form
            
        elif case_type == 'keyword_function_one':
            if turn_number != 1:
                function_form = params[index]['function_form']
                params_dict['function_form'] = function_form
                #all_prompts.append(f"Your code did not include one {function_form}.")
            else:
                function_form = "function"
                params_dict['function_form'] = function_form
            
        elif case_type == 'keyword_class':
            if turn_number != 1:
                number = params[index]['number']
                class_form = params[index]['class_form']
                params_dict['number'] = number
                params_dict['class_form'] = class_form
                #all_prompts.append(f"Your code did not include {number} {class_form}.")
            else:           
                number = generate_random_number(2, 3)
                class_form = "class" if number == 1 else "classes"
                params_dict['number'] = number
                params_dict['class_form'] = class_form
            
        elif case_type == 'keyword_class_one':
            if turn_number != 1:
                class_form = params[index]['class_form']
                params_dict['class_form'] = class_form
                #all_prompts.append(f"Your code did not include one {class_form}.")
            else:
                class_form = "class"
                params_dict['class_form'] = class_form
            
        elif case_type == 'coding_language':
            if turn_number != 1:
                language = params[index]['language']
                params_dict['language'] = language
                #all_prompts.append(f"Your code did not write in {language}.")
            else:
                language = generate_random_language(coding_language)
                params_dict['language'] = language
            
        elif case_type == 'time_limit':
            time = generate_random_time()
            params_dict['time'] = time
            
        elif case_type == 'storage_limit':
            storage = generate_random_storage()
            params_dict['storage'] = storage
            
        elif case_type == 'output_format':
            format_type = generate_random_format()
            params_dict['format'] = format_type
            
        elif case_type == 'code_lines':
            if turn_number != 1:
                code_lines_limit = params[index]['number']
                params_dict['number'] = code_lines_limit
                #all_prompts.append(f"Your code has more than {code_lines_limit} lines.")
            else:
                code_lines = len(code_block.split('\n'))
                number = max(5, code_lines - random.randint(int(code_lines/8), int(code_lines/4)))
                params_dict['number'] = number
        
        elif case_type == 'function_parameters_min' or case_type == 'function_parameters_max':
            if turn_number != 1:
                number = params[index]['number']
                params_dict['number'] = number
                """
                if case_type == 'function_parameters_min':
                    all_prompts.append(f"Your code has less than {number} parameters.")
                else:
                    all_prompts.append(f"Your code has more than {number} parameters.")
                """
            else:
                number = generate_random_number(1, 4)
                params_dict['number'] = number
        """        
        elif case_type == 'keyword_for':
            if turn_number != 1:
                all_prompts.append("Your code did not include a for loop.")
        elif case_type == 'keyword_for_not':
            if turn_number != 1:
                all_prompts.append("Your code include for loops.")
        elif case_type == 'keyword_while':
            if turn_number != 1:
                all_prompts.append("Your code did not include a while loop.")
        elif case_type == 'keyword_while_not':
            if turn_number != 1:
                all_prompts.append("Your code include while loops.")
        elif case_type == 'keyword_if':
            if turn_number != 1:
                all_prompts.append("Your code did not include an if statement.")
        elif case_type == 'keyword_if_not':
            if turn_number != 1:
                all_prompts.append("Your code include if statements.")
        elif case_type == 'keyword_function_not':
            if turn_number != 1:
                all_prompts.append("Your code include functions.")
        elif case_type == 'keyword_class_not':
            if turn_number != 1:
                all_prompts.append("Your code include classes.")
        elif case_type == 'built_in_function':
            if turn_number != 1:
                all_prompts.append("Your code include functions that are not built-in.")
        elif case_type == 'coding_style_include':
            if turn_number != 1:
                all_prompts.append("Your code still have some comments.")
        elif case_type == 'coding_style':
            if turn_number != 1:
                all_prompts.append("Your code did not include any comments.")
        elif case_type == 'global_variable':
            if turn_number != 1:
                all_prompts.append("Your code did not include global variables.")
        elif case_type == 'global_variable_not':
            if turn_number != 1:
                all_prompts.append("Your code include global variables.")
        elif case_type == 'constant_variable':
            if turn_number != 1:
                all_prompts.append("Your code did not include constant variables.")
        elif case_type == 'constant_variable_not':
            if turn_number != 1:
                all_prompts.append("Your code include constant variables.")
        """        
        # Randomly select a template for this case type
        template = random.choice(templates)
        
        try:
            prompt = template.format(**params_dict) if params_dict else template
            all_prompts.append(prompt)
            all_case_types.append(case_type)
            all_params.append(params_dict)  # Store the parameter dictionary
        except KeyError as e:
            print(f"Error formatting template for {case_type}: {e} - skipping this case")
    
    # Store all generated case types, parameter dictionaries, and prompts in the item
    item[f'turn{turn_number}_kwargs'] = all_case_types
    item[f'turn{turn_number}_params'] = all_params  # Store the parameter dictionaries
    item[f'turn{turn_number}_prompt'] = "Please revise the provided code to meet the following requirements:\n" + "\n".join([f"{i+1}. {req}" for i, req in enumerate(all_prompts)])  # Combine all prompts
    
    # Store in result as well
    result[f'turn{turn_number}_kwargs'] = all_case_types
    result[f'turn{turn_number}_params'] = all_params
    result[f'turn{turn_number}_prompt'] = "Please revise the provided code to meet the following requirements:\n" + "\n".join([f"{i+1}. {req}" for i, req in enumerate(all_prompts)])
    
    if(turn_number != 1):
        result[f'turn{turn_number}_prompt'] = random.choice(["The code you just wrote didn't completely fulfill my requirements.", "The code you just provided did not fully address my needs.", "There are still some bugs in the code you just provided.", "The code you just made still has these errors."]) + result[f'turn{turn_number}_prompt']
        item[f'turn{turn_number}_prompt'] = random.choice(["The code you just wrote didn't completely fulfill my requirements.", "The code you just provided did not fully address my needs.", "There are still some bugs in the code you just provided.", "The code you just made still has these errors."]) + item[f'turn{turn_number}_prompt']
    
    item[f'turn{turn_number}_prompt'] += "And please remain other requirements in the previous prompt."
    result[f'turn{turn_number}_prompt'] += "And please remain other requirements in the previous prompt." 
    
    return False

def process_multi_turn_conversation(item: Dict[str, Any], api_key: str,
                                   model: str, max_tokens: int,
                                   temperature: float, max_turns: int = 10) -> Dict[str, Any]: # Modified signature to accept parameters directly
    """Process a complete multi-turn conversation for a single item."""
    result_item = item.copy()
    conversation_history = []
    # Generate the initial response
    initial_prompt = create_initial_prompt(item)
    result_item["prompt_turn0"] = initial_prompt
    conversation_history = copy.deepcopy(initial_prompt)

    # generate the turns number
    max_res_turns = max_turns

    try:
        initial_response = model_responses(initial_prompt, model, max_tokens, temperature, api_key=api_key)
        if initial_response is None:
            # Handle the case where the initial response failed
            print(f"Warning: Initial response failed for item. Skipping further processing.")
            result_item["error"] = "Initial API call failed"
            result_item["conversation_history"] = conversation_history # Save history up to failure
            return result_item # Return early

        result_item["model_response_turn0"] = initial_response
        conversation_history.append({"role": "assistant", "content": initial_response})
        last_response = initial_response
        # Process subsequent turns
        contradictory_pairs = [
        # Loop contradictions
        ('keyword_for', 'keyword_for_not'),
        ('keyword_while', 'keyword_while_not'),
        # Statement contradictions
        ('keyword_if', 'keyword_if_not'),
        # If both for and while are not allowed, it's hard to write code
        ('keyword_for_not', 'keyword_while_not'),
        # Global variable contradictions
        ('global_variable', 'global_variable_not'),
        # Others can be added as needed
        ('keyword_function', 'keyword_function_not'),
        ('keyword_function_one', 'keyword_function_not'),
        ('keyword_class', 'keyword_class_not'),
        ('keyword_class_one', 'keyword_class_not'),
        ('coding_style', 'coding_style_include'),
        ('global_variable', 'global_variable_not'),
        ('constant_variable', 'constant_variable_not'),
        ('keyword_if_not', 'keyword_while_not')
        ]
        initial_cases = item['case_types']
        end_turns = 0
        for turn in range(1, max_res_turns + 1):
            if turn != 1:
                params = item.get(f'turn{turn-1}_params') # Use .get for safety
                kwargs = item.get(f'turn{turn-1}_kwargs') # Use .get for safety
                if params is None or kwargs is None:
                    print(f"Warning: Missing params/kwargs for turn {turn-1}. Cannot check case.")
                    available_cases = [] # Cannot determine available cases
                else:
                    available_cases = check_case(last_response, params, kwargs)
            else:
                available_cases = initial_cases

            # Ensure create_turn_instruction handles empty available_cases gracefully if needed
            end = create_turn_instruction(available_cases, item, turn, last_response, result_item, initial_cases)

            if end:
                end_turns = turn - 1
                break

            # Check if the prompt was actually created before proceeding
            if f'turn{turn}_prompt' not in item:
                print(f"Warning: Prompt for turn {turn} was not generated. Stopping conversation.")
                end_turns = turn - 1 # Record the last successful turn
                break

            turn_prompt = create_turn_prompt(item, turn, conversation_history)
            if turn_prompt is None:
                print(f"Warning: Failed to create turn prompt for turn {turn}. Stopping conversation.")
                end_turns = turn - 1 # Record the last successful turn
                break

            result_item[f"prompt_turn{turn}"] = turn_prompt
            turn_response = model_responses(turn_prompt, model, max_tokens, temperature, api_key=api_key)

            if turn_response is None:
                # Handle API call failure within the loop
                print(f"Warning: API call failed for turn {turn}. Stopping conversation.")
                result_item["error"] = f"API call failed at turn {turn}"
                end_turns = turn - 1 # Record the last successful turn
                break # Stop processing this item

            last_response = turn_response
            result_item[f"model_response_turn{turn}"] = turn_response
            conversation_history.append({"role": "assistant", "content": turn_response})

        if end_turns == 0 and not result_item.get("error"): # If loop finished naturally
             end_turns = max_res_turns
        result_item["end_turns"] = end_turns

    except Exception as e:
        print(f"Error processing item: {e}")
        result_item["error"] = str(e) # Record the error

    result_item["conversation_history"] = conversation_history
    return result_item

def main():
    parser = argparse.ArgumentParser(description="Process multi-turn LLM interaction for programming problems with parallelism")
    parser.add_argument("--model_name", type=str, default="deepseek/deepseek-r1",
                        help="Model name to use for API calls")
    parser.add_argument("--input_file", type=str, default="new_try\output\real_experiment\decoded_data.jsonl",
                        help="Path to input JSONL file")
    parser.add_argument("--output_file", type=str, default="new_try\output\real_experiment\ex_result_deepseek_r1.jsonl",
                        help="Path to output JSONL file")
    parser.add_argument("--max_tokens", type=int, default=8192,
                        help="Maximum tokens for model response")
    parser.add_argument("--temperature", type=float, default=0,
                        help="Temperature for model response (0-1)")
    parser.add_argument("--max_turns", type=int, default=5,
                        help="Maximum conversation turns")
    parser.add_argument("--api_key", type=str, required=True,
                        help="API key for OpenRouter")
    parser.add_argument("--parallelism", type=int, default=8,
                        help="Number of parallel threads for processing")
    
    args = parser.parse_args()

    print(f"从 {args.input_file} 加载数据")
    data = load_jsonl(args.input_file)

    print(f"为 {len(data)} 个问题生成多轮回复 (并行度: {args.parallelism})")

    # Use functools.partial to pre-fill arguments for the worker function
    worker_func = partial(process_multi_turn_conversation,
                          api_key=args.api_key,
                          model=args.model_name,
                          max_tokens=args.max_tokens,
                          temperature=args.temperature,
                          max_turns=args.max_turns)

    results = []
    # Use ThreadPoolExecutor for I/O-bound tasks like API calls
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallelism) as executor:
        # Use executor.map to apply the function in parallel
        results_iterator = executor.map(worker_func, data)
        results = list(tqdm(results_iterator, total=len(data), desc="处理问题", unit="问题"))

    print(f"保存结果到 {args.output_file}")
    save_jsonl(results, args.output_file)
    print("完成!")

if __name__ == "__main__":
    main()
        