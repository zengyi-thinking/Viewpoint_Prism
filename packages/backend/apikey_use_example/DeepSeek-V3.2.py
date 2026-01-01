# 支持兼容 OpenAI Python SDK  终端运行：pip install OpenAI
from openai import OpenAI
import sys

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# 初始化客户端
client = OpenAI(
    api_key= "pA3uYXtPw3vV3sb3khjGTe8D5Jbi7Bm1Ohk6rGSyXParemqqszyOG5v5-onI62EkR1q-9pqjCgSC-3jQUoiETg",
    base_url= "https://www.sophnet.com/api/open-apis/v1"
)
# 调用接口
response = client.chat.completions.create(
    model="DeepSeek-V3.2",
    messages=[
        {"role": "system", "content": "你是SophNet智能助手"},
        {"role": "user", "content": "你可以帮我做些什么"}
    ]
)
# 打印结果
print(response.choices[0].message.content)
