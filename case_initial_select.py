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
import collections

change_cases = [
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
    ('coding_style', ['Please revise your code and ensure it contains no comments.', 'Kindly update your code to exclude any comments in the implementation.', 'Could you modify your code to remove all comments?', 'We recommend refactoring your code to omit any comments entirely.', 'It would be appreciated if you could adjust your code to be free of comments.']),
    ('coding_style_include', ['Please revise your code and ensure it contains comments.', 'Kindly update your code to include comments in the implementation.', 'Could you modify your code to add comments?', 'We recommend refactoring your code to include comments for clarity.', 'It would be appreciated if you could adjust your code to have comments.']),
    ('global_variable', ['Please revise your code to use at least one global variable.', 'Kindly update your code to include a global variable in the implementation.', 'Could you modify your code to ensure it contains a global variable?', 'We recommend refactoring your code to integrate a global variable into the logic.', 'It would be appreciated if you could adjust your code to include a global variable.']),
    ('global_variable_not', ['Please revise your code to exclude any global variables in the implementation.', 'Kindly update your code to ensure it does not contain any global variables.', 'Could you modify your code to avoid using global variables entirely?', 'We recommend refactoring your code to remove any global variables from the logic.', 'It would be appreciated if you could adjust your code to omit global variables.']),
    ('constant_variable', ['Please revise your code to use at least one constant variable.', 'Kindly update your code to include a constant variable in the implementation.', 'Could you modify your code to ensure it contains a constant variable?', 'We recommend refactoring your code to integrate a constant variable into the logic.', 'It would be appreciated if you could adjust your code to include a constant variable.']),
    ('constant_variable_not', ['Please revise your code to exclude any constant variables in the implementation.', 'Kindly update your code to ensure it does not contain any constant variables.', 'Could you modify your code to avoid using constant variables entirely?', 'We recommend refactoring your code to remove any constant variables from the logic.', 'It would be appreciated if you could adjust your code to omit constant variables.']),
    ('code_lines', ['Please revise your code to contain at most {number} lines of code.', 'Kindly update your code to limit the number of lines to {number}.', 'Could you modify your code to ensure it does not exceed {number} lines?', 'We recommend refactoring your code to reduce the number of lines to {number}.', 'It would be appreciated if you could adjust your code to have at most {number} lines.']),
    ('function_parameters_max', ['All Your function should have at most {number} parameters.', 'Please revise your code to ensure that all functions have at most {number} parameters.', 'Kindly update your code to limit the number of parameters in each function to {number}.', 'Could you modify your code to ensure that no function has more than {number} parameters?', 'We recommend refactoring your code to restrict all functions to a maximum of {number} parameters.', 'It would be appreciated if you could adjust your code to ensure that all functions have at most {number} parameters.']),
    ('function_parameters_min', ['All Your function should have at least {number} parameters.', 'Please revise your code to ensure that all functions have at least {number} parameters.', 'Kindly update your code to require a minimum of {number} parameters in each function.', 'Could you modify your code to ensure that no function has fewer than {number} parameters?', 'We recommend refactoring your code to restrict all functions to a minimum of {number} parameters.', 'It would be appreciated if you could adjust your code to ensure that all functions have at least {number} parameters.'])
]

