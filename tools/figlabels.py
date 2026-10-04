"""図（JPG）の中のラベル文字の位置を自動検出して、番号つきの確認画像を作る（図で覚えるコーナーの下準備）。
使い方: tools/.venv/bin/python tools/figlabels.py <画像>  → private/figs/_boxes_<名前>.png と 座標一覧を表示
"""
import sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage


def boxes(path):
    im = np.asarray(Image.open(path).convert("L"))
    dark = im < 140
    lab, n = ndimage.label(dark)
    sl = ndimage.find_objects(lab)
    glyph = np.zeros_like(dark)
    for i, s in enumerate(sl):
        h, w = s[0].stop - s[0].start, s[1].stop - s[1].start
        if 3 <= h <= 16 and w <= 18:  # 文字くらいの大きさの塊だけ
            glyph[s][lab[s] == i + 1] = True
    # 横に近い文字をつなげて単語・行にする
    merged = ndimage.binary_dilation(glyph, structure=np.ones((3, 9)))
    lab2, n2 = ndimage.label(merged)
    out = []
    for s in ndimage.find_objects(lab2):
        y0, y1, x0, x1 = s[0].start, s[0].stop, s[1].start, s[1].stop
        if (x1 - x0) >= 14 and (y1 - y0) <= 24 and glyph[s].sum() > 25:
            out.append([x0, y0, x1, y1])
    return sorted(out, key=lambda b: (b[1], b[0]))


if __name__ == "__main__":
    p = sys.argv[1]
    bs = boxes(p)
    im = Image.open(p).convert("RGB")
    d = ImageDraw.Draw(im)
    for i, b in enumerate(bs):
        d.rectangle(b, outline=(255, 0, 0))
        d.text((b[0], b[1] - 10), str(i), fill=(0, 0, 255))
        print(i, b)
    im.save("private/figs/_boxes_" + p.rsplit("/", 1)[-1].rsplit(".", 1)[0] + ".png")
