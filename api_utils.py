"""텍스트: OpenRouter 무료 모델 / 이미지: HuggingFace"""

import json
import os
import time
import httpx

OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
FREE_MODELS = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "minimax/minimax-m2.5:free",
    "stepfun/step-3.5-flash:free",
]


def call_llm(prompt, max_retries=5):
    """OpenRouter 무료 모델 호출 - 실패 시 다른 모델로 폴백"""
    for model in FREE_MODELS:
        for attempt in range(max_retries):
            try:
                resp = httpx.post(
                    OPENROUTER_URL,
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "You are a helpful assistant. Always respond in Korean. When asked for JSON, output ONLY valid JSON with no extra text."},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.7,
                        "max_tokens": 4000,
                    },
                    timeout=300,
                )
                data = resp.json()
                if "error" in data:
                    code = data["error"].get("code", "")
                    if code in [429, "429"]:
                        wait = (attempt + 1) * 10
                        print(f"  [API] {model} rate limited - {wait}초 대기 ({attempt+1}/{max_retries})")
                        time.sleep(wait)
                        continue
                    # 다른 에러면 다음 모델로
                    print(f"  [API] {model} 에러 - 다음 모델 시도")
                    break

                resp.raise_for_status()
                text = data["choices"][0]["message"]["content"]
                time.sleep(2)
                return text
            except Exception as e:
                err_str = str(e)
                if any(k in err_str for k in ["429", "503", "500", "rate"]):
                    wait = (attempt + 1) * 10
                    print(f"  [API] {type(e).__name__} - {wait}초 후 재시도 ({attempt+1}/{max_retries})")
                    time.sleep(wait)
                else:
                    print(f"  [API] {model} 실패: {err_str[:80]} - 다음 모델 시도")
                    break
    raise RuntimeError("모든 무료 모델 호출 실패")


def parse_json_response(text):
    """응답에서 JSON 추출"""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)