basic_cases = [
    ('keyword_variable_include', ['Kindly revise your code to incorporate {name} as a variable identifier.', 'Please refactor your code to include {name} as a variable name.', 'Could you modify your code to use {name} as a variable name?', 'We recommend updating your code to utilize {name} as a variable name.', 'It would be appreciated if you could rewrite your code with {name} as a variable name.']),
    ('keyword_variable_number', ['Please revise your code to position {name} as the {number}{suffix} variable in the sequence.', 'Kindly refactor your code to assign {name} as the {number}{suffix} variable in the list.', 'Could you update your code to ensure {name} is the {number}{suffix} variable in the order?', 'We recommend modifying your code to make {name} the {number}{suffix} variable in the structure.', 'It would be appreciated if you could adjust your code to set {name} as the {number}{suffix} variable.']),
    ('keyword_variable_type', ['Please modify your code to ensure the {number}{suffix} variable is of type {type}.', 'Kindly update your code to define the {number}{suffix} variable as a {type} variable.', 'Could you revise your code to make the {number}{suffix} variable a {type} variable?', 'We recommend refactoring your code to set the {number}{suffix} variable as a {type} variable.', 'It would be appreciated if you could adjust your code to make the {number}{suffix} variable a {type}.']),
    ('coding_language', ['Please revise your code to be written in {language}.', 'Kindly update your code to conform to the {language} programming language.', 'Could you modify your code to be implemented in {language}?', 'We recommend refactoring your code to be written in {language}.', 'It would be appreciated if you could adjust your code to be written in {language}.']),
    ('time_limit', ['Please revise your code to ensure it executes within {time} milliseconds.', 'Kindly update your code to optimize its runtime to be within {time} ms.', 'Could you modify your code to guarantee its execution time does not exceed {time} milliseconds?', 'We recommend refactoring your code to achieve a runtime of {time} ms or less.', 'It would be appreciated if you could adjust your code to run within {time} milliseconds.']),
    ('storage_limit', ['Please revise your code to ensure its memory usage remains below {storage} kilobytes.', 'Kindly update your code to optimize its memory consumption to less than {storage} KB.', 'Could you modify your code to guarantee its memory usage does not exceed {storage} kilobytes?', 'We recommend refactoring your code to limit its memory footprint to under {storage} KB.', 'It would be appreciated if you could adjust your code to use less than {storage} KB of memory.']),
    ('output_format', ['Please revise your code to ensure the output adheres to the {format} format.', 'Kindly update your code to generate output strictly in the {format} format.', 'Could you modify your code to guarantee the output conforms to the {format} format?', 'We recommend refactoring your code to produce output in the {format} format.', 'It would be appreciated if you could adjust your code to output data in the {format} format.'])
]

def extract_code_from_text(text):
    """
    Extract code blocks from text and identify their programming language type

    Parameters:
        text: The text content containing code blocks

    Returns:
        A list of extracted code information, each item containing language and code
    """
    # Store all extracted code blocks and their language information
    extracted_codes = []
    
    # Find all code blocks
    pos = 0
    while True:
        # Find the start marker of a code block
        start_marker_pos = text.find("```", pos)
        if start_marker_pos == -1:
            break
            
        # Find the language identifier, which follows ```
        language_start = start_marker_pos + 3
        language_end = text.find("\n", language_start)
        if language_end == -1:
            pos = start_marker_pos + 3
            continue
            
        language = text[language_start:language_end].strip()
        
        # Start position of the code block content
        code_start = language_end + 1
        
        # Find the end marker of the code block
        code_end = text.find("```", code_start)
        if code_end == -1:
            break
            
        code_block = text[code_start:code_end].strip()

        # Check for separator lines in the code block
        lines = code_block.split('\n')
        for i, line in enumerate(lines):
            # Print debug information
            #print(f"Debug info: '{line}'")
            
            # Use regex to match separator lines (composed of multiple '-')
            if re.match(r"^-+$", line.strip()):  # Match any number of consecutive `-`
                print(f"Found separator line: {line.strip()}")
                # Found a separator line, keep only the content before it
                code_block = '\n'.join(lines[:i]).strip()
                break

        # Store the code block and language information
        extracted_codes.append({
            "language": language,
            "code": code_block
        })
                
        # Update position to find the next code block
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
    """Check if the code contains an if statement"""
    coding_language = coding_language.lower()
    
    # Remove string literals and comments to avoid false positives
    if coding_language == "python":
        # Remove strings and comments
        code_no_strings = re.sub(r'"[^"]*"', '', code_block)
        code_no_strings = re.sub(r"'[^']*'", '', code_no_strings)
        code_no_strings = re.sub(r'#.*$', '', code_no_strings, flags=re.MULTILINE)
        
        # Use word boundaries to check for actual if statements
        return 1 if re.search(r'\bif\b', code_no_strings) else 0
        
    elif coding_language in ["c++", "java"]:
        # Remove strings and comments
        code_no_strings = re.sub(r'"[^"]*"', '', code_block)
        code_no_strings = re.sub(r"'[^']*'", '', code_no_strings)
        code_no_strings = re.sub(r'//.*$', '', code_no_strings, flags=re.MULTILINE)
        code_no_strings = re.sub(r'/\*[\s\S]*?\*/', '', code_no_strings)
        
        # Use word boundaries to check for actual if statements
        return 1 if re.search(r'\bif\b', code_no_strings) else 0
    
    # Return 0 for unsupported languages
    return 0

