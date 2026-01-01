# 支持兼容 OpenAI Python SDK  终端运行：pip install OpenAI
from openai import OpenAI
import sys
#image_url = "https://zh.freepik.com/%E7%85%A7%E7%89%87/%E5%9B%BE%E7%89%87"
if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
# 初始化客户端
client = OpenAI(
    api_key= "pA3uYXtPw3vV3sb3khjGTe8D5Jbi7Bm1Ohk6rGSyXParemqqszyOG5v5-onI62EkR1q-9pqjCgSC-3jQUoiETg",
    base_url= "https://www.sophnet.com/api/open-apis/v1"
)
# 调用接口
response = client.chat.completions.create(
    model="Qwen2.5-VL-72B-Instruct",
    messages=[
        {"role": "user", "content": [
                {"type": "text", "text": "这是什么"},
                {"type": "image_url", "image_url": {"url": "https://i.ibb.co/nQNGqL0/1beach1.jpg"}}
            ]}
    ]
)
# 打印结果
print(response.choices[0].message.content)
