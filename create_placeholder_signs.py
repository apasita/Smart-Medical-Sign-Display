"""
create_placeholder_signs.py  — v2
===================================
สร้าง placeholder video สำหรับทุกคำใน sign_data.py (314 คำ)
ใช้แทนคลิปจริงระหว่างที่ยังไม่ได้อัดคลิปภาษามือ

Requirements:
  pip install opencv-python pillow numpy

Usage:
  python create_placeholder_signs.py
  python create_placeholder_signs.py --missing-only   # สร้างแค่ที่ยังไม่มี
  python create_placeholder_signs.py --force           # สร้างใหม่ทั้งหมด
"""

import os, sys, math, argparse
from pathlib import Path

try:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# ─── Import from sign_data.py (single source of truth) ────────────────────────
try:
    from sign_data import SIGN_DICT
except ImportError:
    print("❌ ไม่พบ sign_data.py — ต้องอยู่ในโฟลเดอร์เดียวกัน")
    sys.exit(1)

SIGNS_DIR = Path(__file__).parent / "signs"
SIGNS_DIR.mkdir(exist_ok=True)

W, H   = 480, 480
FPS    = 24
SECS   = 2

# ─── Font paths (Windows / Mac / Linux) ───────────────────────────────────────
FONT_CANDIDATES = [
    # Windows
    r"C:\Windows\Fonts\THSarabunNew.ttf",
    r"C:\Windows\Fonts\THSarabunNew Bold.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\ArialUni.ttf",
    # Mac
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    # Linux
    "/usr/share/fonts/truetype/thai/Garuda.ttf",
    "/usr/share/fonts/truetype/tlwg/Garuda.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

def _load_font(size: int):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def make_frame(word: str, emoji: str, color_rgb: tuple, t: float, total: float) -> np.ndarray:
    img  = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    r, g, b = color_rgb

    # Pulsing circle
    pulse  = 0.85 + 0.15 * math.sin(t * math.pi * 3)
    radius = int(150 * pulse)
    cx, cy = W // 2, H // 2 - 30

    # Shadow
    draw.ellipse([cx-radius-4, cy-radius-4, cx+radius+4, cy+radius+4], fill=(210,210,210))
    # Main circle
    draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill=(r, g, b))
    # Inner white
    ir = int(radius * 0.6)
    draw.ellipse([cx-ir, cy-ir, cx+ir, cy+ir], fill=(255,255,255))

    font_word = _load_font(56)
    font_sub  = _load_font(26)

    # Word label
    try:
        bb = draw.textbbox((0,0), word, font=font_word)
        tw, th = bb[2]-bb[0], bb[3]-bb[1]
        draw.text((W//2 - tw//2, cy + radius + 14), word, font=font_word, fill=(30,30,30))
    except Exception:
        pass

    # Category color bar at top
    draw.rectangle([0, 0, W, 10], fill=(r, g, b))

    # Subtitle
    sub = "ภาษามือไทย"
    try:
        bb2 = draw.textbbox((0,0), sub, font=font_sub)
        sw = bb2[2]-bb2[0]
        draw.text((W//2 - sw//2, H - 48), sub, font=font_sub, fill=(160,160,160))
    except Exception:
        pass

    # Progress bar
    progress = t / total
    draw.rectangle([0, H-7, W, H], fill=(220,220,220))
    draw.rectangle([0, H-7, int(W*progress), H], fill=(r, g, b))

    return np.array(img)


def create_video(out_path: Path, word: str, emoji: str, color_hex: str):
    color_rgb = hex_to_rgb(color_hex)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, FPS, (W, H))
    for i in range(FPS * SECS):
        t = i / FPS
        frame = make_frame(word, emoji, color_rgb, t, SECS)
        writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    writer.release()


def main():
    parser = argparse.ArgumentParser(description="สร้าง placeholder videos")
    parser.add_argument("--missing-only", action="store_true",
                        help="สร้างแค่ไฟล์ที่ยังไม่มี (default)")
    parser.add_argument("--force", action="store_true",
                        help="สร้างใหม่ทั้งหมดแม้จะมีอยู่แล้ว")
    args = parser.parse_args()

    if not CV2_AVAILABLE:
        print("❌ กรุณาติดตั้ง: pip install opencv-python pillow numpy")
        sys.exit(1)

    total = len(SIGN_DICT)
    print(f"📋 พจนานุกรม: {total} คำ")
    print(f"📁 บันทึกที่: {SIGNS_DIR.resolve()}\n")

    ok = skip = fail = 0
    for i, (thai_word, info) in enumerate(SIGN_DICT.items()):
        out = SIGNS_DIR / info["video"]

        # skip if exists (unless --force)
        if out.exists() and not args.force:
            skip += 1
            continue

        try:
            create_video(out, thai_word, info["emoji"], info["color"])
            ok += 1
            status = "🎬" if ok % 10 == 0 else "✅"
            print(f"  [{i+1:03d}/{total}] {status} {info['video']:35s} [{thai_word}]")
        except Exception as e:
            fail += 1
            print(f"  [{i+1:03d}/{total}] ❌ {info['video']:35s} → {e}")

    print(f"\n{'='*55}")
    print(f"  สร้างใหม่  : {ok:3d} ไฟล์")
    print(f"  มีอยู่แล้ว : {skip:3d} ไฟล์")
    print(f"  ล้มเหลว   : {fail:3d} ไฟล์")
    print(f"  รวม        : {ok+skip:3d} / {total} ไฟล์")
    print(f"{'='*55}")

    if fail == 0:
        print("\n✅ เสร็จสมบูรณ์! รัน app ได้เลย:")
    else:
        print(f"\n⚠️  มี {fail} ไฟล์ที่ล้มเหลว ลองรันใหม่อีกครั้ง")
    print("  streamlit run app.py")


if __name__ == "__main__":
    main()