def check_function(code_block, coding_language):
    coding_language = coding_language.lower()
    if coding_language == "python":
        if re.search(r'\bdef\s+\w+\s*$$ ', code_block):
            return 1
        return 0
    elif coding_language == "c++":
        if re.search(r'\b(?:void|int|float|double|char|bool|std::string)\s+\w+\s*\(', code_block):
            return 1
        return 0
    elif coding_language == "java":
        if re.search(r'\b(?:public|private|protected)?\s*(?:static)?\s*(?:void|int|float|double|char|boolean|String)\s+\w+\s*\(', code_block):
            return 1
        return 0
    else:
        return 0

def check_class(code_block, coding_language):
    coding_language = coding_language.lower()
    if coding_language == "python":
        if re.search(r'\bclass\s+\w+\s*:', code_block):
            return 1
        return 0
    elif coding_language == "c++":
        if re.search(r'\b(?:public:|private:|protected:)?\s*class\s+\w+\s*{', code_block):
            return 1
        return 0
    elif coding_language == "java":
        if re.search(r'\b(?:public|private|protected)?\s*(?:abstract)?\s*class\s+\w+\s*{', code_block):
            return 1
        return 0
    else:
        return 0

def check_built_in_function(code_block, coding_language):
    coding_language = coding_language.lower()
    if coding_language == "python":
        # Check for imports of non-built-in libraries
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
        # Find all imported libraries
        import_lines = re.findall(r'^(?:import\s+(\S+)|from\s+(\S+)\s+import)', code_block, re.MULTILINE)
        imported_libs = []
        for match in import_lines:
            if match[0]:
                imported_libs.append(match[0])
            elif match[1]:
                imported_libs.append(match[1])

        # Check if all imported libraries are in allowed_libraries
        for lib in imported_libs:
            if lib not in allowed_libraries:
                return False  # Found a disallowed library
        return True  # All imported libraries are allowed
    elif coding_language == "c++":
        # Check include statements, only allow standard libraries
        includes = re.findall(r'#include\s*<([^>]+)>', code_block)
        standard_headers = {
            'iostream', 'string', 'vector', 'map', 'set', 'algorithm', 'cmath',
            'cstdlib', 'ctime', 'cstring', 'cassert', 'queue', 'stack', 'deque'
        }
        return all(header in standard_headers for header in includes)
    elif coding_language == "java":
        # Check import statements, only allow java. packages
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
    elif coding_language == "c++":
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
        if re.search(r'^(?!(?:\s*def|\s*class)\s+\w+\s*\(?:\w+\s*,\s*\w+ $$?\s*:).*?\b\w+\s*=\s*.*', code_block, re.MULTILINE | re.DOTALL):
            return 1
        return 0
    elif coding_language == "c++":
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

def check_case(response: str):
    codes = extract_code_from_text(response)
    coding_language = codes[0]['language']
    code_block = codes[0]['code']
    available_cases = basic_cases.copy()
    # Check loops in code_block
    loop_present = check_loop(code_block, coding_language)
    if loop_present:
        if loop_present == 1:
            available_cases += [change_cases[1], change_cases[2]]
        elif loop_present == 2:
            available_cases += [change_cases[0], change_cases[3]]
        elif loop_present == 3:
            available_cases += [change_cases[1], change_cases[3]]
    else:
        available_cases += [change_cases[0], change_cases[2]]
    if_present = check_if(code_block, coding_language)
    if if_present:
        available_cases += [change_cases[5]]
    else:
        available_cases += [change_cases[4]]
    function_present = check_function(code_block, coding_language)
    if function_present:
        available_cases += [change_cases[6], change_cases[7], change_cases[20], change_cases[21]]
    else:
        available_cases += [change_cases[8]]
    class_present = check_class(code_block, coding_language)
    if class_present:
        available_cases += [change_cases[9], change_cases[10]]
    else:
        available_cases += [change_cases[11]]
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
    if coding_language != "python":
        constant_variable_present = check_constant_variable(code_block, coding_language)
        if constant_variable_present:
            available_cases += [change_cases[18]]
        else:
            available_cases += [change_cases[17]]
    code_lines = len(code_block.split('\n'))
    if code_lines > 40:
        available_cases += [change_cases[19]]
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
            print(f"Call failed: {str(e)}, retrying...")
            retries += 1
            if retries >= max_retries:
                print("Reached maximum retries, returning last response")
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
        {"role": "system", "content": "You are an expert Python programmer. You will be given a question (problem specification) and will generate a correct Python program that matches the specification and passes all tests. Your code should not only handle the test cases but also any possible input. The test cases are merely provided to facilitate your understanding of the problem."},
        {"role": "user", "content": item['prompt']}
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

