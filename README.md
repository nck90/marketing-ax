# CardFlow - AI 카드뉴스 자동생성 플랫폼

CardFlow는 주제 하나로 AI가 자동 기획하고, 리서치하고, 글을 쓰고, 이미지를 생성해 최종 PNG 슬라이드까지 완성하는 종단간(end-to-end) 카드뉴스 자동화 플랫폼입니다.

## 주요 기능

- **AI 카드뉴스 자동생성**: 주제 입력 → 기획안 → 리서치 → 텍스트 → 이미지 → PNG 렌더링 (완전자동)
- **URL 콘텐츠 스크레이핑**: 블로그/웹페이지 URL에서 본문 자동 추출
- **블로그 이미지 추출**: URL에서 이미지 자동 다운로드 및 활용
- **커스텀 이미지 업로드**: 기존 이미지 업로드 후 자동 적용
- **AI 배경 이미지 생성**: HuggingFace FLUX.1-schnell 모델로 병렬 생성
- **다중 템플릿 지원**: 표지/본문A/본문B/본문C/마지막 장 템플릿
- **브랜드 설정**: 색상, 폰트, CTA 문구, 타겟 독자 등 커스터마이징
- **SNS 연동**: Instagram 계정 연결 및 페르소나 자동분석
- **슬라이드 개수 제어**: 3~10장 범위 내 자유 설정
- **일괄 다운로드**: 생성된 모든 슬라이드를 ZIP으로 일괄 다운로드

## 기술 스택

| 영역 | 기술 |
|------|------|
| **백엔드** | Flask (Python 3) |
| **텍스트 AI** | OpenRouter (무료 모델: Nemotron, Minimax, StepFun) |
| **이미지 생성** | HuggingFace FLUX.1-schnell |
| **HTML→PNG 렌더링** | Playwright / Puppeteer |
| **웹 스크레이핑** | httpx, BeautifulSoup4, DuckDuckGo |
| **SNS 연동** | instagrapi, instaloader |
| **프론트엔드** | HTML/CSS/JavaScript (web.html) |

## 설치 방법

### 1. 저장소 클론

```bash
git clone https://github.com/your-org/cardflow.git
cd cardflow
```

### 2. Python 패키지 설치

```bash
pip install flask httpx huggingface-hub duckduckgo-search pillow
```

**선택적 패키지:**
```bash
# HTML→PNG 렌더링 (Playwright 권장)
pip install playwright
playwright install chromium

# 또는 Puppeteer 사용
pip install pyppeteer

# SNS 기능
pip install instagrapi instaloader

# 웹 스크레이핑 향상
pip install beautifulsoup4
```

### 3. API 키 설정

#### OpenRouter API 키
1. https://openrouter.ai 에서 가입
2. 대시보드에서 API 키 생성
3. `api_utils.py`의 `OPENROUTER_KEY` 변수에 입력

```python
OPENROUTER_KEY = "sk-or-v1-your-key-here"
```

#### HuggingFace API 토큰
1. https://huggingface.co 에서 가입
2. Settings → Access Tokens에서 생성
3. 환경변수로 설정:

```bash
export HF_TOKEN="hf_your_token_here"
```

또는 `image_generator.py`에 직접 입력:
```python
HF_TOKEN = "hf_your_token_here"
```

### 4. 브랜드 설정

`brand.md` 파일을 편집하여 브랜드 정보 설정:

```markdown
# 브랜드 가이드

## 브랜드 정보
- 브랜드명: 올리디아(Olidia)
- 메인 컬러: #E8862A
- 서브 컬러: #F5F3F0

## 타겟 독자 및 목표
- 내 카드뉴스의 타겟독자: 피부 노화와 주름 개선에 관심있는 30~50대 여성
- 카드뉴스 게시 목표: 브랜드 인지도 향상 및 방문 유도

## 톤앤매너
- 신뢰감 있으면서도 친근하게
- 의학 용어는 쉽게 풀어서 설명

## CTA 문구
올리디아 공식 인스타그램에서 더 많은 정보를 확인하세요
```

## 실행 방법

### 웹 서버 시작

```bash
python3 app.py
```

브라우저에서 열기: http://localhost:8080

### 주요 UI 기능

1. **기본 생성**
   - 주제 입력 → "생성 시작" 클릭
   - 진행 상황 실시간 표시 (5% → 100%)

2. **URL 활용**
   - URL 입력 → "콘텐츠 추출" 옵션 체크
   - 선택: "블로그 이미지도 추출" (이미지 다운로드)
   - 시스템이 URL 내용을 자동 요약 후 기획에 반영

3. **커스텀 이미지**
   - "이미지 업로드" 탭에서 파일 선택
   - 업로드 완료 후 생성 시작
   - 업로드된 이미지가 우선 적용 (AI 생성보다 우선순위 높음)

4. **슬라이드 개수 및 템플릿**
   - 슬라이드 수: 3~10장 (기본 5장)
   - 템플릿: 
     - "mix" (기본): 본문A/B/C 로테이션
     - "A", "B", "C": 특정 템플릿만 사용

