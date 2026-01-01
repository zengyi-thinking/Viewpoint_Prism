# Non-stream speech-to-text example.
import base64
import sys
import requests

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

API_KEY = "pA3uYXtPw3vV3sb3khjGTe8D5Jbi7Bm1Ohk6rGSyXParemqqszyOG5v5-onI62EkR1q-9pqjCgSC-3jQUoiETg"
PROJECT_ID = "5U57ROU7TqfeNINZnKzYZ5"
EASYLLM_ID = "x2u0AJ4lrwebvD95Znjgs"

API_URL = (
    f"https://www.sophnet.com/api/open-apis/projects/{PROJECT_ID}/easyllms/"
    "speechtotext/non-stream"
)

# Use a public URL if available. Otherwise, set LOCAL_AUDIO_PATH to build a data URL.
AUDIO_URL = "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20250210/iwaouc/asr_example.wav?spm=a2c4g.11186623.0.0.343c2117knegZm&file=asr_example.wav"
LOCAL_AUDIO_PATH = r"D:\DevProject\Viewpoint_Prism\output.wav"

def build_audio_url() -> str:
    if AUDIO_URL:
        return AUDIO_URL
    with open(LOCAL_AUDIO_PATH, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return f"data:audio/wav;base64,{encoded}"

payload = {
    "easyllm_id": EASYLLM_ID,
    "audio_url": build_audio_url(),
    "speech_recognition_param": {"format": "wav"},
}

resp = requests.post(
    API_URL,
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json=payload,
    timeout=120,
)

print("status_code:", resp.status_code)
print("body:", resp.text)
