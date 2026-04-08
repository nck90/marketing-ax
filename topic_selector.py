"""Step 2: Topic Selector - 헤드라인 중 카드뉴스 주제 1개 선정"""

import json
from api_utils import call_llm, parse_json_response
from prompts.prompts import TOPIC_SELECTOR_PROMPT


def build_prompt(headlines, brand):
    headline_text = "\n".join(f"- {h['title']}" for h in headlines)
    return TOPIC_SELECTOR_PROMPT.format(
        topic=brand.get("topic", "뷰티/안티에이징"),
        target_audience=brand.get("target_audience", ""),
        audience_interest=brand.get("audience_interest", ""),
        headlines=headline_text,
    )


def run(headlines, brand, api_client=None):
    if api_client is None:
        print("[Topic Selector] STUB 모드")
        title = headlines[0]["title"] if headlines else "트렌드"
        return {"selected_topic": title}

    prompt = build_prompt(headlines, brand)
    text = call_llm(prompt)
    try:
        result = parse_json_response(text)
        if isinstance(result, list):
            result = {"curated_topics": result}
        return result
    except (json.JSONDecodeError, IndexError):
        return {"selected_topic": text.strip()[:200]}
