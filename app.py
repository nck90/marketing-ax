"""Flask 웹앱 - AI 카드뉴스 생성기 (CardFlow)"""

import io
import json
import os
import sys
import uuid
import zipfile
from datetime import datetime
from threading import Thread
from werkzeug.utils import secure_filename

# .env 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask import Flask, jsonify, render_template, request, send_file

# 현재 디렉토리를 sys.path에 추가 (기존 모듈 import 용)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import editor
import image_generator
import renderer
import researcher
import scraper
import writer

app = Flask(__name__)

# 진행 상태 저장 (세션ID → 상태)
_jobs: dict[str, dict] = {}

# ── Usage tracking ──────────────────────────────────────

USAGE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "usage.json")
PERSONA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "persona.json")


def _load_usage() -> dict:
    current_month = datetime.now().strftime("%Y-%m")
    if os.path.isfile(USAGE_FILE):
        with open(USAGE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("month") == current_month:
            return data
    return {"month": current_month, "generations": 0, "images": 0, "api_calls": 0}


def _save_usage(data: dict):
    with open(USAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _increment_usage(generations=0, images=0, api_calls=0):
    data = _load_usage()
    data["generations"] += generations
    data["images"] += images
    data["api_calls"] += api_calls
    _save_usage(data)


def load_brand(filepath=None):
    """brand.md에서 브랜드 정보 로드"""
    if filepath is None:
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brand.md")
    brand = {}
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    for line in content.split("\n"):
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

    brand.setdefault("brand_name", "올리디아")
    brand.setdefault("main_color", "#1a1a2e")
    brand.setdefault("sub_color", "#e8d5b7")
    brand.setdefault("target_audience", "피부 노화와 주름 개선에 관심있는 30~50대 여성")
    brand.setdefault("audience_interest", "안티에이징 시술 트렌드")
    brand.setdefault("cta_text", "올리디아 공식 인스타그램에서 더 많은 정보를 확인하세요")
    brand.setdefault("topic", "뷰티/안티에이징")
    return brand


def run_pipeline(job_id: str, topic: str, url: str = "", extract_images: bool = False,
                 slide_count: int = 5, template_style: str = "mix", uploaded_images: list = None):
    """백그라운드 파이프라인 실행"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "output", f"session_{job_id}")
    os.makedirs(output_dir, exist_ok=True)

    job = _jobs[job_id]
    api_client = "openrouter"
    blog_images = []  # 블로그에서 추출한 이미지 경로
    if uploaded_images is None:
        uploaded_images = []

    try:
        # Step 0: 브랜드 로드 + URL 처리
        _set_step(job, "브랜드 정보 로드 중...", 5)
        brand = load_brand()

        # URL이 있으면 스크레이핑
        if url:
            _set_step(job, "URL에서 콘텐츠 추출 중...", 8)
            content = scraper.scrape_url(url)

            # 이미지 추출 옵션
            if extract_images:
                _set_step(job, "블로그 이미지 다운로드 중...", 10)
                blog_images = scraper.extract_images(url, output_dir)
                print(f"  [Scraper] {len(blog_images)}개 이미지 다운로드 완료")

            _set_step(job, "콘텐츠 요약 중...", 12)
            from api_utils import call_llm
            summary = call_llm(
                f"다음 글의 핵심 내용을 500자 이내로 요약해줘. 주요 포인트 3~5개를 뽑아줘:\n\n{content[:3000]}"
            )
            # topic이 비어있으면 URL 내용을 topic으로
            if not topic:
                topic = f"다음 내용을 기반으로 카드뉴스를 만들어줘:\n\n{summary}"
            else:
                topic = f"{topic}\n\n참고 자료:\n{summary}"

        # Step 1: 기획안 (Editor)
        _set_step(job, "기획안 작성 중... (Editor)", 15)
        editor_plan = editor.run(topic, brand, api_client, slide_count=slide_count)
        _save_json(editor_plan, output_dir, "editor_plan.json")

        # Step 2: 리서치 (Researcher)
        _set_step(job, "팩트 리서치 중... (Researcher)", 30)
        research_data = researcher.run(editor_plan, api_client)
        _save_json(research_data, output_dir, "research.json")

        # Step 3: 최종 텍스트 (Writer)
        _set_step(job, "카드뉴스 텍스트 작성 중... (Writer)", 50)
        writer_result = writer.run(editor_plan, research_data, brand, api_client, slide_count=slide_count)
        slides_data = writer_result.get("slides", [])
        _save_json(writer_result, output_dir, "writer.json")

        # Step 4: 이미지 결정 (업로드 > 블로그 > AI 생성 순서)
        if uploaded_images and len(uploaded_images) >= len(slides_data):
            _set_step(job, "업로드된 이미지 적용 중...", 65)
            image_paths = uploaded_images[:len(slides_data)]
        elif uploaded_images:
            _set_step(job, "업로드 이미지 + AI 이미지 생성 중...", 65)
            remaining = [s for i, s in enumerate(slides_data) if i >= len(uploaded_images)]
            ai_paths = image_generator.run(remaining, output_dir)
            image_paths = list(uploaded_images) + ai_paths
        elif blog_images and len(blog_images) >= len(slides_data):
            _set_step(job, "블로그 이미지 적용 중...", 65)
            image_paths = blog_images[:len(slides_data)]
        elif blog_images:
            _set_step(job, "블로그 이미지 + AI 이미지 생성 중...", 65)
            # 블로그 이미지로 채우고 부족분은 AI 생성
            remaining = [s for i, s in enumerate(slides_data) if i >= len(blog_images)]
            ai_paths = image_generator.run(remaining, output_dir)
            image_paths = blog_images[:] + ai_paths
        else:
            _set_step(job, "AI 배경 이미지 생성 중... (HuggingFace)", 65)
            image_paths = image_generator.run(slides_data, output_dir)

        # Step 5: HTML → PNG 렌더링
        _set_step(job, "슬라이드 렌더링 중...", 85)
        # renderer는 templates/ 기준 상대 경로를 사용하므로 cwd 변경
        orig_cwd = os.getcwd()
        os.chdir(base_dir)
        png_paths = renderer.run(slides_data, brand, image_paths, output_dir, template_style=template_style)
        os.chdir(orig_cwd)

        # 결과 저장
        slides_info = []
        for i, (slide, png_path) in enumerate(zip(slides_data, png_paths)):
            slides_info.append({
                "index": i,
                "slide_type": slide.get("slide_type", "content"),
                "heading": slide.get("heading", ""),
                "png_path": png_path,
                "png_exists": os.path.isfile(png_path),
            })

        job["status"] = "done"
        job["progress"] = 100
        job["message"] = "생성 완료!"
        job["output_dir"] = output_dir
        job["slides"] = slides_info

        # 사용량 트래킹
        _increment_usage(generations=1, images=len(slides_info), api_calls=3)

    except Exception as e:
        job["status"] = "error"
        job["message"] = f"오류 발생: {str(e)}"
        import traceback
        job["traceback"] = traceback.format_exc()


def _set_step(job: dict, message: str, progress: int):
    job["message"] = message
    job["progress"] = progress


def _save_json(data, output_dir: str, filename: str):
    path = os.path.join(output_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Routes ──────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("web.html")


@app.route("/favicon.ico")
def favicon():
    return "", 204


@app.route("/upload", methods=["POST"])
def upload_images():
    """이미지 업로드 엔드포인트"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    upload_dir = os.path.join(base_dir, "output", "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    files = request.files.getlist("images")
    if not files:
        return jsonify({"error": "업로드된 파일이 없습니다."}), 400

    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    saved_paths = []
    for f in files:
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            continue
        filename = uuid.uuid4().hex + ext
        path = os.path.join(upload_dir, filename)
        f.save(path)
        saved_paths.append(path)

    if not saved_paths:
        return jsonify({"error": "유효한 이미지 파일이 없습니다."}), 400

    return jsonify({"paths": saved_paths, "count": len(saved_paths)})


@app.route("/generate", methods=["POST"])
def generate():
    """카드뉴스 생성 시작"""
    if request.is_json:
        data = request.get_json() or {}
        topic = data.get("topic", "").strip()
        url = data.get("url", "").strip()
        extract_images = data.get("extract_images", False)
        slide_count = int(data.get("slide_count", 5))
        template_style = data.get("template_style", "mix").strip()
        uploaded_images = data.get("uploaded_images", [])
    else:
        topic = request.form.get("topic", "").strip()
        url = request.form.get("url", "").strip()
        extract_images = bool(request.form.get("extract_images"))
        slide_count = int(request.form.get("slide_count", 5))
        template_style = request.form.get("template_style", "mix").strip()
        uploaded_images = []

    # slide_count 범위 제한
    slide_count = max(3, min(10, slide_count))

    if not topic and not url:
        return jsonify({"error": "내용 또는 URL을 입력해주세요."}), 400

    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = {
        "status": "running",
        "progress": 0,
        "message": "파이프라인 시작 중...",
        "slides": [],
        "output_dir": "",
    }

    thread = Thread(
        target=run_pipeline,
        args=(job_id, topic, url, extract_images, slide_count, template_style, uploaded_images),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status(job_id: str):
    """작업 진행 상태 조회"""
    job = _jobs.get(job_id)
    if not job:
        return jsonify({"error": "작업을 찾을 수 없습니다."}), 404
    return jsonify({
        "status": job["status"],
        "progress": job["progress"],
        "message": job["message"],
        "slides": job.get("slides", []),
    })


@app.route("/slide/<job_id>/<int:slide_index>")
def serve_slide(job_id: str, slide_index: int):
    """슬라이드 PNG 파일 서빙"""
    job = _jobs.get(job_id)
    if not job or job["status"] != "done":
        return "Not found", 404

    slides = job.get("slides", [])
    if slide_index >= len(slides):
        return "Not found", 404

    png_path = slides[slide_index]["png_path"]
    if not os.path.isfile(png_path):
        # PNG 변환 실패 시 HTML 파일 존재 여부 확인
        html_path = png_path.replace(".png", ".html")
        if os.path.isfile(html_path):
            return send_file(html_path, mimetype="text/html")
        return "Image not found", 404

    return send_file(png_path, mimetype="image/png")


@app.route("/download/<job_id>/<int:slide_index>")
def download_slide(job_id: str, slide_index: int):
    """개별 슬라이드 PNG 다운로드"""
    job = _jobs.get(job_id)
    if not job or job["status"] != "done":
        return "Not found", 404

    slides = job.get("slides", [])
    if slide_index >= len(slides):
        return "Not found", 404

    png_path = slides[slide_index]["png_path"]
    if not os.path.isfile(png_path):
        return "Image not found", 404

    return send_file(
        png_path,
        mimetype="image/png",
        as_attachment=True,
        download_name=f"slide_{slide_index + 1:02d}.png",
    )


@app.route("/download-all/<job_id>")
def download_all(job_id: str):
    """모든 슬라이드를 ZIP으로 다운로드"""
    job = _jobs.get(job_id)
    if not job or job["status"] != "done":
        return "Not found", 404

    slides = job.get("slides", [])
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, slide in enumerate(slides):
            png_path = slide["png_path"]
            if os.path.isfile(png_path):
                zf.write(png_path, f"slide_{i + 1:02d}.png")

    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name="card_news.zip",
    )


@app.route("/api/usage")
def api_usage():
    """이번 달 사용량 반환"""
    return jsonify(_load_usage())


@app.route("/api/sns/instagram/connect", methods=["POST"])
def sns_instagram_connect():
    """Instagram 계정 연결 (instagrapi 사용 시도, 없으면 더미 응답)"""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "사용자명과 비밀번호를 입력해주세요."}), 400

    try:
        from instagrapi import Client
        cl = Client()
        cl.login(username, password)
        user = cl.user_info_by_username(username)
        profile = {
            "username": username,
            "full_name": user.full_name,
            "followers": user.follower_count,
            "following": user.following_count,
            "posts": user.media_count,
            "profile_pic": str(user.profile_pic_url) if user.profile_pic_url else "",
            "biography": user.biography or "",
        }
        return jsonify({"success": True, "profile": profile})
    except ImportError:
        # instagrapi 미설치 시 더미 응답
        profile = {
            "username": username,
            "full_name": username,
            "followers": 0,
            "following": 0,
            "posts": 0,
            "profile_pic": "",
            "biography": "(instagrapi 미설치 — 더미 데이터)",
        }
        return jsonify({"success": True, "profile": profile})
    except Exception as e:
        return jsonify({"error": f"로그인 실패: {str(e)}"}), 400


