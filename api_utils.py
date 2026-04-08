"""HuggingFace Inference API - 텍스트 생성 유틸리티"""

import json
import os
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from huggingface_hub import InferenceClient

HF_TOKEN = os.environ.get("HF_TOKEN", "")
HF_TEXT_MODELS = [
    "Qwen/Qwen2.5-72B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",
]

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = InferenceClient(token=HF_TOKEN)
    return _client


def call_llm(prompt, max_retries=5):
    """HuggingFace 텍스트 생성 - 모델 자동 폴백"""
    client = _get_client()

    for model in HF_TEXT_MODELS:
        for attempt in range(max_retries):
            try:
                response = client.chat_completion(
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant. Always respond in Korean. When asked for JSON, output ONLY valid JSON with no extra text."},
                        {"role": "user", "content": prompt},
                    ],
                    model=model,
                    max_tokens=4000,
                    temperature=0.7,
                )
                text = response.choices[0].message.content
                time.sleep(1)
                return text
            except Exception as e:
                err_str = str(e)
                if any(k in err_str for k in ["429", "503", "500", "rate", "quota", "busy", "overloaded"]):
                    wait = (attempt + 1) * 10
                    print(f"  [API] {model} - {wait}초 후 재시도 ({attempt+1}/{max_retries})")
                    time.sleep(wait)
                elif "402" in err_str or "Payment" in err_str:
                    print(f"  [API] {model} 크레딧 소진 - 다음 모델 시도")
                    break
                else:
                    print(f"  [API] {model} 에러: {err_str[:60]} - 다음 모델 시도")
                    break
    raise RuntimeError("모든 텍스트 모델 호출 실패")


def parse_json_response(text):
    """응답에서 JSON 추출"""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)
