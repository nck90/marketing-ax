"""Step 1: 소스 크롤링 - RSS + 웹사이트 스크레이핑"""

import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from xml.etree import ElementTree

import httpx


def parse_sources(filepath: str = "news_sources.txt") -> list[str]:
    """news_sources.txt에서 URL 목록 파싱"""
    urls = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def parse_rss_date(date_str: str) -> Optional[datetime]:
    """RSS 날짜 문자열을 datetime으로 파싱"""
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
    ]
    date_str = date_str.replace("GMT", "+0000").replace("UTC", "+0000")
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def extract_items_from_xml(xml_text: str) -> list[dict]:
    """XML에서 RSS/Atom 아이템 추출"""
    items = []
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return items

    # RSS 2.0
    for item in root.iter("item"):
        title_el = item.find("title")
        pub_date_el = item.find("pubDate")
        link_el = item.find("link")
        if title_el is not None and title_el.text:
            items.append({
                "title": re.sub(r"<[^>]+>", "", title_el.text).strip(),
                "pub_date": pub_date_el.text.strip() if pub_date_el is not None and pub_date_el.text else None,
                "link": link_el.text.strip() if link_el is not None and link_el.text else None,
            })

    # Atom
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        updated_el = entry.find("atom:updated", ns)
        link_el = entry.find("atom:link", ns)
        if title_el is not None and title_el.text:
            items.append({
                "title": re.sub(r"<[^>]+>", "", title_el.text).strip(),
                "pub_date": updated_el.text.strip() if updated_el is not None and updated_el.text else None,
                "link": link_el.get("href") if link_el is not None else None,
            })

    return items


def extract_items_from_html(html_text: str, source_url: str) -> list[dict]:
    """HTML 웹사이트에서 텍스트 콘텐츠 추출"""
    # script, style 태그 제거
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)

    # 제목 태그 추출
    titles = []
    for tag in ['h1', 'h2', 'h3']:
        for match in re.finditer(rf'<{tag}[^>]*>(.*?)</{tag}>', text, re.DOTALL):
            clean = re.sub(r'<[^>]+>', '', match.group(1)).strip()
            if clean and len(clean) > 3:
                titles.append(clean)

    # meta description
    meta_desc = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html_text)
    if meta_desc:
        titles.insert(0, meta_desc.group(1).strip())

    # og:description
    og_desc = re.search(r'<meta\s+property="og:description"\s+content="([^"]*)"', html_text)
    if og_desc and og_desc.group(1).strip() not in titles:
        titles.insert(0, og_desc.group(1).strip())

    items = []
    seen = set()
    for title in titles:
        if title not in seen and len(title) > 5:
            seen.add(title)
            items.append({
                "title": title,
                "pub_date": None,
                "link": source_url,
            })

    return items


async def fetch_source(client: httpx.AsyncClient, url: str) -> list[dict]:
    """단일 소스 비동기 수집 (RSS 또는 웹사이트 자동 판별)"""
    try:
        resp = await client.get(url, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        content = resp.text

        # RSS/XML인지 판별
        if '<?xml' in content[:200] or '<rss' in content[:500] or '<feed' in content[:500]:
            return extract_items_from_xml(content)
        else:
            return extract_items_from_html(content, url)
    except Exception as e:
        print(f"  [WARN] {url} 수집 실패: {e}")
        return []


def filter_recent(items: list[dict], hours: int = 168) -> list[dict]:
    """최근 N시간 이내 기사만 필터링 (기본 7일)"""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    recent = []
    for item in items:
        if item["pub_date"]:
            dt = parse_rss_date(item["pub_date"])
            if dt:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt >= cutoff:
                    recent.append(item)
                    continue
        # 날짜 파싱 실패 또는 날짜 없는 경우 포함
        recent.append(item)
    return recent


async def crawl() -> list[dict]:
    """전체 크롤링 실행"""
    urls = parse_sources()
    print(f"[Crawler] {len(urls)}개 소스에서 크롤링 시작...")

    async with httpx.AsyncClient(
        headers={"User-Agent": "CardNewsBot/1.0"},
        verify=False,  # SSL 인증서 문제 우회
    ) as client:
        tasks = [fetch_source(client, url) for url in urls]
        results = await asyncio.gather(*tasks)

    all_items = []
    for items in results:
        all_items.extend(items)

    recent = filter_recent(all_items, hours=168)
    # 중복 제거
    seen = set()
    unique = []
    for item in recent:
        if item["title"] not in seen:
            seen.add(item["title"])
            unique.append(item)

    print(f"[Crawler] 총 {len(unique)}개 헤드라인 수집 완료")
    return unique


def run() -> list[dict]:
    """동기 래퍼"""
    return asyncio.run(crawl())


if __name__ == "__main__":
    headlines = run()
    for h in headlines[:10]:
        print(f"  - {h['title']}")
