# -*- coding: utf-8 -*-
import requests

API_KEY = "pA3uYXtPw3vV3sb3khjGTe8D5Jbi7Bm1Ohk6rGSyXParemqqszyOG5v5-onI62EkR1q-9pqjCgSC-3jQUoiETg"

CREATE_URL = "https://www.sophnet.com/api/open-apis/projects/easyllms/imagegenerator/task"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json; charset=utf-8",
}

# 使用简单英文测试
payload = {
    "model": "qwen-image",
    "input": {"prompt": "A cat running"},
    "parameters": {"size": "1024*1024"},
}

print(f"Testing with English prompt: A cat running")

resp = requests.post(CREATE_URL, headers=headers, json=payload, timeout=60)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:200]}")

if resp.status_code == 200:
    data = resp.json()
    task_id = data.get("output", {}).get("taskId")
    print(f"Task ID: {task_id}")

    # Poll for result
    import time
    status_url = f"{CREATE_URL}/{task_id}"
    for i in range(10):
        time.sleep(2)
        status_resp = requests.get(status_url, headers=headers, timeout=60)
        if status_resp.status_code == 200:
            result_data = status_resp.json().get("output", {})
            if result_data.get("taskStatus") == "SUCCEEDED":
                results = result_data.get("results") or []
                if results:
                    print(f"Image URL: {results[0].get('url')}")
                break
