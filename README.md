<!-- markdownlint-disable first-line-h1 -->
<!-- markdownlint-disable html -->
<!-- markdownlint-disable no-duplicate-header -->

<div align="center" style="line-height: 1;">
  <h1><img src="icon2.png" width="40" alt=""> CoCoPIF</h1>
</div>
<hr>
<div align="center" style="line-height: 1;">
  <a href="https://huggingface.co/datasets/Han03430/CoCoPIF"><img alt="Dataset"
    src="https://img.shields.io/badge/%F0%9F%A4%97%20Dataset-CoCoPIF-ffc107?color=ffc107&logoColor=white"/></a>
</div>

## Table of Contents

1. [Introduction](#1-introduction)
2. [Evaluation Source Code](#2-evaluation-source-code)
3. [Dataset Access](#3-dataset-access)
4. [Running the Evaluation Scripts](#4-running-the-evaluation-scripts)

## 1. Introduction

CoCoPIF is a dataset and evaluation framework designed for evaluating code generation and execution capabilities across various programming languages. The evaluation source code provided enables researchers to generate baseline solutions, obtain model responses, and evaluate execution results. The dataset is publicly available on Hugging Face, and the evaluation scripts are designed to work seamlessly with it.

## 2. Evaluation Source Code

The CoCoPIF evaluation framework consists of several Python scripts, each serving a specific purpose in the evaluation pipeline:

- **`case_initial_select.py`**: Generates baseline solutions for the CoCoPIF evaluation.
- **`code_generation_turn_multi.py`**: Obtains responses from different models for the evaluation process.
- **`evaluation_all_turn.py`**: Evaluates the final execution results of the submissions.
- **`evaluation.py`**, **`evaluation_c.py`**, **`evaluation_java.py`**: Dependency files required by `evaluation_all_turn.py` for evaluating results across different programming languages.

## 3. Dataset Access

The CoCoPIF dataset is hosted on Hugging Face and can be accessed at the following link:

<div align="center">
  <a href="https://huggingface.co/datasets/Han03430/CoCoPIF"><b>CoCoPIF Dataset on Hugging Face</b> 🤗</a>
</div>

The dataset contains input files in JSONL format (e.g., `input.jsonl`) that are used by the evaluation scripts to generate and evaluate solutions.

## 4. Running the Evaluation Scripts

Below are the commands to run the evaluation scripts, which interact with the CoCoPIF dataset.

### 4.1 Running `case_initial_select.py`

To generate baseline solutions, use the following command:

```bash
python case_initial_select.py --model_name "openai/gpt-4o-mini" --input_file "path/to/input.jsonl" --output_file "path/to/output.jsonl" --max_tokens 4096 --temperature 0.2 --max_turns 3 --api_key "your-api-key"
```

This command specifies the model, input and output files, token limit, temperature, maximum turns, and API key required for the script. The `input.jsonl` file can be obtained from the CoCoPIF dataset.

### 4.2 Running `code_generation_turn_multi.py`

To obtain a model's solution, use the following command:

```bash
python code_generation_turn_multi.py --api_key "your-api-key" --model_name "your-model" --input_file "path/to/input.jsonl" --output_file "path/to/output.jsonl"
```

This command specifies the API key, model name, and input/output files for generating model responses.

### 4.3 Running `evaluation_all_turn.py`

To evaluate the results, use the following command:

```bash
python evaluation_all_turn.py --input_file path/to/input.jsonl --output_file path/to/output.jsonl
```

This command evaluates the final execution results using the specified input and output files.

> [!NOTE]
> Ensure that the `input.jsonl` and `output.jsonl` file paths point to valid files from the CoCoPIF dataset or generated outputs. Replace `your-api-key` and `your-model` with appropriate values for your setup.
