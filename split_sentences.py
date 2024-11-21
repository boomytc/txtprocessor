import os
import jieba


# 使用jieba进行中文分句
def split_sentences(text):
    sentences = []
    words = jieba.cut(text)
    sentence = []
    for word in words:
        sentence.append(word)
        if word in ["。", "！", "？"]:  # 判断句子的结尾符号
            sentences.append("".join(sentence))
            sentence = []
    if sentence:
        sentences.append("".join(sentence))
    return sentences


# 保存分句后的文本
def save_to_file(text, output_dir, filename):
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
        f.write(text)


# 分句并保存
def split_and_save(input_dir, output_dir):
    file_count = 0
    for filename in os.listdir(input_dir):
        if filename.endswith(".txt"):
            file_count += 1
            file_path = os.path.join(input_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            
            sentences = split_sentences(text)
            
            # 创建子目录来存放分句后的文件
            split_dir = os.path.join(output_dir, f"{file_count}")
            os.makedirs(split_dir, exist_ok=True)
            
            # 按顺序保存每个句子
            for idx, sentence in enumerate(sentences, start=1):
                save_to_file(sentence, split_dir, f"{file_count}-{idx}.txt")
    print(f"分句完成，共处理 {file_count} 个文件。")


# 主程序
if __name__ == "__main__":
    input_directory = "path/to/output/puredoc_output"  # 输入纯文本文件夹路径
    output_directory = "path/to/output/split_output"  # 输出分句文件夹路径
    split_and_save(input_directory, output_directory)
