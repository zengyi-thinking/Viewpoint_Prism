"""
测试 Chat API
"""
import requests
import json

# 配置
API_BASE = "http://localhost:8000/api"
SOURCE_ID = "bb762472-522e-448b-8e98-b86574b022e4"

print("=" * 60)
print("测试 Chat API")
print("=" * 60)

# 测试请求
request_data = {
    "session_id": "test_session",
    "message": "这个视频在讲什么？",
    "source_ids": [SOURCE_ID]
}

print(f"\n[请求]")
print(f"  URL: {API_BASE}/chat/")
print(f"  Data: {json.dumps(request_data, ensure_ascii=False, indent=2)}")

print(f"\n[发送请求...]")
response = requests.post(
    f"{API_BASE}/chat/",
    json=request_data,
    headers={"Content-Type": "application/json"}
)

print(f"\n[响应]")
print(f"  Status: {response.status_code}")
print(f"  Body: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

# 检查是否有 references
result = response.json()
references = result.get("references", [])
print(f"\n[References]")
print(f"  数量: {len(references)}")
for i, ref in enumerate(references[:3], 1):
    print(f"  [{i}] source_id={ref.get('source_id', 'N/A')}")
    print(f"      timestamp={ref.get('timestamp', 'N/A')}s")
    print(f"      text={ref.get('text', '')[:80]}...")

print("\n" + "=" * 60)
