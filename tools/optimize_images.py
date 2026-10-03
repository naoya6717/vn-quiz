"""アプリ用の画像を軽量化する：app/data/dog と app/data/items の PNG を縮小して WebP（透過あり）に変換する。
使い方: tools/.venv/bin/python tools/optimize_images.py
元のPNGは削除する（生成元の画像は private/ に残っている）。
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
TARGETS = {"dog": 480, "items": 320}  # 表示サイズの約2倍（高解像度画面向け）

for folder, size in TARGETS.items():
    for png in sorted((ROOT / "app" / "data" / folder).rglob("*.png")):
        im = Image.open(png).convert("RGBA")
        im.thumbnail((size, size), Image.LANCZOS)
        out = png.with_suffix(".webp")
        im.save(out, "WEBP", quality=82, method=6)
        png.unlink()
        print(f"{out.relative_to(ROOT)} {out.stat().st_size // 1024}KB")
