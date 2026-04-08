"""Step 3: Editor - 슬라이드 기획안 작성"""

import json
from api_utils import call_llm, parse_json_response
from prompts.prompts import EDITOR_PROMPT


def run(selected_topic, brand, api_client=None, slide_count=5):
    content_count = max(1, slide_count - 2)  # cover + content slides + last

    if api_client is None:
        print("[Editor] STUB 모드")
        slides = [
            {"slide_index": 0, "slide_type": "cover", "purpose": "훅", "key_point": selected_topic, "research_needed": "관련 통계"},
        ]
        for i in range(content_count):
            slides.append({"slide_index": i + 1, "slide_type": "content", "purpose": f"포인트 {i+1}", "key_point": f"핵심 {i+1}", "research_needed": "데이터"})
        slides.append({"slide_index": slide_count - 1, "slide_type": "last", "purpose": "CTA", "key_point": "추천", "research_needed": None})
        return {
            "angle": f"'{selected_topic}' 핵심 포인트",
            "hook_strategy": "질문형 훅",
            "narrative_arc": "문제→원인→해결→효과→CTA",
            "slides": slides,
        }

    prompt = EDITOR_PROMPT.format(
        target_audience=brand.get("target_audience", ""),
        selected_topic=selected_topic,
        slide_count=slide_count,
        content_count=content_count,
        content_count_plus1=content_count + 1,
    )
    text = call_llm(prompt)
    try:
        return parse_json_response(text)
    except (json.JSONDecodeError, IndexError):
        raise ValueError(f"Editor JSON 파싱 실패: {text[:300]}")
