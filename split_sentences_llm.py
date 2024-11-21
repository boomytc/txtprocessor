import os
import re
import shutil
import pexpect
import time
import argparse
import psutil
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from tqdm import tqdm

# 创建一个锁用于同步打印输出
print_lock = Lock()

# 获取当前进程
process = psutil.Process()

def safe_print(*args, **kwargs):
    """线程安全的打印函数"""
    with print_lock:
        print(*args, **kwargs)

def clean_text(text: str) -> str:
    """清理文本，去除不需要的内容并规范化标点"""
    # 1. 去除序号（数字+点）
    text = re.sub(r'^\d+\.\s*', '', text)
    
    # 2. 去除英文及其括号内容，但保留中文括号内容
    text = re.sub(r'\([A-Za-z\s\-_]+\)', '', text)  # 去除英文括号内容
    text = re.sub(r'[A-Za-z\s\-_]+', '', text)      # 去除其他英文
    
    # 3. 统一标点符号
    punct_map = {
        '：': '，',
        '；': '，',
        '！': '。',
        '？': '。',
        '、': '，',
        '…': '。',
        '──': '，',
        ' ': '',
        '\n': '，',
        '．': '。',
        '.': '。',
        ',': '，'
    }
    
    for old, new in punct_map.items():
        text = text.replace(old, new)
    
    # 4. 只保留中文字符和基本标点
    text = re.sub(r'[^\u4e00-\u9fff，。""]', '', text)
    
    # 5. 处理重复的标点符号
    text = re.sub(r'[，。]+', lambda m: '。' if '。' in m.group() else '，', text)
    
    # 6. 确保句子以句号结尾
    if text and not text.endswith('。'):
        text += '。'
    
    # 7. 去除可能的空括号
    text = re.sub(r'[（\(]\s*[）\)]', '', text)
    
    return text.strip()

def ask_llama_for_fine_split(text: str) -> Tuple[List[str], bool]:
    """使用Llama模型对文本进行智能分句和优化"""
    prompt = f"""请分析以下文本，完成这些任务：
1. 判断是否需要拆分为多个句子
2. 检查句子是否通顺，如果不通顺则改写
3. 只保留中文内容和基本标点（逗号、句号、引号）

文本：{text}

请直接按以下格式回复：
需要处理：是/否
处理结果：
1. [处理后的句子1]
2. [处理后的句子2]
...

如果是单句且通顺的中文，直接在"处理结果"后写出该句子。"""

    try:
        # child = pexpect.spawn('ollama run llama3.2:3b', encoding='utf-8')
        child = pexpect.spawn('ollama run qwen2.5-coder:7b', encoding='utf-8')
        index = child.expect(['>>>', pexpect.EOF, pexpect.TIMEOUT], timeout=10)
        if index != 0:
            return [text], False

        child.sendline(prompt)
        index = child.expect(['>>>', pexpect.EOF, pexpect.TIMEOUT], timeout=30)
        if index == 0:
            response = child.before.strip()
            response = response.replace(prompt, '').strip()
            
            # 解析响应
            needs_split = False
            sentences = []
            current_sentence = []
            
            for line in response.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('需要处理：'):
                    needs_split = '是' in line
                elif line.startswith('处理结果：'):
                    continue
                elif re.match(r'^\d+\.', line):
                    if current_sentence:
                        sentences.append(''.join(current_sentence))
                        current_sentence = []
                    sentence = re.sub(r'^\d+\.\s*', '', line).strip()
                    if sentence:
                        current_sentence.append(sentence)
                else:
                    current_sentence.append(line)
            
            if current_sentence:
                sentences.append(''.join(current_sentence))
            
            if not sentences:
                return [clean_text(text)], False
            
            # 清理每个句子的标点符号
            cleaned_sentences = []
            for sentence in sentences:
                # 提取中文内容并规范化标点
                cleaned = clean_text(sentence)
                if cleaned:
                    cleaned_sentences.append(cleaned)
            
            return cleaned_sentences if cleaned_sentences else [clean_text(text)], needs_split

    except Exception as e:
        print(f"✗ 处理出错：{str(e)}")
        return [clean_text(text)], False
    finally:
        try:
            child.sendline("/bye")
            child.close()
        except:
            pass

