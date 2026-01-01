# Image generation example (task create + poll result).
import time
import requests
import sys

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

API_KEY = "pA3uYXtPw3vV3sb3khjGTe8D5Jbi7Bm1Ohk6rGSyXParemqqszyOG5v5-onI62EkR1q-9pqjCgSC-3jQUoiETg"
CREATE_URL = "https://www.sophnet.com/api/open-apis/projects/easyllms/imagegenerator/task"

payload = {
    "model": "qwen-image",
    "input": {"prompt": "奔跑小猫"},
    "parameters": {"size": "1328*1328", "seed": 42},
}

headers = {"Authorization": f"Bearer {API_KEY}"}

create_resp = requests.post(CREATE_URL, headers=headers, json=payload, timeout=60)
print("create_status_code:", create_resp.status_code)
print("create_body:", create_resp.text)
create_resp.raise_for_status()

task_id = create_resp.json().get("output", {}).get("taskId")
if not task_id:
    raise SystemExit("No taskId returned.")

status_url = f"{CREATE_URL}/{task_id}"

for i in range(10):
    time.sleep(2)
    status_resp = requests.get(
        status_url,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        timeout=60,
    )
    print(f"poll_{i+1}_status_code:", status_resp.status_code)
    print(f"poll_{i+1}_body:", status_resp.text)
    if status_resp.status_code != 200:
        continue

    data = status_resp.json().get("output", {})
    status = data.get("taskStatus")
    if status == "SUCCEEDED":
        results = data.get("results") or []
        if results and isinstance(results, list):
            print("image_url:", results[0].get("url"))
        break
    if status in {"FAILED", "CANCELED"}:
        break
