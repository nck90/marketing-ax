"""Step 4: Researcher - 웹 검색으로 실제 데이터 수집 + LLM 정리"""

import json
from api_utils import call_llm, parse_json_response


def web_search(query, max_results=3):
    """DuckDuckGo 웹 검색"""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS(timeout=10) as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "body": r.get("body", ""),
                    "href": r.get("href", ""),
                })
        return results
    except Exception as e:
        print(f"  [Researcher] 검색 실패: {e}")
        return []


def run(editor_plan, api_client=None):
    if api_client is None:
        print("[Researcher] STUB 모드")
        slides = []
        for slide in editor_plan.get("slides", []):
            slides.append({
                "slide_index": slide["slide_index"],
                "facts": ["(STUB)"], "examples": ["(STUB)"],
                "trends": ["(STUB)"], "source_context": "(STUB)",
            })
        return {"slides": slides, "overall_context": "(STUB)", "key_statistics": []}

    # 1. 기획안에서 검색 키워드 추출
    angle = editor_plan.get("angle", "")
    slides = editor_plan.get("slides", [])
    research_topics = [angle]
    for s in slides:
        rn = s.get("research_needed")
        if rn:
            research_topics.append(rn)

    # 2. 웹 검색 실행
    print("  [Researcher] 웹 검색 중...")
    all_search_results = []
    for topic in research_topics[:4]:  # 최대 4개 검색
        results = web_search(topic)
        all_search_results.extend(results)
        print(f"    검색: '{topic[:40]}...' → {len(results)}건")

    search_text = "\n".join(
        f"- {r['title']}: {r['body']}" for r in all_search_results
    )

    # 3. LLM으로 검색 결과를 기획안에 맞게 정리
    prompt = f"""다음 검색 결과를 카드뉴스 기획안에 맞게 정리해줘. 반드시 JSON만 출력.

## 기획안
{json.dumps(editor_plan, ensure_ascii=False, indent=2)}

## 검색 결과
{search_text[:4000]}

## 출력 형식 (JSON만)
{{
    "slides": [
        {{
            "slide_index": 0,
            "facts": ["구체적 팩트 (수치 포함)"],
            "examples": ["실제 사례"],
            "trends": ["최신 트렌드"],
            "source_context": "출처"
        }}
    ],
    "overall_context": "전체 맥락",
    "key_statistics": ["핵심 통계"]
}}"""

    text = call_llm(prompt)
    try:
        return parse_json_response(text)
    except (json.JSONDecodeError, IndexError):
        return {
            "slides": [],
            "overall_context": search_text[:2000],
            "key_statistics": [],
        }
