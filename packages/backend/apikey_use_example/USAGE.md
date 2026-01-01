# API Key Use Examples

This folder contains runnable examples for SophNet LLM APIs.

Prereqs:
- Python venv at `packages/backend/venv`
- Packages: `openai`, `requests`
- API key and IDs in `apikey_info.txt`

Notes:
- `image_url` must be a valid HTTPS URL or `data:` URL.
- These scripts print UTF-8 output on Windows.

## DeepSeek-V3.2 (chat)

Run:
```bash
packages/backend/venv/Scripts/python.exe packages/backend/apikey_use_example/DeepSeek-V3.2.py
```

## Qwen2.5-VL (vision)

Run:
```bash
packages/backend/venv/Scripts/python.exe packages/backend/apikey_use_example/Qwen2.5-VL.py
```

Make sure `image_url` points to a real image:
```json
{"type":"image_url","image_url":{"url":"https://example.com/image.jpg"}}
```

## CosyVoice (text to speech)

Run:
```bash
packages/backend/venv/Scripts/python.exe packages/backend/apikey_use_example/CosyVioce.py
```

The script writes `output.mp3` to the current working directory.

## BGE-M3 (embeddings)

HTTP example:
```bash
curl --location --request POST "https://www.sophnet.com/api/open-apis/projects/{projectId}/easyllms/embeddings" ^
  --header "Authorization: Bearer {API_KEY}" ^
  --header "Content-Type: application/json" ^
  --data-raw "{\"easyllm_id\":\"{YOUR_EMBEDDING_EASYLLM_ID}\",\"input_texts\":[\"你好\",\"很高兴认识你\"],\"dimensions\":1024}"
```

`easyllm_id` must be an embeddings model ID (it may be different from the voice model ID).

## Image generation (qwen-image)

Create task (see `imgegenration.txt` for the curl template):
```bash
curl --location --request POST "https://www.sophnet.com/api/open-apis/projects/easyllms/imagegenerator/task" ^
  --header "Authorization: Bearer {API_KEY}" ^
  --header "Content-Type: application/json" ^
  --data-raw "{\"model\":\"qwen-image\",\"input\":{\"prompt\":\"奔跑小猫\"},\"parameters\":{\"size\":\"1328*1328\",\"seed\":42}}"
```

Get task result (returns image URL):
```bash
curl --location --request GET "https://www.sophnet.com/api/open-apis/projects/easyllms/imagegenerator/task/{TaskId}" ^
  --header "Authorization: Bearer {API_KEY}" ^
  --header "Content-Type: application/json"
```
