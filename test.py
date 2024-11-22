import requests

class LLMProcessor:
    def __init__(self, model="qwen2.5-coder:7b"):
        """初始化LLM处理器"""
        self.base_url = "http://localhost:11434/api"
        self.headers = {"Content-Type": "application/json"}
        self.model = model
        
        # 修改初始化提示词，强调逻辑内容的提取
        self.system_prompt = """你是一个中文文本处理助手。你的任务是提取和优化文本的核心逻辑内容：

主要处理规则：
1. 删除所有技术性标记，如：(P>0.05)、(n=100)等统计学标记
2. 删除所有序号标记，如：(1)、（二）等
3. 删除所有英文内容
4. 删除不影响理解的括号内容
5. 删除去掉后对文本逻辑没有影响的数字

但要保留：
1. 核心的逻辑内容和关键信息
2. 必要的专业术语
3. 句子的完整性和通顺性

请用一个例子确认你理解了规则：
输入：'（3）研究结果(n=500)表明，3学生的学习成绩(P<0.01)显著提高。'
输出：'研究结果表明，学生的学习成绩显著提高。'


请回复：明白。"""
        
        # 初始化模型
        self._init_model()
        
    def _init_model(self):
        """初始化模型设置"""
        try:
            response = self._generate_completion(self.system_prompt)
            print("模型初始化状态：", response)
        except Exception as e:
            print(f"❌ 初始化错误: {str(e)}")
            
    def _generate_completion(self, prompt):
        """发送请求到Ollama API"""
        url = f"{self.base_url}/generate"
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        response = requests.post(url, headers=self.headers, json=data)
        return response.json().get('response', '')
        
    def process_text(self, text: str):
        """处理单个文本"""
        try:
            print("\n原文：", text)
            prompt = f"""请按照之前设定的规则处理以下文本，保留核心逻辑内容，删除技术性标记：

{text}"""
            print("\n处理后：")
            response = self._generate_completion(prompt)
            print(response)
            return response
        except Exception as e:
            print(f"❌ 处理错误: {str(e)}")
            return None

# 测试代码
test_text = """（2）工作记忆和短时记忆 
	短时记忆（short-term memory）是个体对刺激信息进行加工、编码、短暂保持和容量有限的记忆。"""
processor = LLMProcessor()
processor.process_text(test_text)