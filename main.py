# my_main.py
from dotenv import load_dotenv
from my_llm import MyLLM # 注意:这里导入我们自己的类
import os

# 加载环境变量
load_dotenv()
model = os.getenv("LLM_MODEL_ID")
api_key = os.getenv("LLM_API_KEY")
base_url = os.getenv("LLM_BASE_URL")
# 实例化我们重写的客户端，并指定provider
llm = MyLLM(model=model, api_key=api_key, base_url=base_url, provider="deepseek") 

# 准备消息
messages = [{"role": "user", "content": "你好，请介绍一下你自己。"}]



# 发起调用，think等方法都已从父类继承，无需重写
print("Deepseek Response:")
response_stream = llm.think(messages)

# 打印响应

'''
for chunk in response_stream:
    # chunk 已经是文本片段，可以直接使用
    print(chunk, end="", flush=True)
'''