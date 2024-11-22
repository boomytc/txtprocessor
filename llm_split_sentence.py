import os
import re
import time
import jieba
import requests
import argparse
from typing import List, Tuple
from tqdm import tqdm
from datetime import datetime

class LLMProcessor:
    def __init__(self, model="qwen2.5-coder:7b"):
        self.base_url = "http://localhost:11434/api"
        self.headers = {"Content-Type": "application/json"}
        self.model = model
        
        # 初始化prompt
        self.init_prompt = """你是一个航空领域的文本处理专家。
        请回复：模型初始化完成。"""
        
        # 第一次迭代的prompt - 处理原始文本
        self.first_prompt = """你是一个航空领域的专家，精通直升机、发动机、航空电子等专业知识。你的任务是优化文本格式并补充必要的专业细节：

        处理规则：
        1. 删除所有技术性标记，如：(P>0.05)、(n=100)等
        2. 删除所有序号标记，如：(1)、（二）等
        3. 删除所有英文内容
        4. 删除中括号[]和其内容
        5. 删除括号()中的数字
        6. 删除markdown格式标记
        7. 删除表格相关标记

        严格要求：
        1. 不要对文本进行总结或压缩
        2. 保持原文的所有重要细节
        3. 在不改变原意的前提下，补充相关的专业描述
        4. 使用更专业的航空术语替换普通用语
        5. 添加必要的技术参数和操作要求
        6. 扩展说明关键的安全注意事项

        示例：
        输入：'从[燃油喷嘴](20)上拆下[余油管]。'
        输出：'从位于发动机6点钟方向的高压燃油喷嘴上小心拆下余油回流管，注意检查密封圈完整性。'

        注意：
        1. 直接输出处理后的文本
        2. 不要添加任何解释或说明
        3. 保持并扩充专业内容
        """

        # 第二次迭代的prompt - 检查单个句子
        self.second_prompt = """你是一个航空维修专家。请判断并优化下面这句话：

        {text}

        处理要求：
        1. 如果是完整的专业句子，补充必要的技术细节
        2. 如果不是完整的句子，扩展为完整的专业描述
        3. 添加必要的操作规范和安全提示
        4. 使用准确的航空专业术语

        注意：
        1. 只返回处理后的句子
        2. 不要简化或压缩内容
        3. 保持专业性和完整性
        """

        # 第三次迭代的prompt - 判断是否需要分句
        self.third_prompt = """你是一个航空文档专家。请判断下面这段文本的结构：

        {text}

        判断标准：
        1. 如果是单个完整的维修步骤，回复：SINGLE
        2. 如果包含多个操作步骤，回复：MULTIPLE
        3. 如果是无效或非维修内容，回复：INVALID

        只返回：SINGLE 或 MULTIPLE 或 INVALID"""
        
        # 添加第四次迭代的prompt - 最终清理
        self.fourth_prompt = """你是一个文本清理专家。请对下面这句话进行最后的格式清理：

        {text}

        处理规则：
        1. 删除句首的所有数字和符号（如1.、(1)、-、*等）
        2. 删除句首的所有空白字符
        3. 确保句子以中文字符开头
        4. 保持句子的完整性和专业性
        5. 删除句子中的多余标点符号
        6. 确保使用规范的中文标点

        只返回处理后的句子，不要添加任何说明。"""
        
        self._init_model()
    
    def _init_model(self):
        try:
            # 使用first_prompt进行初始化测试
            response = self._generate_completion(self.first_prompt)
            print("模型初始化完成")
        except Exception as e:
            print(f"❌ 初始化错误: {str(e)}")
    
    def _generate_completion(self, prompt):
        url = f"{self.base_url}/generate"
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        response = requests.post(url, headers=self.headers, json=data)
        return response.json().get('response', '')

    def initialize(self) -> bool:
        """确保模型完全初始化"""
        try:
            print("正在初始化模型...", end=' ', flush=True)
            response = self._generate_completion(self.init_prompt)
            if response and "模型初始化完成" in response:
                print("✓")
                return True
            else:
                print("✗")
                return False
        except Exception as e:
            print(f"✗\n初始化失败: {str(e)}")
            return False

def clean_text(text: str) -> str:
    """清理文本，去除markdown标记和特殊符号"""
    # 去除markdown标题标记
    text = re.sub(r'^#+\s*', '', text)
    
    # 去除markdown列表标记
    text = re.sub(r'^\s*[-*]\s*', '', text)  # 无序列表标记 - 和 *
    text = re.sub(r'^\s*\d+\.\s*', '', text)  # 有序列表标记 1. 2. 等
    
    # 去除markdown加粗和斜体标记
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    
    # 去除多余的空白字符
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'([。！？；\?!;])\s*', r'\1\n', text)
    
    return text.strip()

