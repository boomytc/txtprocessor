# 文本处理工具集

这是一个用于处理Word文档和文本的工具集，包含多个脚本用于不同阶段的文本处理。

## 脚本说明

### 1. extract_text.py
从Word文档(.docx)中提取文本内容。

**功能：**
- 提取文档中的段落文本
- 保留表格内容的格式
- 支持批量处理多个文档

**使用方法：**
```bash
处理单个文件
python extract_text.py document.docx
处理单个文件并指定输出目录
python extract_text.py document.docx -o /path/to/output
处理整个目录下的所有docx文件
python extract_text.py /path/to/docx/folder
处理整个目录并指定输出目录
python extract_text.py /path/to/docx/folder -o /path/to/output
```

### 2. split_sentences.py
对提取的文本进行智能分句处理。

**功能：**
- 支持多种文本类型的分句（普通文本、表格、指令、词典等）
- 自动识别文本类型并使用相应的分句策略
- 保持专业术语和关键信息的完整性

**使用方法：**
```bash
python split_sentences.py
```
默认从 `output/docx_output` 读取文件，输出到 `output/split_output`。

### 3. split_sentences_llm.py
使用大语言模型进行高级文本处理和分句。

**功能：**
- 使用LLM模型优化文本内容
- 智能去除冗余信息
- 保持文本的专业性和完整性
- 多线程并行处理
- 支持断点续传

**使用方法：**
```bash
python split_sentences_llm.py
```
默认从 `output/split_output` 读取文件，输出到 `output/split_llm_output`。

### 4. test_llama.py / test.py
用于测试LLM模型的功能和效果。

**功能：**
- 测试模型的初始化
- 验证文本处理效果
- 调试提示词

**使用方法：**
```bash
python test_llama.py
# 或
python test.py
```

## 处理流程
1. 使用 `extract_text.py` 从Word文档中提取文本
2. 使用 `split_sentences.py` 进行初步分句
3. 使用 `split_sentences_llm.py` 进行LLM优化处理

## 目录结构
```
output/
├── docx_output/        # extract_text.py 的输出目录
├── split_output/       # split_sentences.py 的输出目录
└── split_llm_output/   # split_sentences_llm.py 的输出目录
```

## 注意事项
1. 确保已安装所需依赖：
```bash
pip install python-docx requests tqdm
```
2. 使用LLM相关脚本前，需要确保本地Ollama服务已启动并加载了相应模型

3. 处理大量文件时，建议先使用小批量测试

4. 所有脚本都会创建必要的输出目录

5. 每个处理阶段都会生成处理报告，方便追踪和调试
```


