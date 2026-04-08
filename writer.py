"""Step 5: Writer - 최종 카드뉴스 텍스트 작성"""

import json
from api_utils import call_llm, parse_json_response
from prompts.prompts import WRITER_PROMPT


def run(editor_plan, research_data, brand, api_client=None, slide_count=5):
    content_count = max(1, slide_count - 2)

    if api_client is None:
        print("[Writer] STUB 모드")
        slides = [{"slide_type": "cover", "heading": "제목", "body": "부제", "image_prompt": "placeholder"}]
        for i in range(content_count):
            slides.append({"slide_type": "content", "category_tag": f"Point {i+1:02d}", "heading": f"포인트{i+1}", "body": "내용", "image_prompt": "placeholder"})
        slides.append({"slide_type": "last", "heading": "마무리", "body": "CTA", "image_prompt": "placeholder"})
        return {"slides": slides}

    prompt = WRITER_PROMPT.format(
        target_audience=brand.get("target_audience", ""),
        editor_plan=json.dumps(editor_plan, ensure_ascii=False, indent=2),
        research_data=json.dumps(research_data, ensure_ascii=False, indent=2),
        slide_count=slide_count,
        content_count=content_count,
        content_count_plus1=content_count + 1,
    )
    text = call_llm(prompt)
    try:
        result = parse_json_response(text)
        if "slides" in result and len(result["slides"]) > slide_count:
            result["slides"] = result["slides"][:slide_count]
        return result
    except (json.JSONDecodeError, IndexError):
        # JSON 파싱 실패 시 간결한 재시도
        print("  [Writer] JSON 파싱 실패 - 재시도 중...")
        content_slides = "\n".join(
            f'  {{"slide_type":"content","category_tag":"Point {i+1:02d}","heading":"제목","body":"내용","image_prompt":"..."}}'
            for i in range(content_count)
        )
        retry_prompt = f"""기획안 앵글: {editor_plan.get('angle', '')}
이것을 올리디아 스타일 {slide_count}장 카드뉴스로 만들어줘. 반드시 완전한 JSON만 출력.
image_prompt는 영어 1문장. 한국어만 사용.

{{"slides":[
  {{"slide_type":"cover","heading":"짧은훅","body":"부제","image_prompt":"..."}},
{content_slides},
  {{"slide_type":"last","heading":"이런 분들께","body":"항목1 / 항목2 / 항목3","image_prompt":"..."}}
]}}"""
        text2 = call_llm(retry_prompt)
        try:
            return parse_json_response(text2)
        except (json.JSONDecodeError, IndexError):
            raise ValueError(f"Writer JSON 파싱 실패: {text2[:300]}")
