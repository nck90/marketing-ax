"""
AI 카드뉴스 자동생성기 - 메인 파이프라인

실행: python main.py

텍스트 생성: OpenRouter (GPT-4o-mini)
이미지 생성: HuggingFace (Stable Diffusion XL)

파이프라인:
  1. Crawler      - 소스 크롤링
  2. Topic Selector - 주제 선정
  3. Editor       - 기획안 작성
  4. Researcher   - 리서치
  5. Writer       - 최종 텍스트
  6. Image Gen    - AI 배경 이미지 (HuggingFace)
  7. Renderer     - HTML → PNG
"""

import json
import os
import sys

import crawler
import topic_selector
import editor
import researcher
import writer
import image_generator
import renderer


def load_brand(filepath="brand.md"):
    brand = {}
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("- 브랜드명:"):
            brand["brand_name"] = line.split(":", 1)[1].strip()
        elif line.startswith("- 메인 컬러:"):
            brand["main_color"] = line.split(":", 1)[1].strip()
        elif line.startswith("- 서브 컬러:"):
            brand["sub_color"] = line.split(":", 1)[1].strip()
        elif line.startswith("- 내 카드뉴스의 타겟독자:"):
            brand["target_audience"] = line.split(":", 1)[1].strip()
        elif line.startswith("- 카드뉴스 게시 목표:"):
            brand["audience_interest"] = line.split(":", 1)[1].strip()

    if "## CTA 문구" in content:
        cta_section = content.split("## CTA 문구")[1].strip()
        cta_line = cta_section.split("\n")[0].strip()
        if cta_line:
            brand["cta_text"] = cta_line

    brand.setdefault("brand_name", "Brand")
    brand.setdefault("main_color", "#1a1a2e")
    brand.setdefault("sub_color", "#e8d5b7")
    brand.setdefault("target_audience", "")
    brand.setdefault("audience_interest", "")
    brand.setdefault("cta_text", "팔로우하기")
    brand.setdefault("topic", "뷰티/안티에이징")

    return brand


def save_intermediate(data, filename, output_dir="output"):
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  → 저장: {path}")


def main():
    print("=" * 60)
    print("  AI 카드뉴스 자동생성기")
    print("  텍스트: OpenRouter (GPT-4o-mini)")
    print("  이미지: HuggingFace (SDXL)")
    print("=" * 60)

    # API 클라이언트 마커 (None이 아니면 실제 API 사용)
    api_client = "openrouter"

    # 0. 브랜드 정보
    print("\n[Step 0] 브랜드 정보 로드")
    brand = load_brand()
    print(f"  브랜드: {brand['brand_name']}")
    print(f"  컬러: {brand['main_color']}")
    print()

    # 1. 크롤링
    print("[Step 1] 소스 크롤링")
    headlines = crawler.run()
    save_intermediate({"headlines": headlines}, "1_headlines.json")
    print()

    if not headlines:
        print("⚠ 수집된 헤드라인이 없습니다.")
        sys.exit(1)

    # 2. 주제 선정
    print("[Step 2] 주제 선정")
    topic_result = topic_selector.run(headlines, brand, api_client)
    if "selected_topic" in topic_result:
        selected_topic = topic_result["selected_topic"]
    elif "curated_topics" in topic_result and topic_result["curated_topics"]:
        first = topic_result["curated_topics"][0]
        selected_topic = first.get("topic") or first.get("title") or str(first)
    elif "topic" in topic_result:
        selected_topic = topic_result["topic"]
    else:
        selected_topic = str(topic_result)
    topic_result["selected_topic"] = selected_topic
    save_intermediate(topic_result, "2_topic.json")
    print(f"  선정 주제: {selected_topic}")
    print()

    # 3. 기획안
    print("[Step 3] 기획안 작성")
    editor_plan = editor.run(selected_topic, brand, api_client)
    save_intermediate(editor_plan, "3_editor_plan.json")
    print(f"  앵글: {editor_plan.get('angle', '')}")
    print()

    # 4. 리서치
    print("[Step 4] 리서치")
    research_data = researcher.run(editor_plan, api_client)
    save_intermediate(research_data, "4_research.json")
    print()

    # 5. 최종 텍스트
    print("[Step 5] 최종 텍스트 작성")
    writer_result = writer.run(editor_plan, research_data, brand, api_client)
    slides_data = writer_result["slides"]
    save_intermediate(writer_result, "5_writer.json")
    print(f"  슬라이드 {len(slides_data)}장 작성 완료")
    print()

    # 6. 이미지 생성 (HuggingFace)
    print("[Step 6] 이미지 생성 (HuggingFace)")
    image_paths = image_generator.run(slides_data, "output")
    print()

    # 7. 렌더링
    print("[Step 7] HTML → PNG 렌더링")
    png_paths = renderer.run(slides_data, brand, image_paths, "output")
    print()

    print("=" * 60)
    print("  완료!")
    print(f"  생성된 파일: output/ 폴더 확인")
    for p in png_paths:
        print(f"    - {p}")
    print("=" * 60)


if __name__ == "__main__":
    main()
