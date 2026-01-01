import requests

API_KEY = "pA3uYXtPw3vV3sb3khjGTe8D5Jbi7Bm1Ohk6rGSyXParemqqszyOG5v5-onI62EkR1q-9pqjCgSC-3jQUoiETg"

# Test using the exact same approach as sophnet_service.py
CREATE_URL = "https://www.sophnet.com/api/open-apis/projects/easyllms/imagegenerator/task"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

payload = {
    "model": "qwen-image",
    "input": {"prompt": "测试提示词"},
    "parameters": {"size": "1024*1024"},
}

print(f"URL: {CREATE_URL}")
print(f"Headers: {headers}")
print(f"Payload: {payload}")

resp = requests.post(CREATE_URL, headers=headers, json=payload, timeout=60)
print(f"\nStatus: {resp.status_code}")
print(f"Response: {resp.text}")

if resp.status_code == 200:
    data = resp.json()
    task_id = data.get("output", {}).get("taskId")
    print(f"Task ID: {task_id}")
