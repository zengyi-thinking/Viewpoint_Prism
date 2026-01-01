# -*- coding: utf-8 -*-
import httpx

API_KEY = "pA3uYXtPw3vV3sb3khjGTe8D5Jbi7Bm1Ohk6rGSyXParemqqszyOG5v5-onI62EkR1q-9pqjCgSC-3jQUoiETg"
CREATE_URL = "https://www.sophnet.com/api/open-apis/projects/easyllms/imagegenerator/task"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

payload = {
    "model": "qwen-image",
    "input": {"prompt": "奔跑小猫"},
    "parameters": {"size": "1024*1024"},
}

print("Testing with httpx...")

with httpx.Client(timeout=60.0) as client:
    resp = client.post(CREATE_URL, headers=headers, json=payload)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")

    if resp.status_code == 200:
        data = resp.json()
        task_id = data.get("output", {}).get("taskId")
        print(f"Task ID: {task_id}")