@app.route("/api/sns/instagram/analyze", methods=["POST"])
def sns_instagram_analyze():
    """Instagram 계정 페르소나 분석 - URL 또는 저장된 데이터 기반"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data = request.get_json() or {}
    instagram_url = data.get("url", "").strip()

    posts_sample = []

    # 1. URL이 주어지면 스크레이핑으로 데이터 수집
    if instagram_url:
        import re
        # URL에서 username 추출
        match = re.search(r'instagram\.com/([^/?]+)', instagram_url)
        username = match.group(1) if match else instagram_url.replace("@", "")

        try:
            from instaloader import Instaloader
            L = Instaloader()
            L.login(os.environ.get("IG_USERNAME", ""), os.environ.get("IG_PASSWORD", ""))
            session = L.context._session
            headers = {**session.headers, "X-IG-App-ID": "936619743392459"}
            resp = session.get(
                "https://i.instagram.com/api/v1/users/web_profile_info/",
                params={"username": username},
                headers=headers,
            )
            if resp.status_code == 200:
                user = resp.json().get("data", {}).get("user", {})
                media = user.get("edge_owner_to_timeline_media", {})
                for edge in media.get("edges", [])[:12]:
                    node = edge["node"]
                    cap = node.get("edge_media_to_caption", {}).get("edges", [])
                    caption = cap[0]["node"]["text"] if cap else ""
                    posts_sample.append({
                        "caption": caption[:500],
                        "likes": node.get("edge_liked_by", {}).get("count", 0),
                    })
        except Exception as e:
            print(f"  [Instagram] 스크레이핑 실패: {e}")

    # 2. URL 결과가 없으면 저장된 파일 사용
    if not posts_sample:
        posts_file = os.path.join(base_dir, "olidia_all_posts.json")
        if not os.path.isfile(posts_file):
            posts_file = os.path.join(base_dir, "olidia_posts.json")
        if os.path.isfile(posts_file):
            with open(posts_file, encoding="utf-8") as f:
                file_data = json.load(f)
            if isinstance(file_data, dict) and "posts" in file_data:
                posts_sample = file_data["posts"][:12]
            elif isinstance(file_data, list):
                posts_sample = file_data[:12]

    if not posts_sample:
        return jsonify({"error": "분석할 게시물 데이터가 없습니다. 인스타그램 URL을 입력해주세요."}), 400

    try:
        from api_utils import call_llm
        brand = load_brand()

        prompt = f"""다음 인스타그램 게시물 데이터를 분석하여 브랜드 페르소나를 JSON 형식으로 작성해줘.