def process_file(args) -> Tuple[bool, str, int, bool]:
    """处理单个文件的函数"""
    input_file_path, output_subdir, current_output_index = args
    
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        
        # 跳过索引文件（0.txt）的处理
        if os.path.basename(input_file_path) == '0.txt':
            return True, input_file_path, 1, False
        
        filename = os.path.basename(input_file_path)
        
        # 使用LLM判断是否需要细分并处理
        sentences, needs_split = ask_llama_for_fine_split(text)
        
        file_count = 0
        if needs_split:
            with print_lock:
                print(f"\n处理文件：{filename}")
                print(f"✓ 需要处理，将输出 {len(sentences)} 个优化后的句子")
            # 保存处理后的句子
            for sentence in sentences:
                output_path = os.path.join(output_subdir, f'{current_output_index + file_count}.txt')
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(sentence.strip())
                file_count += 1
        else:
            # 直接复制原文（如果是纯中文且通顺的单句）
            output_path = os.path.join(output_subdir, f'{current_output_index}.txt')
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            file_count = 1
        
        return True, filename, file_count, needs_split
    except Exception as e:
        safe_print(f"✗ 处理文件 {os.path.basename(input_file_path)} 时出错: {str(e)}")
        return False, os.path.basename(input_file_path), 0, False

