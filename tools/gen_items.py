"""部屋に飾るアイテム・食べ物の画像を Gemini で作る（犬と同じ3D風の画風、背景透過）。
使い方: tools/.venv/bin/python tools/gen_items.py [id ...]
出力: app/data/items/<id>.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_dog  # noqa: E402  （API呼び出しと背景透過の処理を共用）

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "data" / "items"
RAW = ROOT / "private" / "items_raw"

STYLE = ("A single cute 3D-rendered game item in a soft, high-quality animated-film style, pastel colors, soft studio lighting, "
         "front view, centered, whole object visible, no text, no logo, no people, no animals, no shadow on the ground. "
         "Background: perfectly flat solid pure green (#00FF00) chroma-key color filling the entire background. The object: ")
ITEMS = {
    "boro": "a small pastel bowl filled with tiny round egg biscuit treats (tamago boro) for dogs",
    "jerky": "a few sticks of chicken jerky dog treats tied with a little ribbon",
    "cake": "a small round celebration cake for dogs with whipped cream and a strawberry, one candle",
    "bowl": "a set of two cute ceramic pet bowls side by side, one with kibble and one with water, pink and mint colors",
    "ball": "a bright yellow-green tennis ball",
    "cushion": "a round fluffy pink pet cushion bed, low and soft",
    "plant": "a potted monstera houseplant in a white ceramic pot",
    "clock": "a round wall clock with a cute pastel frame, front view",
    "shelf": "a small wooden bookshelf with colorful study books and a tiny pencil cup, front view",
    "bed": "a luxurious canopy pet bed with a soft cream mattress and pastel pink fabric canopy, front view",
    "chandelier": "a sparkling golden crystal chandelier hanging from a short chain, front view",
    "trophy": "a shiny golden trophy cup on a wooden base decorated with a red ribbon and cherry blossoms",
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    for iid in sys.argv[1:] or list(ITEMS):
        for attempt in range(3):
            try:
                png = gen_dog.call(gen_dog.MODEL, [{"text": STYLE + ITEMS[iid]}])
                break
            except Exception as err:
                print("retry", iid, str(err)[:120])
        (RAW / f"{iid}.png").write_bytes(png)
        gen_dog.chroma(png).save(OUT / f"{iid}.png", optimize=True)
        print("ok", iid)


if __name__ == "__main__":
    main()