브랜드명: {brand.get('brand_name', '')}
샘플 게시물: {json.dumps(posts_sample[:8], ensure_ascii=False)}

반드시 다음 JSON 구조로만 응답해:
{{
  "brand": {{
    "name": "브랜드명",
    "main_color": "#E8862A",
    "sub_color": "#F5F3F0",
    "tagline": "브랜드 태그라인"
  }},
  "copy_style": {{
    "tone": "톤 설명",
    "key_phrases": ["핵심 표현1", "핵심 표현2"],
    "hooks": ["훅 문구1", "훅 문구2"]
  }},
  "visual_style": {{
    "colors": ["#색상1", "#색상2"],
    "image_types": ["이미지 유형1", "이미지 유형2"]
  }},
  "target_audience": "타겟 독자 설명",
  "hashtags": ["#해시태그1", "#해시태그2", "#해시태그3"]
}}"""

        result_text = call_llm(prompt)
        # JSON 파싱 시도
        import re
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            persona = json.loads(json_match.group())
        else:
            raise ValueError("JSON 파싱 실패")

        # 저장
        with open(PERSONA_FILE, "w", encoding="utf-8") as f:
            json.dump(persona, f, ensure_ascii=False, indent=2)

        return jsonify({"success": True, "persona": persona})
    except Exception as e:
        return jsonify({"error": f"분석 실패: {str(e)}"}), 500


@app.route("/api/persona")
def api_persona():
    """현재 페르소나 데이터 반환"""
    if os.path.isfile(PERSONA_FILE):
        with open(PERSONA_FILE, encoding="utf-8") as f:
            persona = json.load(f)
        return jsonify(persona)

    # 페르소나 없으면 brand.md 기반 기본값 반환
    brand = load_brand()
    default_persona = {
        "brand": {
            "name": brand.get("brand_name", ""),
            "main_color": brand.get("main_color", "#E8862A"),
            "sub_color": brand.get("sub_color", "#F5F3F0"),
            "tagline": brand.get("cta_text", ""),
        },
        "copy_style": {
            "tone": "신뢰감 있으면서도 친근하게",
            "key_phrases": [],
            "hooks": [],
        },
        "visual_style": {
            "colors": [brand.get("main_color", "#E8862A"), brand.get("sub_color", "#F5F3F0")],
            "image_types": [],
        },
        "target_audience": brand.get("target_audience", ""),
        "hashtags": [],
    }
    return jsonify(default_persona)


@app.route("/api/persona/save", methods=["POST"])
def api_persona_save():
    """페르소나 저장"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "데이터가 없습니다."}), 400
    with open(PERSONA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return jsonify({"success": True})


@app.route("/api/settings/save", methods=["POST"])
def api_settings_save():
    """설정 저장 (brand.md 업데이트)"""
    data = request.get_json() or {}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    brand_file = os.path.join(base_dir, "brand.md")

    brand_name = data.get("brand_name", "").strip()
    main_color = data.get("main_color", "#E8862A").strip()
    sub_color = data.get("sub_color", "#F5F3F0").strip()
    target_audience = data.get("target_audience", "").strip()

    content = f"""# 브랜드 가이드

## 브랜드 정보
- 브랜드명: {brand_name}
- 메인 컬러: {main_color}
- 서브 컬러: {sub_color}

## 타겟 독자 및 목표
- 내 카드뉴스의 타겟독자: {target_audience}
- 카드뉴스 게시 목표: {data.get("audience_interest", "")}

## 톤앤매너
- {data.get("tone", "신뢰감 있으면서도 친근하게")}

## CTA 문구
{data.get("cta_text", "")}
"""
    with open(brand_file, "w", encoding="utf-8") as f:
        f.write(content)

    return jsonify({"success": True})


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=debug, host="0.0.0.0", port=port)