def create_turn_instruction(available_cases: List[tuple], item: Dict[str, Any], turn_number: int, response, selected, contradict, result) -> None:
    """
    Create instruction for a specific turn by selecting from available cases
    
    Args:
        available_cases: List of available case tuples (case_type, templates)
        item: The item dictionary to modify
        turn_number: Current turn number
        response: The previous model response
        selected: List of previously selected case types
        contradict: List of contradictory case type pairs
    """
    codes = extract_code_from_text(response)
    coding_language = codes[0]['language']
    code_block = codes[0]['code']
    
    # Check if we have any available cases
    if not available_cases:
        print(f"Warning: No available cases for turn {turn_number}")
        return
    
    # Filter out already selected case types
    filtered_cases = [case for case in available_cases if case[0] not in selected]
    
    # Further filter out cases that would contradict with any previously selected case type
    non_contradictory_cases = []
    for case in filtered_cases:
        contradicts_existing = False
        for pair in contradict:
            # If this case type is part of a contradictory pair and the other type is already selected
            if case[0] in pair and (pair[0] in selected or pair[1] in selected):
                contradicts_existing = True
                break
        if not contradicts_existing:
            non_contradictory_cases.append(case)
    
    result[f'turn{turn_number}_available'] = non_contradictory_cases
    
    # If we don't have any valid cases left, use the original available cases
    if not non_contradictory_cases:
        print(f"Warning: No non-contradictory cases available for turn {turn_number}, using original cases.")
        case_type, templates = random.choice(available_cases)
    else:
        case_type, templates = random.choice(non_contradictory_cases)
    
    # Dictionary to keep track of any additional parameters needed
    params_dict = {}
    
    # Handle specific cases that need parameters
    if case_type == 'keyword_variable_include':
        var_name = generate_random_variable_name()
        params_dict['name'] = var_name
        
    elif case_type == 'keyword_variable_number':
        var_name = generate_random_variable_name()
        number = generate_random_number(1, 4)
        suffix = get_ordinal_suffix(number)
        params_dict['name'] = var_name
        params_dict['number'] = number
        params_dict['suffix'] = suffix
        
    elif case_type == 'keyword_variable_type':
        number = generate_random_number(1, 4)
        suffix = get_ordinal_suffix(number)
        language = coding_language
        var_type = generate_random_type(language)
        params_dict['number'] = number
        params_dict['suffix'] = suffix
        params_dict['type'] = var_type
        
    elif case_type == 'keyword_for':
        # No additional parameters needed
        pass
        
    elif case_type == 'keyword_for_not':
        # No additional parameters needed
        pass
        
    elif case_type == 'keyword_while':
        # No additional parameters needed
        pass
        
    elif case_type == 'keyword_while_not':
        # No additional parameters needed
        pass
        
    elif case_type == 'keyword_if':
        # No additional parameters needed
        pass
        
    elif case_type == 'keyword_if_not':
        # No additional parameters needed
        pass
        
    elif case_type == 'keyword_function':
        number = generate_random_number(2, 3)
        function_form = "function" if number == 1 else "functions"
        params_dict['number'] = number
        params_dict['function_form'] = function_form
        
    elif case_type == 'keyword_function_not':
        # No additional parameters needed
        pass
        
    elif case_type == 'keyword_function_one':
        function_form = "function"
        params_dict['function_form'] = function_form
        
    elif case_type == 'keyword_class':
        number = generate_random_number(2, 3)
        class_form = "class" if number == 1 else "classes"
        params_dict['number'] = number
        params_dict['class_form'] = class_form
        
    elif case_type == 'keyword_class_not':
        # No additional parameters needed
        pass
        
    elif case_type == 'keyword_class_one':
        class_form = "class"
        params_dict['class_form'] = class_form
        
    elif case_type == 'built_in_function':
        # No additional parameters needed
        pass
        
    elif case_type == 'coding_language':
        language = generate_random_language(coding_language)
        params_dict['language'] = language
        
    elif case_type == 'coding_style':
        # No additional parameters needed - remove comments
        pass
        
    elif case_type == 'coding_style_include':
        # No additional parameters needed - add comments
        pass
        
    elif case_type == 'time_limit':
        time = generate_random_time()
        params_dict['time'] = time
        
    elif case_type == 'storage_limit':
        storage = generate_random_storage()
        params_dict['storage'] = storage
        
    elif case_type == 'output_format':
        format_type = generate_random_format()
        params_dict['format'] = format_type
        
    elif case_type == 'global_variable':
        # No additional parameters needed
        pass
        
    elif case_type == 'global_variable_not':
        # No additional parameters needed
        pass
        
    elif case_type == 'constant_variable':
        # No additional parameters needed
        pass
        
    elif case_type == 'constant_variable_not':
        # No additional parameters needed
        pass
        
    elif case_type == 'code_lines':
        code_lines = len(code_block.split('\n'))
        number = code_lines - random.randint(code_lines/8, code_lines/4)
        params_dict['number'] = number
    
    # Randomly select a template and format it with parameters if needed
    template = random.choice(templates)
    
    try:
        prompt = template.format(**params_dict) if params_dict else template
    except KeyError as e:
        print(f"Error formatting template: {e} - using first template as fallback")
        prompt = templates[0]  # Fallback to first template
    
    # Store the case type and generated prompt in the item
    item[f'turn{turn_number}_prompt'] = prompt
    item[f'turn{turn_number}_kwargs'] = case_type
    result[f'turn{turn_number}_kwargs'] = case_type
    result[f'turn{turn_number}_prompt'] = prompt

