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


def _generate_single(args):
    """단일 이미지 생성 (스레드용)"""
    i, slide, output_dir = args
    image_path = os.path.join(output_dir, f"slide_{i}_bg.png")
    image_prompt = slide.get("image_prompt", "A clean minimal beauty background with soft lighting")

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
