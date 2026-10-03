"""Gemini の画像生成でトイプードル「もこ」の成長段階画像を作る。
使い方: tools/.venv/bin/python tools/gen_dog.py [--models] [--breed=poodle|shiba|pome|dachs] [stage1 stage1_happy ...]
.env の GEMINI_API_KEY を使う。出力: app/data/dog/<breed>/<name>.png（背景透過）→ 生成後に tools/optimize_images.py で WebP 化する
キャラの一貫性のため、stage1 を最初に作り、以降は stage1 を参照画像として渡す。
"""
import base64, io, json, os, sys, urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

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

BREEDS = {
    "poodle": "a toy poodle with fluffy curly apricot (light caramel) fur",
    "shiba": "a Shiba Inu with red-sesame (orange-tan) fur, cream white cheeks, chest and belly, upright triangular ears and a curled tail",
    "pome": "a Pomeranian with very fluffy cream-orange double coat, a big fluffy mane around the neck, small upright ears and a plume tail",
    "dachs": "a miniature dachshund with smooth chocolate-and-tan short coat, long body, short legs and long floppy ears",
}
BREED = "poodle"


def base():
    return ("A cute 3D-rendered character in a soft, high-quality animated-film style: " + BREEDS[BREED] +
            ", big round shiny dark eyes, small black nose, rosy cheeks, friendly expression. Full body, front-facing, "
            "centered, standing on nothing, soft studio lighting, no text, no logo, no shadow on the ground. "
            "Background: perfectly flat solid pure green (#00FF00) chroma-key color filling the entire background.")
STAGES = {
    "stage1": "Stage: tiny puppy, very small and round, oversized head, sitting, innocent look.",
    "stage2": "Stage: young playful dog, a bit bigger than a puppy, energetic pose with one paw raised.",
    "stage3": "Stage: hard-working student dog, sitting upright, wearing a small light-blue scarf, determined but kind smile.",
    "stage4": "Stage: mature, elegant grown-up version of the same dog (same breed, same coat color), well-groomed coat, confident gentle smile, sitting proudly. Only one dog in the image.",
    "stage5": "Stage: legendary champion version of the same dog (same breed, same coat color) wearing a tiny golden star badge on a red ribbon collar, subtle sparkles around, majestic happy pose. Only one dog in the image.",
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


def chroma(png: bytes, flood: bool = False) -> Image.Image:
    """背景色を画像の外周から推定して透過する。
    flood=True: 外周とつながった背景色の領域だけを透明にし、物の内側は色に関係なく不透明にする
    （淡いパステル色の物が半透明になるのを防ぐ。アイテム画像用）。"""
    im = Image.open(io.BytesIO(png)).convert("RGB")
    a = np.array(im).astype(np.float32)
    border = np.concatenate([a[:8].reshape(-1, 3), a[-8:].reshape(-1, 3), a[:, :8].reshape(-1, 3), a[:, -8:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    dist = np.sqrt(((a - bg) ** 2).sum(axis=2))
    if flood:
        from scipy import ndimage
        # 背景色に近い色、または背景と同じ色味の影（緑背景なら緑っぽい影）を背景候補にする
        r_, g_, b_ = a[..., 0], a[..., 1], a[..., 2]
        if bg[1] > max(bg[0], bg[2]):
            tint = (g_ - np.maximum(r_, b_)) > 10
        else:
            tint = (np.minimum(r_, b_) - g_) > 25
        darker = a.mean(axis=2) < bg.mean() + 15  # 影は背景と同じか暗い。明るいミント色などは物の色として残す
        near = (dist < 38) | (tint & darker & (dist < 95))
        lab, _ = ndimage.label(near)
        edge_labels = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
        bgmask = np.isin(lab, edge_labels[edge_labels > 0])
        bgmask = ndimage.binary_opening(bgmask, iterations=1)
        obj = ~bgmask
        # 本体から離れた小さな点（ゴミ）を取り除く：最大の塊の2%未満の塊は背景にする
        olab, n = ndimage.label(obj)
        if n > 1:
            sizes = ndimage.sum(obj, olab, range(1, n + 1))
            keep = np.isin(olab, np.where(sizes >= sizes.max() * 0.02)[0] + 1)
            obj = keep
        obj = ndimage.binary_fill_holes(obj)
        alpha = obj.astype(np.float32)
        alpha = np.array(Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))) / 255.0
    else:
        alpha = np.clip((dist - 40) / (110 - 40), 0, 1)  # 40未満は完全透明、110以上は不透明
    # 縁の色かぶりを抑える：半透明部分で背景色の成分が強いときだけ（緑背景＝緑、マゼンタ背景＝赤青）
    if bg[1] > max(bg[0], bg[2]):
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
    global BREED
    if args[:1] and args[0].startswith("--breed="):
        BREED = args.pop(0).split("=", 1)[1]
    out, raw = OUT / BREED, RAW / BREED
    out.mkdir(parents=True, exist_ok=True)
    raw.mkdir(parents=True, exist_ok=True)
    names = args or [f"{s}{h}" for s in STAGES for h in ("", "_happy")]
    ref = raw / "stage1.png"
    for name in names:
        stage = name.replace("_happy", "")
        prompt = base() + " " + STAGES[stage] + (HAPPY if name.endswith("_happy") else "")
        parts = [{"text": prompt}]
        if ref.exists() and name != "stage1":
            parts = [{"text": "This is the reference character Moko. Keep exactly the same character design, fur color, face and art style. " + prompt},
                     {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(ref.read_bytes()).decode()}}]
        for attempt in range(3):
            try:
                png = call(MODEL, parts)
                break
            except Exception as err:  # 一時的な失敗は再試行
                print("retry", name, err)
        (raw / f"{name}.png").write_bytes(png)
        chroma(png).save(out / f"{name}.png", optimize=True)
        print("ok", name)


if __name__ == "__main__":
    main()
