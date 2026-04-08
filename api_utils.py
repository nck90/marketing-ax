"""HuggingFace Inference API - 텍스트 생성 유틸리티"""

import json
import os
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import httpx
from huggingface_hub import InferenceClient

HF_TOKEN = os.environ.get("HF_TOKEN", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")

# HuggingFace 모델 (우선)
HF_TEXT_MODELS = [
    "Qwen/Qwen2.5-72B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",
]

# OpenRouter 무료 폴백
OPENROUTER_MODELS = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "minimax/minimax-m2.5:free",
    "stepfun/step-3.5-flash:free",
]

_hf_client = None


def _get_hf_client():
    global _hf_client
    if _hf_client is None:
        _hf_client = InferenceClient(token=HF_TOKEN)
    return _hf_client


def _call_hf(prompt, max_retries=3):
    """HuggingFace로 텍스트 생성"""
    client = _get_hf_client()
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
                if any(k in err_str for k in ["429", "503", "500", "rate", "busy", "overloaded"]):
                    wait = (attempt + 1) * 10
                    print(f"  [HF] {model} - {wait}초 후 재시도 ({attempt+1}/{max_retries})")
                    time.sleep(wait)
                elif "402" in err_str or "Payment" in err_str:
                    print(f"  [HF] {model} 크레딧 소진 - 다음 모델")
                    break
                else:
                    print(f"  [HF] {model} 에러: {err_str[:60]}")
                    break
    return None  # 전부 실패


def _call_openrouter(prompt, max_retries=3):
    """OpenRouter 무료 모델로 폴백"""
    key = OPENROUTER_KEY
    if not key:
        return None

    for model in OPENROUTER_MODELS:
        for attempt in range(max_retries):
            try:
                resp = httpx.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
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
                    if data["error"].get("code") in [429, "429"]:
                        time.sleep((attempt + 1) * 10)
                        continue
                    break
                text = data["choices"][0]["message"]["content"]
                time.sleep(2)
                return text
            except Exception as e:
                print(f"  [OR] {model} 에러: {str(e)[:60]}")
                break
    return None


def call_llm(prompt, max_retries=3):
    """텍스트 생성 - HuggingFace 우선, OpenRouter 폴백"""
    # 1차: HuggingFace
    result = _call_hf(prompt, max_retries)
    if result:
        return result

    # 2차: OpenRouter 폴백
    print("  [API] HuggingFace 실패 → OpenRouter 폴백")
    result = _call_openrouter(prompt, max_retries)
    if result:
        return result

    raise RuntimeError("모든 텍스트 모델 호출 실패")


def parse_json_response(text):
    """응답에서 JSON 추출"""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)
