import pexpect
import sys
import time

def test_llama_connection():
    """测试Llama模型连接是否正常"""
    print("=== 开始测试Llama模型连接 ===\n")
    
    try:
        # 启动 ollama 交互式会话
        # child = pexpect.spawn('ollama run llama3.2:3b', encoding='utf-8')
        child = pexpect.spawn('ollama run qwen2.5-coder:7b', encoding='utf-8')
        
        # 等待提示符
        index = child.expect(['>>>', pexpect.EOF, pexpect.TIMEOUT], timeout=10)
        if index != 0:
            print("✗ 错误：无法启动模型交互式会话")
            return False
            
        print("✓ 成功启动模型交互式会话")
        
        # 发送测试消息
        test_prompt = "请用一句话回答：能介绍一下你自己吗？"
        print(f"\n发送测试提示：{test_prompt}")
        
        child.sendline(test_prompt)
        
        # 等待响应
        index = child.expect(['>>>', pexpect.EOF, pexpect.TIMEOUT], timeout=30)
        if index == 0:
            # 获取响应并处理
            response = child.before.strip()
            # 移除输入提示
            response = response.replace(test_prompt, '').strip()
            
            print("\n✓ 模型响应成功！")
            print("\n模型返回的测试回答：")
            print("-" * 50)
            print(response)
            print("-" * 50)
            
            # 退出会话
            child.sendline("/bye")
            return True
        else:
            print("\n✗ 等待模型响应超时或会话意外结束")
            return False
            
    except Exception as e:
        print(f"\n✗ 测试模型时出错: {str(e)}")
        print("错误类型:", type(e).__name__)
        return False
    finally:
        # 确保子进程被终止
        try:
            child.close()
        except:
            pass

if __name__ == "__main__":
    print("开始模型可用性测试...\n")
    
    try:
        if test_llama_connection():
            print("\n✓ 测试通过！模型工作正常，可以继续后续操作。")
            sys.exit(0)
        else:
            print("\n✗ 测试失败！请检查模型配置和运行状态。")
            print("\n故障排除建议：")
            print("1. 确保 ollama 服务正在运行（运行 'ollama serve'）")
            print("2. 检查模型是否正确安装（运行 'ollama list'）")
            print("3. 尝试重新拉取模型（运行 'ollama pull llama3.2:3b'）")
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ 程序执行出错: {str(e)}")
        sys.exit(1) 