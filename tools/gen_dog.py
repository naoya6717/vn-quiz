"""Gemini の画像生成でトイプードル「もこ」の成長段階画像を作る。
使い方: tools/.venv/bin/python tools/gen_dog.py [--models] [stage1 stage1_happy ...]
.env の GEMINI_API_KEY を使う。出力: app/data/dog/<name>.png（背景透過）
キャラの一貫性のため、stage1 を最初に作り、以降は stage1 を参照画像として渡す。
"""
import base64, io, json, os, sys, urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "data" / "dog"
RAW = ROOT / "private" / "dog_raw"
API = "https://generativelanguage.googleapis.com/v1beta"


def key():
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("GEMINI_API_KEY not set in vn-quiz/.env")


K = key()
MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

BASE = ("A cute 3D-rendered character in a soft, high-quality animated-film style: a toy poodle named Moko with fluffy curly apricot "
        "(light caramel) fur, big round shiny dark eyes, small black nose, rosy cheeks, friendly expression. Full body, front-facing, "
        "centered, standing on nothing, soft studio lighting, no text, no logo, no shadow on the ground. "
        "Background: perfectly flat solid pure green (#00FF00) chroma-key color filling the entire background.")
STAGES = {
    "stage1": "Stage: tiny puppy, very small and round, oversized head, sitting, innocent look.",
    "stage2": "Stage: young playful dog, a bit bigger than a puppy, energetic pose with one paw raised.",
    "stage3": "Stage: hard-working student dog, sitting upright, wearing a small light-blue scarf, determined but kind smile.",
    "stage4": "Stage: mature, elegant adult toy poodle with a well-groomed fluffy coat, confident gentle smile, sitting proudly.",
    "stage5": "Stage: legendary champion toy poodle with a tiny golden star badge on a red ribbon collar, subtle sparkles around, majestic happy pose.",
}
HAPPY = " Expression: overjoyed — eyes happily closed in crescent shapes, mouth open in a big smile, jumping slightly with front paws up, small pink hearts floating nearby."


def call(model, parts):
    body = {"contents": [{"parts": parts}], "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}}
    req = urllib.request.Request(f"{API}/models/{model}:generateContent?key={K}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.load(r)
    for c in d.get("candidates", []):
        for p in c.get("content", {}).get("parts", []):
            if "inlineData" in p:
                return base64.b64decode(p["inlineData"]["data"])
    raise RuntimeError(json.dumps(d)[:500])


def chroma(png: bytes) -> Image.Image:
    """背景色を画像の外周から推定し、その色からの距離で透明度を決める（くすんだ緑でも抜ける）。"""
    im = Image.open(io.BytesIO(png)).convert("RGB")
    a = np.array(im).astype(np.float32)
    border = np.concatenate([a[:8].reshape(-1, 3), a[-8:].reshape(-1, 3), a[:, :8].reshape(-1, 3), a[:, -8:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    dist = np.sqrt(((a - bg) ** 2).sum(axis=2))
    alpha = np.clip((dist - 40) / (110 - 40), 0, 1)  # 40未満は完全透明、110以上は不透明
    # 縁の緑かぶりを抑える：半透明部分の緑を赤・青の大きい方まで下げる
    g_excess = a[..., 1] - np.maximum(a[..., 0], a[..., 2])
    edge = (alpha < 1) & (g_excess > 0)
    a[..., 1] = np.where(edge, np.maximum(a[..., 0], a[..., 2]), a[..., 1])
    rgba = np.dstack([a, alpha * 255]).astype(np.uint8)
    out = Image.fromarray(rgba)
    bbox = out.getbbox()
    out = out.crop(bbox)
    side = max(out.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(out, ((side - out.width) // 2, side - out.height))
    return canvas.resize((640, 640), Image.LANCZOS)


def main():
    args = sys.argv[1:]
    if args[:1] == ["--models"]:
        with urllib.request.urlopen(f"{API}/models?key={K}&pageSize=200") as r:
            for m in json.load(r)["models"]:
                if "image" in m["name"]:
                    print(m["name"], m.get("supportedGenerationMethods"))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    names = args or [f"{s}{h}" for s in STAGES for h in ("", "_happy")]
    ref = RAW / "stage1.png"
    for name in names:
        stage = name.replace("_happy", "")
        prompt = BASE + " " + STAGES[stage] + (HAPPY if name.endswith("_happy") else "")
        parts = [{"text": prompt}]
        if ref.exists() and name != "stage1":
            parts = [{"text": "This is the reference character Moko. Keep exactly the same character design, fur color, face and art style. " + prompt},
                     {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(ref.read_bytes()).decode()}}]
        png = call(MODEL, parts)
        (RAW / f"{name}.png").write_bytes(png)
        chroma(png).save(OUT / f"{name}.png", optimize=True)
        print("ok", name)


if __name__ == "__main__":
    main()