def process_multi_turn_conversation(api_key: str, item: Dict[str, Any], 
                                   model: str, max_tokens: int, 
                                   temperature: float, max_turns: int = 5) -> Dict[str, Any]:
    """Process a complete multi-turn conversation for a single item."""
    result_item = item.copy()
    conversation_history = []
    create_problem_prompt(item)
    # Generate the initial response
    initial_prompt = create_initial_prompt(item)
    result_item["prompt_turn0"] = initial_prompt
    conversation_history = copy.deepcopy(initial_prompt)

    # Generate the turns number
    res_turns = random.choice([4, 6, 8])
    #res_turns = 8
    
    initial_response = model_responses(initial_prompt, model, max_tokens, temperature, api_key=api_key)
    if initial_response is None:
        raise Exception("Initial response is None")
    
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
    ('keyword_if_not', 'keyword_while_not'),
    ('function_parameters_min', 'function_parameters_max')
    ]
    selected_case_types = []
    available_cases = check_case(last_response)

    # Define weights for case types (adjust values as needed)
    # You can place this dictionary definition outside the function if preferred
    case_weights = {
        # Change cases (higher weight for more impactful changes?)
        'keyword_for': 18, 'keyword_for_not': 11,
        'keyword_while': 14, 'keyword_while_not': 6,
        'keyword_if': 30, 'keyword_if_not': 16,
        'keyword_function': 70, 'keyword_function_not': 30, 'keyword_function_one': 17,
        'keyword_class': 39, 'keyword_class_not': 11, 'keyword_class_one': 15,
        'built_in_function': 14,
        'coding_style': 19, 'coding_style_include': 21,
        'global_variable': 21, 'global_variable_not': 5,
        'constant_variable': 7, 'constant_variable_not': 5, # Only for C++/Java
        'code_lines': 7,
        'function_parameters_max': 10, 'function_parameters_min': 5,
        # Basic cases (lower weight?)
        'keyword_variable_include': 32, 'keyword_variable_number': 13, 'keyword_variable_type': 18,
        'coding_language': 69, # Lower weight for changing language
        'time_limit': 8, 'storage_limit': 8, 'output_format': 6
        # Default weight for any unlisted case type will be 1 (see below)
    }

    current_available_cases = available_cases # Startancs with all initially available cases

    for i in range(1, res_turns + 1):
        # --- Filtering based on previous selections ---
        current_selected_type_strings = [selected_tuple[0] for selected_tuple in selected_case_types]

        # Filter out already selected case types (based on type string)
        filtered_cases = [case for case in current_available_cases if case[0] not in current_selected_type_strings]

        # Further filter out cases that would contradict with any previously selected case type
        non_contradictory_cases = []
        for case in filtered_cases:
            contradicts_existing = False
            for pair in contradictory_pairs:
                # Check if case[0] is in the pair AND if either element of the pair is in the list of selected type strings
                if case[0] in pair and (pair[0] in current_selected_type_strings or pair[1] in current_selected_type_strings):
                    contradicts_existing = True
                    break
            if not contradicts_existing:
                non_contradictory_cases.append(case)

        # --- Weighted Selection ---
        if not non_contradictory_cases:
            print(f"Warning: No non-contradictory cases available for turn {i}. Stopping turn generation.")
            break # Stop if no valid cases left

        # Prepare for weighted choice
        case_options = non_contradictory_cases
        # Get weights for the available options, defaulting to 1 if not specified in case_weights
        weights = [case_weights.get(case[0], 1.0) for case in case_options]

        # Ensure weights are valid (non-negative, sum > 0)
        weights = [max(0, w) for w in weights] # Ensure non-negative weights
        total_weight = sum(weights)

        if total_weight <= 0:
             print(f"Warning: Sum of weights is not positive for turn {i}. Using uniform distribution.")
             # Fallback to uniform choice if all weights are zero or negative
             if case_options: # Ensure case_options is not empty
                 selected_case_tuple = random.choice(case_options)
             else: # Should not happen due to the check above, but for safety
                 print(f"Error: No case options available for turn {i} even after fallback.")
                 break
        else:
            # Perform weighted selection
            # random.choices returns a list, so get the first element [0]
            selected_case_tuple = random.choices(case_options, weights=weights, k=1)[0]

        # --- Update state ---
        selected_case_types.append(selected_case_tuple)
        # Update the pool for the next iteration based on the remaining non-contradictory cases
        current_available_cases = non_contradictory_cases

    result_item['case_types'] = selected_case_types
    return result_item

