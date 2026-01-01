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

## Paraformer (speech to text)

Audio URL mode:
```bash
curl --location --request POST "https://www.sophnet.com/api/open-apis/projects/easyllms/speechtotext/transcriptions" ^
  --header "Authorization: Bearer {API_KEY}" ^
  --header "Content-Type: application/json" ^
  --data-raw "{\"audio_url\":\"https://example.com/audio.wav\"}"
```

File upload mode:
```bash
curl --location --request POST "https://www.sophnet.com/api/open-apis/projects/easyllms/speechtotext/transcriptions" ^
  --header "Authorization: Bearer {API_KEY}" ^
  --form "audio_file=@/path/to/your_audio_file.wav;type=audio/wav"
```