def split_sentences_with_jieba(text: str) -> List[str]:
    """使用jieba进行分句"""
    # 确保标点符号后换行
    text = clean_text(text)
    
    # 使用jieba分词
    sentences = []
    for line in text.split('\n'):
        if not line.strip():
            continue
            
        # 使用jieba进行分词和断句
        words = list(jieba.cut(line))
        current_sentence = []
        
        for word in words:
            current_sentence.append(word)
            if word in '。！？；!?;':
                sentence = ''.join(current_sentence).strip()
                if sentence:
                    sentences.append(sentence)
                current_sentence = []
        
        # 处理最后一个句子
        if current_sentence:
            sentence = ''.join(current_sentence).strip()
            if sentence:
                sentences.append(sentence)
    
    return sentences

def create_done_marker(input_path: str, output_dir: str):
    """创建处理完成标记文件"""
    # 在输出目录创建.done文件
    done_marker = os.path.join(output_dir, '.done')
    with open(done_marker, 'w', encoding='utf-8') as f:
        f.write(f"Processed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def is_file_processed(input_path: str, output_dir: str) -> bool:
    """检查文件是否已经处理过"""
    # 检查输出目录中的.done文件
    done_marker = os.path.join(output_dir, '.done')
    
    if os.path.exists(done_marker):
        # 如果存在.done文件，检查输出目录是否有实际的处理结果
        files = [f for f in os.listdir(output_dir) if f.endswith('.txt')]
        if files:  # 如果有处理结果文件
            print(f"\n文件已处理过，跳过：{os.path.basename(input_path)}")
            print(f"  输出目录：{output_dir}")
            print(f"  包含文件：{len(files)} 个")
            return True
        else:
            # 如果没有处理结果文件，删除.done文件
            os.remove(done_marker)
    
    return False

def process_text_iteratively(text: str, llm_processor: LLMProcessor, output_dir: str, progress_bar: tqdm) -> bool:
    """四次迭代处理文本"""
    try:
        # 第一次迭代：先分句，再处理每个句子
        progress_bar.set_description("第一阶段：分句和格式优化")
        
        # 先使用jieba进行初步分句
        initial_sentences = split_sentences_with_jieba(text)
        
        # 对每个句子使用first_prompt进行处理
        first_iter_files = []
        for i, sentence in enumerate(initial_sentences, 1):
            # 使用first_prompt处理每个句子
            processed = llm_processor._generate_completion(sentence)
            if not processed:
                processed = sentence
                
            # 保存处理结果
            file_path = os.path.join(output_dir, f"{i}.txt")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(processed)
            first_iter_files.append(file_path)
            
        progress_bar.update(33)
        
        # 第二次迭代：检查每个句子
        progress_bar.set_description("第二阶段：优化句子完整性")
        for i, file_path in enumerate(first_iter_files):
            with open(file_path, 'r', encoding='utf-8') as f:
                sentence = f.read().strip()
            
            # 处理句子
            prompt = llm_processor.second_prompt.format(text=sentence)
            second_processed = llm_processor._generate_completion(prompt)
            
            if second_processed and second_processed != sentence:
                # 如果内容有修改，创建新文件
                new_file_path = os.path.join(output_dir, f"{i+1}-1.txt")
                with open(new_file_path, 'w', encoding='utf-8') as f:
                    f.write(second_processed)
                # 删除原文件
                os.remove(file_path)
            
            progress_bar.update(33 / len(first_iter_files))
        
        # 第三次迭代：判断分句
        progress_bar.set_description("第三阶段：最终分句检查")
        second_iter_files = [f for f in os.listdir(output_dir) if f.endswith('.txt') and f != '0.txt']
        
        for file_name in second_iter_files:
            file_path = os.path.join(output_dir, file_name)
            with open(file_path, 'r', encoding='utf-8') as f:
                sentence = f.read().strip()
            
            # 判断是否需要分句
            prompt = llm_processor.third_prompt.format(text=sentence)
            sentence_type = llm_processor._generate_completion(prompt)
            
            if sentence_type == "INVALID":
                os.remove(file_path)
                continue
                
            base_name = os.path.splitext(file_name)[0]
            
            if sentence_type == "MULTIPLE":
                # 需要分句，创建多个新文件
                sub_sentences = split_sentences_with_jieba(sentence)
                for j, sub_sentence in enumerate(sub_sentences, 1):
                    new_file_path = os.path.join(output_dir, f"{base_name}-{j}.txt")
                    with open(new_file_path, 'w', encoding='utf-8') as f:
                        f.write(sub_sentence)
                # 删除原文件
                os.remove(file_path)
            elif sentence_type == "SINGLE":
                # 检查是否需要优化
                prompt = llm_processor.second_prompt.format(text=sentence)
                final_processed = llm_processor._generate_completion(prompt)
                
                if final_processed and final_processed != sentence:
                    new_file_path = os.path.join(output_dir, f"{base_name}-1.txt")
                    with open(new_file_path, 'w', encoding='utf-8') as f:
                        f.write(final_processed)
                    os.remove(file_path)
        
        # 第四次迭代：最终清理
        progress_bar.set_description("第四阶段：最终格式清理")
        third_iter_files = [f for f in os.listdir(output_dir) if f.endswith('.txt') and f != '0.txt']
        
        for file_name in third_iter_files:
            file_path = os.path.join(output_dir, file_name)
            with open(file_path, 'r', encoding='utf-8') as f:
                sentence = f.read().strip()
            
            # 最终清理
            prompt = llm_processor.fourth_prompt.format(text=sentence)
            final_processed = llm_processor._generate_completion(prompt)
            
            if final_processed and final_processed != sentence:
                # 如果内容有修改，创建新文件
                base_name = os.path.splitext(file_name)[0]
                new_file_path = os.path.join(output_dir, f"{base_name}-1.txt")
                with open(new_file_path, 'w', encoding='utf-8') as f:
                    f.write(final_processed)
                # 删除原文件
                os.remove(file_path)
            
            progress_bar.update((100 - progress_bar.n) / len(third_iter_files))
        
        return True
        
    except Exception as e:
        print(f"\n处理文本时出错: {str(e)}")
        return False

def process_file(input_path: str, output_dir: str, llm_processor: LLMProcessor) -> Tuple[bool, float]:
    """处理单个文件
    Returns:
        Tuple[bool, float]: (是否成功, 处理耗时(秒))
    """
    start_time = time.time()
    try:
        # 检查是否已处理
        if is_file_processed(input_path, output_dir):
            return True, 0
        
        # 读取文件
        with open(input_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        
        if not text:
            return False, 0
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\n处理文件：{os.path.basename(input_path)}")
        print(f"输出目录：{output_dir}")
        
        # 更新进度条总量为125（为第四次迭代预留25%）
        with tqdm(total=125, desc="初始化处理", unit="%") as pbar:
            success = process_text_iteratively(text, llm_processor, output_dir, pbar)
        
        if success:
            # 创建处理完成标记
            create_done_marker(input_path, output_dir)
            elapsed_time = time.time() - start_time
            print(f"✓ 成功处理：{os.path.basename(input_path)}")
            print(f"处理耗时：{elapsed_time:.2f}秒")
            
            # 打印最终文件列表
            final_files = [f for f in os.listdir(output_dir) if f.endswith('.txt') and f != '0.txt']
            print(f"生成文件：{len(final_files)} 个")
            for f in sorted(final_files):
                file_path = os.path.join(output_dir, f)
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read().strip()
                print(f"  - {f}: {content[:50]}...")
        
        return success, time.time() - start_time
        
    except Exception as e:
        print(f"\n✗ 处理文件时出错: {str(e)}")
        return False, time.time() - start_time

def process_directory(input_dir: str, output_dir: str):
    """处理整个目录"""
    total_start_time = time.time()
    print(f"\n=== 文本处理工具 ===")
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 初始化LLM处理器
    llm_processor = LLMProcessor()
    if not llm_processor.initialize():
        print("模型初始化失败，程序退出")
        return
        
    # 初始化jieba
    print("正在初始化分词模型...", end=' ', flush=True)
    import jieba
    _ = jieba.lcut("初始化测试")  # 触发jieba初始化
    print("✓")
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有txt文件
    txt_files = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.txt') and not file.startswith('.'):
                txt_files.append(os.path.join(root, file))
    
    if not txt_files:
        print("未找到任何txt文件")
        return
    
    print(f"\n找到 {len(txt_files)} 个txt文件")
    print(f"输入目录：{os.path.abspath(input_dir)}")
    print(f"输出目录：{os.path.abspath(output_dir)}")
    print("=" * 50)
    
    # 处理文件
    success_count = 0
    processed_files = 0
    file_times = []  # 记录每个文件的处理时间
    
    for input_path in txt_files:
        # 创建对应的输出目录
        rel_path = os.path.relpath(input_path, input_dir)
        output_subdir = os.path.join(output_dir, os.path.splitext(rel_path)[0])
        os.makedirs(os.path.dirname(output_subdir), exist_ok=True)
        
        # 处理文件
        success, elapsed_time = process_file(input_path, output_subdir, llm_processor)
        if success:
            success_count += 1
            file_times.append((os.path.basename(input_path), elapsed_time))
            
            # 统计生成的文件数量
            if os.path.exists(output_subdir):
                files = [f for f in os.listdir(output_subdir) if f.endswith('.txt') and f != '0.txt']
                processed_files += len(files)
    
    total_time = time.time() - total_start_time
    
    print("\n处理完成:")
    print(f"结束时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总耗时：{total_time:.2f}秒")
    print(f"成功处理: {success_count}/{len(txt_files)} 个文件")
    print(f"生成文件: {processed_files} 个")
    print(f"输出目录: {os.path.abspath(output_dir)}")
    
    # 打印每个文件的处理时间
    if file_times:
        print("\n各文件处理耗时:")
        for filename, t in file_times:
            print(f"  - {filename}: {t:.2f}秒")

def main():
    parser = argparse.ArgumentParser(description='使用LLM和jieba进行文本分句')
    parser.add_argument('--input_dir', '-i', 
                      default='output/docx_output',
                      help='输入文件夹路径 (默认: output/docx_output)')
    parser.add_argument('--output_dir', '-o',
                      default='output/llm_split_output',
                      help='输出文件夹路径 (默认: output/llm_split_output)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_dir):
        print(f"错误：输入目录 '{args.input_dir}' 不存在")
        return
    
    process_directory(args.input_dir, args.output_dir)

if __name__ == "__main__":
    main()