def main():
    """Process multi-turn LLM interaction programming problems one by one"""
    parser = argparse.ArgumentParser(description="Process multi-turn LLM interaction for programming problems")
    parser.add_argument("--model_name", type=str, default="openai/gpt-4o-mini-2024-07-18",
                        help="Model name to use for API calls")
    parser.add_argument("--input_file", type=str, default="new_try\output\decoded_data.jsonl",
                        help="Path to input JSONL file")
    parser.add_argument("--output_file", type=str, default="new_try\output\\real_experiment\decoded_data.jsonl",
                        help="Path to output JSONL file")
    parser.add_argument("--max_tokens", type=int, default=8192,
                        help="Maximum tokens for model response")
    parser.add_argument("--temperature", type=float, default=0,
                        help="Temperature for model response (0-1)")
    parser.add_argument("--max_turns", type=int, default=5,
                        help="Maximum conversation turns")
    parser.add_argument("--api_key", type=str, required=True,
                        help="API key for OpenRouter")
    
    args = parser.parse_args()

    print(f"Loading data from {args.input_file}")
    data = load_jsonl(args.input_file)

    print(f"Generating multi-turn responses for {len(data)} problems")
    results = []
    case_type_counts = collections.Counter() # Initialize the counter

    with tqdm(total=len(data), desc="Processing problems", unit="problem") as pbar:
        for item in data:
            try: # Add try-except block for robustness
                result = process_multi_turn_conversation(
                    args.api_key, item, args.model_name, args.max_tokens, args.temperature, args.max_turns)
                results.append(result)
                # Increment counts for selected case types in this result
                if 'case_types' in result:
                    for case_tuple in result['case_types']:
                        case_type_counts[case_tuple[0]] += 1 # case_tuple[0] is the case type string
            except Exception as e:
                print(f"\nError processing problem (ID: {item.get('question_id', 'N/A')}): {e}") # Log errors
            finally:
                pbar.update(1)

    print(f"Saving results to {args.output_file}")
    save_jsonl(results, args.output_file)

    # Print the counts of each case type
    print("\n--- Case Type Counts ---")
    if case_type_counts:
        # Sort by count descending for better readability
        for case_type, count in case_type_counts.most_common():
            print(f"{case_type}: {count}")
    else:
        print("No case types were selected or counted.")

    print("Completed!")

if __name__ == "__main__":
    main()