5. **결과 다운로드**
   - 개별 슬라이드: 클릭 → PNG 다운로드
   - 전체: "모든 슬라이드 ZIP 다운로드"

## 프로젝트 구조

```
cardflow/
├── app.py                      # Flask 메인 앱 + API 엔드포인트
├── api_utils.py                # OpenRouter LLM 호출
├── editor.py                   # Step 1: 기획안 생성
├── researcher.py               # Step 2: 팩트 리서치 (DuckDuckGo)
├── writer.py                   # Step 3: 최종 텍스트 작성
├── image_generator.py          # Step 4: HuggingFace 이미지 생성
├── renderer.py                 # Step 5: HTML→PNG 렌더링
├── scraper.py                  # URL 스크레이핑 + 이미지 추출
├── crawler.py                  # RSS/웹사이트 크롤링 (보조)
├── brand.md                    # 브랜드 설정 파일
├── templates/
│   ├── web.html               # 웹 인터페이스
│   ├── first_page.html        # 표지 템플릿
│   ├── content_A.html         # 본문A 템플릿
│   ├── content_B.html         # 본문B 템플릿
│   ├── content_C.html         # 본문C 템플릿
│   └── last_page.html         # 마지막 장 템플릿
├── prompts/
│   └── prompts.py             # AI 프롬프트 템플릿
├── output/                     # 생성된 슬라이드 저장 디렉토리
│   ├── session_{id}/          # 개별 세션 폴더
│   ├── slide_*.png            # 최종 PNG 파일
│   └── uploads/               # 업로드된 이미지
├── usage.json                  # 월별 사용량 추적
├── persona.json                # SNS 페르소나 데이터
└── requirements.txt            # Python 의존성 (선택)
```

## 파이프라인 흐름

```
주제 입력
  ↓
[Step 0] 브랜드 로드 + URL 스크레이핑 (선택)
  ↓
[Step 1] Editor: 기획안 생성 (표지/본문/마지막 구조)
  ↓
[Step 2] Researcher: 웹 검색 + 팩트 정리
  ↓
[Step 3] Writer: 최종 텍스트 작성 (슬라이드별)
  ↓
[Step 4] Image Generator: 배경 이미지 병렬 생성 또는 기존 이미지 적용
  ↓
[Step 5] Renderer: HTML 템플릿 + 데이터 → PNG 변환
  ↓
최종 PNG 슬라이드 (다운로드 가능)
```

## API 엔드포인트

| 메서드 | 엔드포인트 | 설명 | 요청 |
|--------|-----------|------|------|
| GET | `/` | 웹 인터페이스 | - |
| POST | `/generate` | 카드뉴스 생성 시작 | `{topic, url?, extract_images?, slide_count?, template_style?, uploaded_images?}` |
| GET | `/status/<job_id>` | 진행 상태 조회 | - |
| GET | `/slide/<job_id>/<index>` | 슬라이드 PNG 서빙 | - |
| GET | `/download/<job_id>/<index>` | 개별 슬라이드 다운로드 | - |
| GET | `/download-all/<job_id>` | 전체 슬라이드 ZIP 다운로드 | - |
| POST | `/upload` | 이미지 업로드 | `FormData: images[]` |
| GET | `/api/usage` | 월별 사용량 | - |
| POST | `/api/sns/instagram/connect` | Instagram 계정 연결 | `{username, password}` |
| POST | `/api/sns/instagram/analyze` | 페르소나 자동분석 | - |
| GET | `/api/persona` | 현재 페르소나 데이터 | - |
| POST | `/api/persona/save` | 페르소나 저장 | `{JSON 페르소나 데이터}` |
| POST | `/api/settings/save` | 브랜드 설정 저장 | `{brand_name, main_color, sub_color, target_audience, ...}` |

### 생성 요청 예시

```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "콜라겐 재생 필러의 효과",
    "url": "",
    "extract_images": false,
    "slide_count": 5,
    "template_style": "mix",
    "uploaded_images": []
  }'

# 응답: {"job_id": "abc12345def"}
```

### 상태 조회

```bash
curl http://localhost:8080/status/abc12345def

# 응답 예시:
# {
#   "status": "running",
#   "progress": 45,
#   "message": "팩트 리서치 중...",
#   "slides": []
# }
```

## 설정 및 커스터마이징

### 1. 브랜드 설정 (brand.md)

브랜드명, 컬러, 타겟 독자, CTA 문구 등을 편집하면 생성되는 모든 슬라이드에 자동 적용됩니다.

```bash
# 웹 UI에서도 설정 가능 (Settings 탭)
```

### 2. AI 프롬프트 커스터마이징

`prompts/prompts.py` 파일에서 EDITOR_PROMPT, WRITER_PROMPT 등을 수정하여 생성 스타일 조정:

```python
EDITOR_PROMPT = """당신은 올리디아(Olidia) 브랜드의 인스타그램 카드뉴스 편집장입니다.
...
"""
```

### 3. HTML 템플릿 수정

`templates/` 폴더의 HTML 파일들을 편집하여 디자인 변경:

- **first_page.html**: 표지 슬라이드 (훅 메시지, 배경 이미지)
- **content_A.html, B.html, C.html**: 본문 3가지 레이아웃
- **last_page.html**: 마지막 CTA 슬라이드 (체크리스트)

**템플릿 변수:**
```html
<!-- 모든 슬라이드 -->
{{main_color}}     <!-- 브랜드 메인 색상 -->
{{sub_color}}      <!-- 브랜드 서브 색상 -->
{{brand_name}}     <!-- 브랜드명 -->
{{image_path}}     <!-- 배경 이미지 절대 경로 -->
{{heading}}        <!-- 슬라이드 제목 -->
{{body}}           <!-- 슬라이드 본문 -->

<!-- 본문 슬라이드만 -->
{{category_tag}}   <!-- 포인트 태그 (e.g. "Point 01") -->

<!-- 마지막 슬라이드만 -->
{{cta_text}}       <!-- CTA 문구 -->
{{checklist_html}} <!-- 체크리스트 HTML -->
```

### 4. 이미지 생성 모델 변경

`image_generator.py`에서 HF_MODEL 변수 수정:

```python
# 현재
HF_MODEL = "black-forest-labs/FLUX.1-schnell"

# 대안 (더 품질 높음, 시간 걸림)
HF_MODEL = "black-forest-labs/FLUX.1-dev"

# 대안 (더 빠름, 품질 낮음)
HF_MODEL = "stabilityai/stable-diffusion-3-medium"
```

### 5. 렌더링 엔진 선택

`renderer.py`에서 사용할 브라우저 선택:

```python
# Playwright (권장, 더 안정적)
from playwright.sync_api import sync_playwright

# Pyppeteer (Puppeteer Python 포트)
import pyppeteer
```

## 사용 예시

### 1. 기본: 주제로 생성

```
주제: "콜라겐 필러의 원리"
슬라이드 수: 5
템플릿: mix
→ 5장 완성 카드뉴스 자동 생성
```

### 2. URL 활용: 블로그 글을 기반으로 생성

```
URL: https://example.com/my-blog-post
추출 옵션: 콘텐츠 추출 + 이미지 추출
→ 블로그 글 요약 + 블로그 이미지 활용 카드뉴스 생성
```

### 3. 이미지 업로드: 기존 이미지로 생성

```
이미지 파일: [image1.jpg, image2.jpg, image3.jpg, image4.jpg, image5.jpg]
주제: "안티에이징 트렌드"
→ 업로드한 이미지 + AI 생성 텍스트로 슬라이드 완성
```

## 트러블슈팅

### 1. "모든 무료 모델 호출 실패"

**원인**: OpenRouter API 키 만료 또는 무료 할당량 초과

**해결**:
- API 키 재확인 (`api_utils.py`의 OPENROUTER_KEY)
- OpenRouter 대시보드에서 할당량 확인
- 프록시 또는 다른 LLM API로 변경

### 2. PNG 렌더링 실패

**원인**: Playwright/Pyppeteer 미설치 또는 브라우저 없음

**해결**:
```bash
pip install playwright
playwright install chromium
```

### 3. HuggingFace 토큰 에러

**원인**: HF_TOKEN 없음 또는 토큰 만료

**해결**:
```bash
export HF_TOKEN="your-token-here"
# 또는 image_generator.py에 직접 입력
```

### 4. 이미지 생성이 느림

**원인**: FLUX.1-schnell 모델은 병렬 처리되지만 서버 부하 또는 네트워크 느림

**해결**:
- 슬라이드 개수 줄이기 (기본 5 → 3)
- 더 빠른 모델로 변경 (`stable-diffusion-3-medium`)
- 기존 이미지 업로드로 AI 생성 스킵

### 5. 템플릿 변수가 반영 안 됨

**원인**: HTML 템플릿에서 변수 문법 오류

**확인**:
- 정확한 문법: `{{variable_name}}` (정확히 2개의 중괄호)
- 변수명 대소문자 일치
- renderer.py의 fill_template() 함수 확인

## 환경 변수

주요 환경 변수:

```bash
# HuggingFace API 토큰 (이미지 생성)
export HF_TOKEN="hf_..."

# OpenRouter API 키 (텍스트 생성)
# api_utils.py에 하드코딩 또는 환경변수로 설정
export OPENROUTER_KEY="sk-or-v1-..."

# Flask 디버그 모드
export FLASK_ENV=development
export FLASK_DEBUG=1

# 포트 변경 (기본 8080)
export FLASK_PORT=5000
```

## 라이선스

MIT License

이 프로젝트의 오픈소스 라이센스를 준수하세요.

- Flask: BSD 3-Clause
- Playwright: Apache 2.0
- HuggingFace: Apache 2.0
- httpx: BSD 3-Clause

## 기여 및 피드백

버그 리포트, 기능 요청, 개선사항은 GitHub Issues에서 받습니다.

---

**최종 수정**: 2026년 4월

CardFlow 플랫폼에 대한 질문이나 기술 지원이 필요하면 프로젝트 저장소를 참고하세요.
