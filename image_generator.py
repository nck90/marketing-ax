"""Step 6: Image Generator - HuggingFace 병렬 이미지 생성"""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from huggingface_hub import InferenceClient

HF_TOKEN = os.environ.get("HF_TOKEN", "")
HF_MODEL = "black-forest-labs/FLUX.1-schnell"


QUALITY_SUFFIX = ", photorealistic, 8k, sharp focus, professional photography, warm golden lighting, 5500K color temperature, no text, no watermark, no logo"

SLIDE_FALLBACKS = {
    "cover": [
        "3D rendered translucent orange and gold molecular structures floating on warm cream background, octane render, luxury cosmetic product aesthetic, studio lighting",
        "Elegant glass medical vial with orange cap surrounded by floating golden bubbles, 3D render, cinema4d, premium beauty product visualization, beige background",
        "Abstract 3D orange and amber crystal spheres connected by golden threads on light background, octane render, premium cosmetic feel",
    ],
    "content": [
        "Close-up of Korean woman with luminous dewy skin touching her cheek, soft warm studio lighting, Canon EOS R5, beauty photography, golden hour",
        "Macro shot of golden collagen serum droplets on white marble, luxury cosmetic texture, 3D render, warm studio lighting, product photography",
        "Cross-section diagram of healthy glowing skin layers with visible collagen fibers, warm tones, medical illustration, clean white background, 3D render",
        "Elegant skincare treatment scene with golden light, clean modern clinic aesthetic, warm tones, professional photography",
        "Abstract flowing golden liquid silk texture on warm cream background, luxury cosmetic feel, macro photography, studio lighting",
        "Side profile of woman with perfect skin contour, soft rim lighting, beauty photography, warm golden tones, Canon EOS R5",
    ],
    "last": [
        "Soft warm orange to peach gradient with gentle golden bokeh particles, dreamy atmosphere, abstract beauty background",
        "Blurred glass vial silhouette on warm golden gradient background with soft light particles, premium cosmetic aesthetic",
        "Abstract warm amber and cream watercolor wash background with subtle golden sparkles, clean minimal luxury feel",
    ],
}


def _enhance_prompt(slide, index):
    """이미지 프롬프트 품질 강제 보강"""
    import random
    raw = slide.get("image_prompt", "").strip()
    slide_type = slide.get("slide_type", "content")

    # 프롬프트가 없거나 너무 짧으면 폴백 사용
    if not raw or len(raw) < 20 or raw == "placeholder":
        fallbacks = SLIDE_FALLBACKS.get(slide_type, SLIDE_FALLBACKS["content"])
        raw = random.choice(fallbacks)

    # 이미 충분히 상세하면 품질 접미사만 추가
    if len(raw) > 100:
        if "no text" not in raw.lower():
            raw += ", no text, no watermark"
        return raw

    # 짧은 프롬프트면 품질 키워드 보강
    return raw + QUALITY_SUFFIX


def _generate_single(args):
    """단일 이미지 생성 (스레드용)"""
    i, slide, output_dir = args
    image_path = os.path.join(output_dir, f"slide_{i}_bg.png")
    image_prompt = _enhance_prompt(slide, i)

    try:
        hf_client = InferenceClient(token=HF_TOKEN)
        image = hf_client.text_to_image(image_prompt, model=HF_MODEL)
        image = image.resize((1080, 1350))
        image.save(image_path)
        print(f"  [Image Gen] 슬라이드 {i} 완료")
        return i, image_path
    except Exception as e:
        print(f"  [Image Gen] 슬라이드 {i} 에러: {e}")
        _create_placeholder(image_path, i)
        return i, image_path


def run(slides, output_dir="output", api_client=None):
    """슬라이드별 이미지 병렬 생성"""
    os.makedirs(output_dir, exist_ok=True)

    print(f"  [Image Gen] {len(slides)}장 병렬 생성 시작...")
    tasks = [(i, slide, output_dir) for i, slide in enumerate(slides)]

    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(_generate_single, t): t[0] for t in tasks}
        for future in as_completed(futures):
            idx, path = future.result()
            results[idx] = path

    # 순서대로 정렬
    image_paths = [results[i] for i in range(len(slides))]
    print(f"[Image Gen] {len(image_paths)}개 이미지 생성 완료")
    return image_paths


def _create_placeholder(path, index):
    """플레이스홀더"""
    try:
        from PIL import Image
        img = Image.new("RGB", (1080, 1350), "#f5f3f0")
        img.save(path)
    except ImportError:
        import struct, zlib
        w, h = 1080, 1350
        raw = b""
        for _ in range(h):
            raw += b"\x00" + bytes([245, 243, 240]) * w
        comp = zlib.compress(raw)
        def chunk(t, d):
            c = t + d
            crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
            return struct.pack(">I", len(d)) + c + crc
        data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", comp) + chunk(b"IEND", b"")
        with open(path, "wb") as f:
            f.write(data)