def write_done_file(done_file: str, stats: dict):
    """写入完成标记文件"""
    with open(done_file, 'w', encoding='utf-8') as f:
        f.write(f"处理完成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"处理耗时：{stats['time_elapsed']:.2f}秒\n")
        f.write(f"成功处理文件数：{stats['success_count']}\n")
        f.write(f"细分文件数：{stats['split_count']}\n")
        f.write(f"生成句子数：{stats['sentence_count']}\n")
        f.write(f"使用线程数：{stats['workers']}\n")
        if 'peak_memory' in stats:
            current_process = psutil.Process()
            f.write(f"内存峰值：{current_process.memory_info().rss / (1024 * 1024 * 1024):.2f}GB\n")

def split_and_save_with_llm(input_directory: str, output_directory: str, max_workers: int = 4):
    """使用多线程的LLM细分处理"""
    # 规范化路径
    input_directory = os.path.abspath(input_directory)
    output_directory = os.path.abspath(output_directory)
    
    if input_directory == output_directory:
        raise ValueError("输入和输出目录不能相同")
    
    # 检查已处理的文件夹（使用隐藏的.done文件）
    folders = [f for f in os.listdir(input_directory) if os.path.isdir(os.path.join(input_directory, f))]
    processed_folders = set()
    for folder in folders:
        done_file = os.path.join(output_directory, f".{folder}.done")
        if os.path.exists(done_file):
            processed_folders.add(folder)
    
    # 过滤出未处理的文件夹
    folders_to_process = [f for f in folders if f not in processed_folders]
    
    print(f"\n共发现 {len(folders)} 个文件夹")
    print(f"已处理: {len(processed_folders)} 个")
    print(f"待处理: {len(folders_to_process)} 个")
    print("=" * 50)
    
    if not folders_to_process:
        print("所有文件夹都已处理完成")
        return
    
    os.makedirs(output_directory, exist_ok=True)
    
    # 动态调整线程数
    available_memory = psutil.virtual_memory().available / (1024 * 1024 * 1024)  # GB
    suggested_workers = min(max_workers, int(available_memory / 2))  # 每个线程预估使用2GB内存
    if suggested_workers < max_workers:
        print(f"警告：可用内存不足，已将线程数从 {max_workers} 调整为 {suggested_workers}")
        max_workers = suggested_workers
    
    # 统计信息
    start_time = time.time()
    success_count = 0
    failed_count = 0
    failed_files = []
    total_sentences = 0
    
    for folder_index, folder in enumerate(folders_to_process, 1):
        folder_start_time = time.time()
        print(f"\n正在处理第 {folder_index}/{len(folders_to_process)} 个文件夹: {folder}")
        
        input_folder_path = os.path.join(input_directory, folder)
        output_subdir = os.path.join(output_directory, folder)
        done_file = os.path.join(output_directory, f".{folder}.done")
        
        try:
            os.makedirs(output_subdir, exist_ok=True)
            
            # 获取所有txt文件（排除0.txt索引文件）
            files = [f for f in os.listdir(input_folder_path) 
                    if f.endswith('.txt') and f != '0.txt']
            files.sort(key=lambda x: int(x.split('.')[0]))
            
            # 复制索引文件
            index_src = os.path.join(input_folder_path, '0.txt')
            index_dst = os.path.join(output_subdir, '0.txt')
            if os.path.exists(index_src):
                shutil.copy2(index_src, index_dst)
            
            # 准备任务列表
            current_output_index = 1
            tasks = []
            for file in files:
                input_file_path = os.path.join(input_folder_path, file)
                tasks.append((input_file_path, output_subdir, current_output_index))
                current_output_index += 1
            
            # 使用线程池处理文件
            folder_success = 0
            folder_sentences = 0
            split_count = 0
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(process_file, task) for task in tasks]
                
                with tqdm(total=len(tasks), desc=f"处理文件夹 {folder}", 
                         bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]') as pbar:
                    for future in as_completed(futures):
                        success, filename, file_count, was_split = future.result()
                        if success:
                            folder_success += 1
                            folder_sentences += file_count
                            if was_split:
                                split_count += 1
                        else:
                            failed_files.append(filename)
                        pbar.update(1)
            
            success_count += folder_success
            total_sentences += folder_sentences
            failed_count += len(files) - folder_success
            
            # 只在有细分的情况下显示详细统计
            if split_count > 0:
                print(f"\n✓ 文件夹处理完成")
                print(f"✓ 成功处理：{folder_success}/{len(files)} 个文件")
                print(f"✓ 需要细分：{split_count} 个文件")
                print(f"✓ 生成句子：{folder_sentences} 个")
            
            # 创建隐藏的完成标记文件
            if folder_success > 0:
                folder_time = time.time() - folder_start_time
                stats = {
                    'time_elapsed': folder_time,
                    'success_count': folder_success,
                    'split_count': split_count,
                    'sentence_count': folder_sentences,
                    'workers': max_workers,
                }
                write_done_file(done_file, stats)
                
                # 在Unix系统上置隐藏属性（Windows系统会自动隐藏以点开头的文件）
                if os.name == 'posix':  # Linux/Mac
                    try:
                        import subprocess
                        subprocess.run(['chflags', 'hidden', done_file], check=False)
                    except:
                        pass  # 如果设置隐藏属性失败，不影响主要功能
            
        except Exception as e:
            print(f"✗ 处理文件夹 '{folder}' 时出错: {str(e)}")
            if os.path.exists(output_subdir):
                shutil.rmtree(output_subdir)
            continue

    # 输出最终统计
    total_time = time.time() - start_time
    print("\n" + "=" * 50)
    print("处理完成！")
    print(f"总耗时：{total_time:.2f}秒")
    print(f"本次处理文件夹数：{len(folders_to_process)}")
    print(f"总文件数：{success_count + failed_count}")
    print(f"成功：{success_count}")
    print(f"失败：{failed_count}")
    print(f"总句子数：{total_sentences}")
    
    if failed_files:
        print("\n处理失败的文件：")
        for f in failed_files:
            print(f"- {f}")
    
    print(f"\n分句结果已保存到目录：{os.path.abspath(output_directory)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='基于LLM的文本细分处理工具')
    parser.add_argument('--input', default="output/split_output", help='输入目录路径')
    parser.add_argument('--output', default="output/split_llm_output", help='输出目录路径')
    parser.add_argument('--workers', type=int, default=4, help='并行线程数')
    parser.add_argument('--retry', type=int, default=3, help='失败重试次数')
    args = parser.parse_args()
    
    try:
        split_and_save_with_llm(args.input, args.output, args.workers)
    except KeyboardInterrupt:
        print("\n用户中断处理")
    except Exception as e:
        print(f"\n处理过程中出现错误：{str(e)}") 