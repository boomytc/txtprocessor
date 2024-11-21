import os
import re
import shutil  # 用于删除目录

def is_command_content(text):
    """判断是否为指令/快捷键类型的内容"""
    # 检查是否包含大量快捷键特征
    keyboard_patterns = [
        r'CTRL\+',
        r'ALT\+',
        r'SHIFT\+',
        r'\([^)]*键\)',
        r'[A-Z]\+[A-Z]'
    ]
    
    pattern_matches = sum(1 for pattern in keyboard_patterns if re.search(pattern, text))
    return pattern_matches >= 2

def split_command_content(text):
    """处理指令/快捷键内容的分句逻辑"""
    lines = text.split('\n')
    entries = []
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 检查是否是章节标题（以"指令"结尾的行）
        if line.endswith('指令：'):
            current_section = line.rstrip('：')
            continue
            
        # 处理快捷键行
        if ' - ' in line:  # 已经是格式化的内容
            if current_section:
                entries.append(f"{current_section} - {line}")
            else:
                entries.append(line)
        else:
            # 处理未格式化的内容
            match = re.match(r'^(.+?)\s+([A-Z0-9+\s\(\)]+(?:键)?|[^a-z]+)$', line)
            if match:
                description, shortcut = match.groups()
                if current_section:
                    entries.append(f"{current_section} - {description.strip()} - {shortcut.strip()}")
                else:
                    entries.append(f"{description.strip()} - {shortcut.strip()}")
    
    return entries

def is_table_content(text):
    """判断是否为表格内容"""
    return text.strip().startswith('=== 表格开始 ===')

def split_table_content(text):
    """处理表格内容的分句逻辑"""
    lines = text.split('\n')
    entries = []
    current_entry = []
    
    for line in lines:
        line = line.strip()
        if not line or line == '=== 表格开始 ===' or line == '=== 表格结束 ===':
            continue
            
        # 分割每行的多个条目
        items = [item.strip() for item in line.split('|')]
        for item in items:
            # 使用正则提取编号和内容
            match = re.match(r'(\d+)\.\s*(.+)', item.strip())
            if match:
                number, content = match.groups()
                entries.append(f"{number}. {content.strip()}")
    
    return entries

def split_normal_content(text):
    """处理普通文本的分句逻辑"""
    # 使用更严格的分句标点符号
    delimiters = ['。', '！', '？', '；', '\n\n']
    pattern = '|'.join(map(re.escape, delimiters))
    sentences = re.split(f'({pattern})', text)
    
    result = []
    for i in range(0, len(sentences)-1, 2):
        if sentences[i].strip():
            result.append(sentences[i] + (sentences[i+1] if i+1 < len(sentences) else ''))
    
    return result

def is_dictionary_content(text):
    """判断是否为词典类内容"""
    # 检查是否包含音标特征
    phonetic_patterns = [
        r'\[.*?\]',  # 匹配音标
        r'英音.*?美音',  # 匹配音标说明
        r'名词 n\.',  # 匹配词性标注
    ]
    
    pattern_matches = sum(1 for pattern in phonetic_patterns if re.search(pattern, text))
    return pattern_matches >= 2

def split_dictionary_content(text):
    """处理词典类内容的分句逻辑"""
    lines = text.split('\n')
    entries = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 移除音标和发音说明
        line = re.sub(r'英音：\[.*?\]美音：\[.*?\]', '', line)
        line = re.sub(r'英音：.*?美音：.*?(?=\s|$)', '', line)
        
        # 提取词条信息
        # 处理带词性标注的情况
        if '名词 n.' in line or '形容词 a.' in line or '动词 v.' in line:
            parts = re.split(r'(?:名词 n\.|形容词 a\.|动词 v\.)\s*', line, 1)
            if len(parts) == 2:
                term, definition = parts
                entries.append(f"{term.strip()} - {definition.strip()}")
        # 处理固定词组
        elif '固定词组 ph.' in line:
            parts = line.split('固定词组 ph.', 1)
            if len(parts) == 2:
                term, definition = parts
                entries.append(f"{term.strip()} - {definition.strip()}")
        # 处理普通定义
        else:
            parts = line.split(' ', 1)
            if len(parts) == 2:
                term, definition = parts
                entries.append(f"{term.strip()} - {definition.strip()}")
    
    return entries

def is_operation_guide(text):
    """判断是否为操作指南类内容"""
    # 检查是否包含大量快捷键特征
    patterns = [
        r'[A-Z][a-z]+ Arrow',  # 方向键
        r'Ctrl \-',  # Ctrl组合键
        r'Alt \-',   # Alt组合键
        r'Shift \-', # Shift组合键
        r'Key Pad',  # 小键盘
        r'F\d+',     # 功能键
    ]
    
    pattern_matches = sum(1 for pattern in patterns if re.search(pattern, text))
    return pattern_matches >= 2

