##参考文档：https://sophnet.com/docs/component/API.html#text-to-voice
import requests
import json
import base64

projectId = "5U57ROU7TqfeNINZnKzYZ5"
easyllmId = "7RUpfZakZM7tIygXY5AGgA"
API_KEY = "pA3uYXtPw3vV3sb3khjGTe8D5Jbi7Bm1Ohk6rGSyXParemqqszyOG5v5-onI62EkR1q-9pqjCgSC-3jQUoiETg"

url = f"https://www.sophnet.com/api/open-apis/projects/{projectId}/easyllms/voice/synthesize-audio-stream"

headers = {
   'Content-Type': 'application/json',
   'Authorization': 'Bearer ' + API_KEY,
}

payload = json.dumps({
   "easyllm_id": easyllmId,
   "text": [
       "你好，请你简单介绍一下自己，我是个傻逼",
   ],
   "synthesis_param": {
       "model": "cosyvoice-v1",
       "voice": "longxiaochun",
       "format": "MP3_16000HZ_MONO_128KBPS",
       "volume": 80,
       "speechRate": 1.2,
       "pitchRate": 1
   }
})

response = requests.request("POST", url, headers=headers, data=payload)
for chunk in response.iter_lines(decode_unicode=True):
    with open("output.mp3","ab") as f:
        if chunk:
            if (frame:=json.loads(chunk[5:])["audioFrame"]):
                f.write(base64.b64decode(frame))