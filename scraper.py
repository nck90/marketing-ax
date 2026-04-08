"""URL 스크레이핑 - 블로그/웹페이지에서 텍스트 추출"""

import re
import httpx


def scrape_url(url: str) -> str:
    """URL에서 본문 텍스트 추출"""
    try:
        resp = httpx.get(
            url,
            timeout=15,
            follow_redirects=True,
            verify=False,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
        )
        resp.raise_for_status()
        html = resp.text

        # script, style 제거
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

        # 제목 추출
        title = ""
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL)
        if title_match:
            title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()

        # og:title
        og_title = re.search(r'<meta\s+property="og:title"\s+content="([^"]*)"', html)
        if og_title:
            title = og_title.group(1).strip()

        # 본문 텍스트
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()

        # 앞뒤 불필요한 부분 제거 (네이버 블로그 등)
        for marker in ['본문 기타 기능', '본문 폰트 크기']:
            if marker in text:
                text = text.split(marker)[-1]

        # 뒤쪽 불필요 부분 제거
        for marker in ['댓글', '공감한 사람', '이웃추가', '인쇄하기']:
            if marker in text:
                text = text.split(marker)[0]

        text = text.strip()[:5000]  # 최대 5000자

        result = f"제목: {title}\n\n{text}" if title else text
        return result

    except Exception as e:
        return f"URL 스크레이핑 실패: {e}"


def extract_images(url: str, output_dir: str, max_images: int = 5) -> list:
    """블로그/웹페이지에서 이미지를 다운로드하여 저장"""
    import os
    os.makedirs(output_dir, exist_ok=True)

    try:
        resp = httpx.get(
            url,
            timeout=15,
            follow_redirects=True,
            verify=False,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "Referer": url,
            },
        )
        html = resp.text

        # img 태그에서 src 추출
        img_urls = []
        for match in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', html):
            src = match.group(1)
            # 작은 아이콘/로고 제외
            if any(skip in src.lower() for skip in ['icon', 'logo', 'btn', 'button', 'emoji', 'avatar', '1x1', 'spacer']):
                continue
            # 상대 경로 처리
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                from urllib.parse import urlparse
                parsed = urlparse(url)
                src = f"{parsed.scheme}://{parsed.netloc}{src}"
            if src.startswith("http"):
                img_urls.append(src)

        # data-src 도 체크 (네이버 블로그 lazy loading)
        for match in re.finditer(r'data-src=["\']([^"\']+)["\']', html):
            src = match.group(1)
            if src.startswith("//"):
                src = "https:" + src
            if src.startswith("http") and src not in img_urls:
                img_urls.append(src)

        # 이미지 다운로드
        saved_paths = []
        for i, img_url in enumerate(img_urls[:max_images * 2]):  # 여유분 확보
            if len(saved_paths) >= max_images:
                break
            try:
                img_resp = httpx.get(
                    img_url,
                    timeout=10,
                    follow_redirects=True,
                    verify=False,
                    headers={"Referer": url, "User-Agent": "Mozilla/5.0"},
                )
                content_type = img_resp.headers.get("content-type", "")
                if "image" not in content_type and len(img_resp.content) < 10000:
                    continue  # 이미지가 아니거나 너무 작으면 스킵

                # 최소 크기 필터 (10KB 이상)
                if len(img_resp.content) < 10000:
                    continue

                ext = "jpg"
                if "png" in content_type:
                    ext = "png"
                elif "webp" in content_type:
                    ext = "webp"

                path = os.path.join(output_dir, f"blog_img_{i}.{ext}")
                with open(path, "wb") as f:
                    f.write(img_resp.content)

                # 1080x1350으로 리사이즈
                try:
                    from PIL import Image
                    img = Image.open(path).convert("RGB")
                    img = img.resize((1080, 1350))
                    png_path = os.path.join(output_dir, f"slide_{len(saved_paths)}_bg.png")
                    img.save(png_path)
                    saved_paths.append(png_path)
                    os.remove(path)
                except ImportError:
                    saved_paths.append(path)

                print(f"  [Scraper] 이미지 {len(saved_paths)} 다운로드: {img_url[:60]}...")
            except Exception as e:
                continue

        return saved_paths

    except Exception as e:
        print(f"  [Scraper] 이미지 추출 실패: {e}")
        return []


def is_url(text: str) -> bool:
    """텍스트가 URL인지 판별"""
    return text.strip().startswith(("http://", "https://"))