def split_operation_guide(text):
    """处理操作指南类内容的分句逻辑"""
    lines = text.split('\n')
    entries = []
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 跳过日期时间等无关信息
        if re.match(r'\d{4}-\d{1,2}-\d{1,2}', line):
            continue
            
        # 检查是否是章节标题
        if line.endswith('：') or line.endswith(':') or (len(line) < 30 and not re.search(r'[A-Z]', line)):
            current_section = line.rstrip('：:')
            continue
            
        # 处理快捷键行
        if re.search(r'[A-Z]', line):  # 包含大写字母（可能是快捷键）
            # 移除多余的空格
            line = re.sub(r'\s+', ' ', line).strip()
            
            # 处理带括号的补充说明
            line = re.sub(r'\(([^)]+)\)', r'（\1）', line)  # 统一括号格式
            
            if current_section:
                entries.append(f"{current_section} - {line}")
            else:
                entries.append(line)
    
    return entries

def split_sentences(text):
    """主分句函数"""
    if is_table_content(text):
        return split_table_content(text)
    elif is_operation_guide(text):
        return split_operation_guide(text)
    elif is_command_content(text):
        return split_command_content(text)
    elif is_dictionary_content(text):
        return split_dictionary_content(text)
    else:
        return split_normal_content(text)

def split_and_save(input_directory, output_directory):
    # 获取所有需要处理的txt文件
    txt_files = [f for f in os.listdir(input_directory) if f.endswith('.txt')]
    total_files = len(txt_files)
    
    if total_files == 0:
        print("未找到任何txt文件需要处理")
        return
    
    print(f"\n共发现 {total_files} 个txt文件待处理")
    print("=" * 50)
    
    # 创建输出目录
    os.makedirs(output_directory, exist_ok=True)
    
    success_count = 0
    failed_count = 0
    failed_files = []
    
    # 处理每个文件
    for index, filename in enumerate(txt_files, 1):
        print(f"\n正在处理第 {index}/{total_files} 个文件: {filename}")
        
        input_path = os.path.join(input_directory, filename)
        base_name = os.path.splitext(filename)[0]
        output_subdir = os.path.join(output_directory, base_name)
        
        try:
            # 创建输出子目录
            os.makedirs(output_subdir, exist_ok=True)
            
            # 创建索引文件
            index_file_path = os.path.join(output_subdir, '0.txt')
            with open(index_file_path, 'w', encoding='utf-8') as f:
                f.write(f'本目录下的分句结果来自文件：{filename}')
            
            # 读取输入文件
            with open(input_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # 分句
            sentences = split_sentences(text)
            
            # 保存句子
            for i, sentence in enumerate(sentences, 1):
                output_path = os.path.join(output_subdir, f'{i}.txt')
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(sentence.strip())
            
            # 检查是否只有索引文件
            files_in_dir = os.listdir(output_subdir)
            if len(files_in_dir) <= 1:  # 只有0.txt或空目录
                shutil.rmtree(output_subdir)  # 删除整个目录
                print(f"✗ 文件 '{filename}' 分句失败：未能提取到有效句子")
                failed_count += 1
                failed_files.append(filename)
            else:
                print(f"✓ 已完成分句，共分出 {len(sentences)} 个句子")
                print(f"✓ 输出目录：{output_subdir}")
                success_count += 1
            
        except Exception as e:
            print(f"✗ 处理文件 '{filename}' 时出错: {str(e)}")
            failed_count += 1
            failed_files.append(filename)
            # 如果目录已创建，则删除
            if os.path.exists(output_subdir):
                shutil.rmtree(output_subdir)
            continue

    # 输出最终处理结果统计
    print("\n" + "=" * 50)
    print(f"处理完成！总计处理 {total_files} 个文件")
    print(f"成功：{success_count} 个")
    print(f"失败：{failed_count} 个")
    
    if failed_files:
        print("\n以下文件处理失败：")
        for f in failed_files:
            print(f"- {f}")
    
    print(f"\n分句结果已保存到目录：{os.path.abspath(output_directory)}")

if __name__ == "__main__":
    # 设置输入输出路径
    input_directory = "output/docx_output"
    output_directory = "output/split_output"
    
    print("\n=== 文本分句处理工具 ===")
    print(f"输入目录：{os.path.abspath(input_directory)}")
    print(f"输出目录：{os.path.abspath(output_directory)}")
    
    # 检查输入目录是否存在
    if not os.path.exists(input_directory):
        print(f"\n错误：输入目录 '{input_directory}' 不存在")
        exit(1)
    
    try:
        split_and_save(input_directory, output_directory)
        print("\n" + "=" * 50)
        print(f"处理完成！分句结果已保存到目录：{os.path.abspath(output_directory)}")
    except Exception as e:
        print(f"\n处理过程中出现错误：{str(e)}")
