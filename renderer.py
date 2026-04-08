"""Step 7: Renderer - HTML 템플릿 + 데이터 → PNG 출력"""

import os
import subprocess


def load_template(template_name: str) -> str:
    """HTML 템플릿 파일 로드"""
    path = os.path.join("templates", template_name)
    with open(path, encoding="utf-8") as f:
        return f.read()


def fill_template(html: str, variables: dict) -> str:
    """템플릿 변수 치환"""
    for key, value in variables.items():
        html = html.replace(f"{{{{{key}}}}}", str(value))
    return html


def render_slide(slide_data: dict, slide_index: int, brand: dict, image_path: str, output_dir: str = "output", template_style: str = "mix") -> str:
    """단일 슬라이드를 PNG로 렌더링"""
    slide_type = slide_data.get("slide_type", "content")

    # 템플릿 선택 - 본문은 스타일 파라미터 또는 로테이션
    CONTENT_TEMPLATES = ["content_A.html", "content_B.html", "content_C.html"]
    STYLE_MAP = {"A": "content_A.html", "B": "content_B.html", "C": "content_C.html"}
    if slide_type == "cover":
        template_name = "first_page.html"
    elif slide_type == "last":
        template_name = "last_page.html"
    elif template_style in STYLE_MAP:
        template_name = STYLE_MAP[template_style]
    else:
        template_name = CONTENT_TEMPLATES[slide_index % len(CONTENT_TEMPLATES)]

    html = load_template(template_name)

    # 공통 변수
    variables = {
        "main_color": brand.get("main_color", "#E8862A"),
        "sub_color": brand.get("sub_color", "#F5F3F0"),
        "brand_name": brand.get("brand_name", "올리디아(Olidia)"),
        "image_path": os.path.abspath(image_path),
        "heading": slide_data.get("heading", ""),
        "body": slide_data.get("body", ""),
    }

    # 슬라이드 타입별 추가 변수
    if slide_type == "content":
        variables["category_tag"] = slide_data.get("category_tag", f"Point {slide_index:02d}")
    elif slide_type == "last":
        variables["cta_text"] = brand.get("cta_text", "더 알아보기")
        # 마지막 장 체크리스트 생성
        body_text = slide_data.get("body", "")
        lines = [l.strip() for l in body_text.replace("✓", "\n").replace("·", "\n").replace("/", "\n").split("\n") if l.strip()]
        if len(lines) <= 1:
            lines = [s.strip() for s in body_text.split(",") if s.strip()]
        checklist_items = []
        for line in lines[:5]:
            line = line.lstrip("- ·✓•")
            if line:
                checklist_items.append(
                    f'<div class="check-item"><div class="check-icon">✓</div>{line}</div>'
                )
        variables["checklist_html"] = "\n".join(checklist_items) if checklist_items else f'<div class="check-item"><div class="check-icon">✓</div>{body_text}</div>'
        variables["sub_heading"] = "추천드려요"
        # heading이 길면 분리
        heading = slide_data.get("heading", "")
        if len(heading) > 12:
            variables["heading"] = heading[:12]
            variables["sub_heading"] = heading[12:]
        else:
            variables["sub_heading"] = "추천드려요"

    filled_html = fill_template(html, variables)

    # HTML 파일 저장
    os.makedirs(output_dir, exist_ok=True)
    html_path = os.path.join(output_dir, f"slide_{slide_index}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(filled_html)

    # HTML → PNG 변환
    png_path = os.path.join(output_dir, f"slide_{slide_index}.png")
    html_to_png(html_path, png_path)

    return png_path


def html_to_png(html_path: str, png_path: str):
    """HTML 파일을 PNG로 변환 (여러 방법 시도)"""
    abs_html = os.path.abspath(html_path)
    file_url = f"file://{abs_html}"

    # 방법 1: playwright (가장 안정적)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1080, "height": 1350})
            page.goto(file_url)
            page.wait_for_timeout(500)
            page.screenshot(path=png_path, full_page=False)
            browser.close()
        print(f"  [Renderer] {png_path} 생성 (playwright)")
        return
    except (ImportError, Exception):
        pass

    # 방법 2: Chrome headless
    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "google-chrome",
        "chromium-browser",
    ]
    for chrome in chrome_paths:
        try:
            subprocess.run(
                [
                    chrome,
                    "--headless",
                    "--disable-gpu",
                    f"--window-size=1080,1350",
                    f"--screenshot={os.path.abspath(png_path)}",
                    file_url,
                ],
                capture_output=True,
                timeout=30,
                check=True,
            )
            print(f"  [Renderer] {png_path} 생성 (chrome)")
            return
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue

    # 방법 3: 변환 실패 시 HTML만 유지
    print(f"  [Renderer] PNG 변환 도구 없음 - HTML 파일만 생성: {html_path}")
    print(f"           → 브라우저에서 직접 열어 확인하세요")


def run(slides_data, brand, image_paths, output_dir="output", template_style="mix"):
    """전체 슬라이드 병렬 렌더링"""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    print(f"[Renderer] {len(slides_data)}개 슬라이드 병렬 렌더링 시작...")

    def render_one(args):
        i, slide = args
        img_path = image_paths[i] if i < len(image_paths) else ""
        return i, render_slide(slide, i, brand, img_path, output_dir, template_style)

    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(render_one, (i, s)): i for i, s in enumerate(slides_data)}
        for future in as_completed(futures):
            idx, path = future.result()
            results[idx] = path

    png_paths = [results[i] for i in range(len(slides_data))]
    print(f"[Renderer] 렌더링 완료 → {output_dir}/")
    return png_paths
