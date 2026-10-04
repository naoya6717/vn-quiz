"""「図で覚える」コーナーの図と問題データを作る。
- 図は Wikimedia Commons の自由ライセンス図（教科書の図）を使い、図の作者が付けた英語ラベルを白で消して番号に置き換える。
  → 正答は「図の作者が付けたラベル」そのもの。日本語名は過去問の公式表記に合わせ、出典で照合済み。
- 問題の元データ: private/figs/fig_questions.json（evidence＝出典の原文の抜き出し。tools/check_evidence.py で照合）
使い方: tools/.venv/bin/python tools/build_figs.py
出力: app/data/figs/<図id>.webp と app/data/figs.json（evidence は除く）
"""
import json
import random
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "private" / "figs"
OUT = ROOT / "app" / "data" / "figs"
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
JFONT = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
PINK = (226, 69, 127)

# rect = 元画像での英語ラベルの位置（x0, y0, x1, y1）。en = 図の原ラベル、ja = 日本語名
FIGS = {
    "brain": {
        "file": "Anatomy_and_physiology_of_animals_Longitudinal_section_through_brain_of_a_dog.jpg",
        "name": "犬の脳（正中断面）", "crop": (0, 228, 623, 563),
        "labels": [
            ("cerebral cortex", "大脳皮質", (0, 307, 86, 321)),
            ("cerebrum", "大脳", (271, 327, 355, 345)),
            ("nerve fibres joining right and left cerebral hemispheres", "脳梁（左右の大脳半球をつなぐ神経線維）", (488, 316, 614, 362)),
            ("3rd ventricle", "第三脳室", (532, 387, 609, 401)),
            ("cerebellum", "小脳", (18, 407, 88, 421)),
            ("spinal cord", "脊髄", (18, 467, 87, 484)),
            ("thalamus", "視床", (375, 478, 441, 495)),
            ("hypothalamus", "視床下部", (375, 510, 462, 527)),
            ("pons", "橋", (249, 522, 286, 536)),
            ("medulla oblongata", "延髄", (146, 540, 257, 557)),
            ("pituitary gland", "下垂体", (275, 540, 362, 557)),
        ],
    },
    "eye": {
        "file": "Anatomy_and_physiology_of_animals_Structure_of_the_eye.jpg", "name": "眼球の構造（模式図）",
        "labels": [
            ("conjunctiva", "結膜", (211, 2, 283, 18)),
            ("retina", "網膜", (412, 2, 453, 15)),
            ("choroid", "脈絡膜", (464, 1, 514, 15)),
            ("cornea", "角膜", (102, 43, 151, 56)),
            ("sclera", "強膜", (585, 96, 627, 110)),
            ("iris", "虹彩", (126, 99, 151, 110)),
            ("fovea", "中心窩", (584, 149, 624, 163)),
            ("pupil", "瞳孔", (116, 163, 151, 180)),
            ("lens", "水晶体", (119, 222, 151, 236)),
            ("optic nerve", "視神経", (586, 240, 656, 256)),
            ("anterior chamber", "前眼房", (47, 280, 157, 294)),
            ("blind spot", "盲点", (399, 345, 462, 362)),
            ("suspensory ligament", "毛様小帯（チン小帯）", (293, 349, 368, 378)),
        ],
    },
    "ear": {
        "file": "Anatomy_and_physiology_of_animals_The_ear.jpg", "name": "耳の構造（模式図）",
        "labels": [
            ("vestibular organ (semicircular canals and otolith organs)", "前庭器官（半規管と耳石器）", (418, 8, 540, 57)),
            ("ear ossicles tiny bones", "耳小骨", (322, 25, 400, 54)),
            ("ear drum", "鼓膜", (254, 48, 313, 62)),
            ("ear pinna", "耳介", (16, 49, 78, 63)),
            ("cochlea", "蝸牛", (530, 85, 582, 99)),
            ("auditory nerve", "聴神経", (507, 255, 596, 270)),
            ("Eustachian tube", "耳管", (278, 261, 376, 275), "R"),
            ("ear canal", "外耳道", (161, 276, 222, 290)),
        ],
        # 区分の英語キャプションは日本語に置き換える（番号は付けない）
        "captions": [("外耳", (216, 333, 276, 346)), ("中耳", (347, 321, 415, 340)), ("内耳", (467, 329, 526, 340))],
    },
    "kidney": {
        "file": "Anatomy_and_physiology_of_animals_Dissected_kidney.jpg", "name": "腎臓の断面（模式図）",
        "labels": [
            ("renal pelvis", "腎盂", (20, 7, 104, 25)),
            ("cortex", "皮質", (507, 35, 556, 49)),
            ("medulla", "髄質", (507, 83, 568, 98)),
            ("renal artery", "腎動脈", (20, 136, 104, 153)),
            ("pyramids", "腎錐体", (507, 151, 576, 169)),
            ("renal vein", "腎静脈", (31, 173, 104, 188)),
            ("fibrous capsule", "線維被膜", (507, 240, 617, 258)),
            ("ureter", "尿管", (56, 299, 105, 313)),
        ],
    },
    "liver": {
        "file": "Anatomy_and_physiology_of_animals_Liver,_gall_bladder_&_pancreas.jpg", "name": "肝臓・胆嚢・膵臓（模式図）",
        "labels": [
            ("diaphragm", "横隔膜", (509, 19, 588, 38)),
            ("bile ducts transporting bile to gall bladder", "胆管（胆汁を胆嚢へ運ぶ）", (509, 71, 643, 105)),
            ("liver", "肝臓", (95, 80, 129, 96)),
            ("gall bladder (under lobe of liver)", "胆嚢", (7, 130, 130, 164)),
            ("pancreas", "膵臓", (511, 160, 573, 176)),
            ("bile duct", "胆管", (450, 208, 508, 224)),
            ("small intestine (duodenum)", "小腸（十二指腸）", (37, 231, 127, 264)),
        ],
    },
    "heart": {
        "file": "Anatomy_and_physiology_of_animals_heart_showing_Coronary_vessels.jpg", "name": "心臓の外観（模式図）",
        "labels": [
            ("aorta", "大動脈", (126, 37, 165, 52)),
            ("pulmonary artery", "肺動脈", (393, 47, 498, 66)),
            ("cranial vena cava", "前大静脈", (58, 69, 167, 85)),
            ("coronary artery and vein", "冠状動脈・冠状静脈", (391, 126, 537, 145)),
            ("coronary artery and vein ", "冠状動脈・冠状静脈", (21, 149, 166, 168)),
            ("caudal vena cava", "後大静脈", (58, 237, 167, 253)),
        ],
    },
    "organs": {
        "file": "Anatomy_and_physiology_of_animals_main_organs_vertebrate_body.jpg", "name": "からだの主な臓器（腹側から見た模式図）",
        "labels": [
            ("thymus", "胸腺", (352, 105, 404, 122)),
            ("left lung", "左肺", (412, 155, 466, 174)),
            ("heart", "心臓", (436, 187, 476, 203)),
            ("diaphragm", "横隔膜", (2, 219, 73, 238)),
            ("stomach", "胃", (390, 233, 448, 249)),
            ("liver", "肝臓", (17, 249, 51, 265)),
            ("spleen", "脾臓", (372, 258, 420, 277)),
            ("small intestine", "小腸", (348, 281, 438, 297)),
            ("right kidney", "右の腎臓", (38, 283, 113, 302)),
            ("ovary", "卵巣", (391, 317, 433, 331)),
            ("bladder", "膀胱", (45, 343, 98, 359)),
            ("uterus", "子宮", (286, 397, 332, 412)),
            ("testis", "精巣", (230, 434, 271, 449)),
        ],
    },
    # 骨格図は番号と凡例が最初から付いている（番号＝凡例の番号）
    "skeleton": {
        "file": "Skeleton_of_a_dog_diagram.svg", "name": "犬の骨格", "svg": True,
        # 橈骨と尺骨、脛骨と腓骨は、番号の点がどちらの骨を指すか図から読み取りにくいので、場所の説明には使わない
        "unsure": ["9", "10", "21", "22"],
        "legend": {
            1: ("Cranium, or Skull", "頭蓋"), 2: ("Maxilla", "上顎骨"), 3: ("Mandible, or Lower jaw", "下顎骨"), 4: ("Atlas", "環椎"),
            5: ("Axis", "軸椎"), 6: ("Scapula, or Shoulder-blade", "肩甲骨"), 7: ("Spine of scapula", "肩甲棘"), 8: ("Humerus", "上腕骨"),
            9: ("Radius", "橈骨"), 10: ("Ulna", "尺骨"), 11: ("Phalanges", "指骨"), 12: ("Metacarpal Bones", "中手骨"),
            13: ("Carpal Bones or Wrist-bones", "手根骨"), 14: ("Sternum, or Breast-bone", "胸骨"), 15: ("Cartilaginous part of rib", "肋軟骨"),
            16: ("Ribs (13 in number)", "肋骨"), 17: ("Phalanges", "趾骨"), 18: ("Metatarsal Bones", "中足骨"), 19: ("Tarsal Bones", "足根骨"),
            20: ("Calcaneus (os calcu)", "踵骨"), 21: ("Fibula", "腓骨"), 22: ("Tibia", "脛骨"), 23: ("Patella, or Knee-cap", "膝蓋骨"),
            24: ("Femur", "大腿骨"), 25: ("Ischium", "坐骨"), 26: ("Pelvis, or Hip-bone", "寛骨"),
            "A": ("Cervical or Neck Bones (7 in number)", "頸椎"), "B": ("Dorsal or Thoracic Bones (13 in number, each bearing a rib)", "胸椎"),
            "C": ("Lumbar Bones (7 in number)", "腰椎"), "D": ("Sacral Bones (3 in number)", "仙椎"), "E": ("Caudal or Tail Bones (20 to 23 in number)", "尾椎"),
        },
    },
}
SCALE = 2  # 小さい教科書図は2倍に拡大してから番号を描く


def masked(fig):
    im = Image.open(SRC / fig["file"]).convert("RGB")
    W = im.width
    im = im.resize((im.width * SCALE, im.height * SCALE), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    font = ImageFont.truetype(FONT, 13 * SCALE)
    jfont = ImageFont.truetype(JFONT, 12 * SCALE)
    labels = fig["labels"]
    # 番号は上から順（同じ高さなら左から）
    order = sorted(range(len(labels)), key=lambda i: ((labels[i][2][1] + labels[i][2][3]) // 30, labels[i][2][0]))
    num = {i: k + 1 for k, i in enumerate(order)}
    for i, (_, _, r, *_) in enumerate(labels):
        x0, y0, x1, y1 = (v * SCALE for v in r)
        d.rectangle((x0 - 2, y0 - 2, x1 + 2, y1 + 2), fill="white")
    for i, (_, _, r, *side) in enumerate(labels):
        x0, y0, x1, y1 = (v * SCALE for v in r)
        cx = (r[0] + r[2]) / 2
        # 引き出し線がつながる側（図の中心に近い側）に番号を置く。side で "R"/"L" を指定もできる
        if side:
            x = x1 - 13 * SCALE if side[0] == "R" else x0 + 13 * SCALE
        elif r[2] - r[0] < 40:
            x = (x0 + x1) / 2
        elif cx < W / 2:
            x = x1 - 13 * SCALE
        else:
            x = x0 + 13 * SCALE
        y = (y0 + y1) / 2
        R = 12 * SCALE
        d.ellipse((x - R, y - R, x + R, y + R), fill=PINK, outline="white", width=2 * SCALE)
        d.text((x, y + 1), str(num[i]), font=font, fill="white", anchor="mm")
    for text, r in fig.get("captions", []):
        x0, y0, x1, y1 = (v * SCALE for v in r)
        d.rectangle((x0 - 2, y0 - 2, x1 + 2, y1 + 2), fill="white")
        d.text(((x0 + x1) / 2, (y0 + y1) / 2), text, font=jfont, fill=(40, 40, 40), anchor="mm")
    if "crop" in fig:
        im = im.crop(tuple(v * SCALE for v in fig["crop"]))
    keys = {labels[i][0]: {"n": num[i], "ja": labels[i][1]} for i in range(len(labels))}
    return im, keys


def skeleton(fig):
    doc = fitz.open(SRC / fig["file"])
    pix = doc[0].get_pixmap(dpi=96)  # 1052x744 → 約1000px幅
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    keys = {str(k): {"n": k, "ja": v[1], "en": v[0]} for k, v in fig["legend"].items()}
    return im, keys


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = json.loads((SRC / "meta.json").read_text())
    figs = {}
    for fid, fig in FIGS.items():
        im, keys = skeleton(fig) if fig.get("svg") else masked(fig)
        if im.width > 1000:
            im = im.resize((1000, round(im.height * 1000 / im.width)), Image.LANCZOS)
        im.save(OUT / f"{fid}.webp", "WEBP", quality=82)
        m = meta[fig["file"]]
        if "Ruth Lawson" in m["description"]:  # Commons の Artist 欄はアップロード者なので、説明欄の作者名を使う
            m = {**m, "artist": "Ruth Lawson（Otago Polytechnic）"}
        figs[fid] = {"name": fig["name"], "img": f"data/figs/{fid}.webp", "keys": keys,
                     "credit": {"title": m["title"].replace("File:", ""), "author": m["artist"].split("\n")[0].strip(),
                                "license": m["license"], "license_url": m["license_url"], "url": m["page"],
                                "note": "英語ラベルを番号に置き換えて改変" if not fig.get("svg") else "改変なし（凡例を日本語訳）"}}
        print(fid, im.size, len(keys))
    qsrc = SRC / "fig_questions.json"
    questions = build_questions(json.loads(qsrc.read_text()), figs) if qsrc.exists() else []
    (ROOT / "app" / "data" / "figs.json").write_text(json.dumps({"figs": figs, "questions": questions}, ensure_ascii=False, indent=1))
    print("questions", len(questions))


CIRC = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖"


def mark(n):
    return CIRC[n - 1] if isinstance(n, int) else n


def build_questions(src, figs):
    out = []
    for no, (qid, q) in enumerate(src.items(), 1):
        f = figs[q["fig"]]
        keys = f["keys"]
        tgt = keys[q["target"]]
        fill = lambda t: t.replace("{n}", mark(tgt["n"]))
        stem = fill(q["stem"])
        if q["kind"] == "term":      # 「図の③はどれか」→ 日本語名から選ぶ
            opts = [keys[k] for k in q["options"]] if "options" in q else None
            choices = [o["ja"] for o in opts] if opts else q["choices"]
            answer = choices.index(tgt["ja"]) + 1 if opts else q["answer"]
            where = {o["ja"]: o["n"] for o in opts} if opts else {}
        elif q["kind"] == "num":     # 「小脳はどれか」→ 番号から選ぶ
            opts = [keys[k] for k in q["options"]]
            choices = [mark(o["n"]) for o in opts]
            answer = q["options"].index(q["target"]) + 1
            where = {}
        else:                        # 選択肢を直接書く問題（役割を問うなど）
            choices, answer, where, opts = q["choices"], q["answer"], {}, None
        # 正答の位置が偏らないよう、問題ごとに決まった並びにシャッフル
        perm = list(range(len(choices)))
        random.Random(qid).shuffle(perm)
        choices = [choices[i] for i in perm]
        if opts:
            opts = [opts[i] for i in perm]
        answer = perm.index(answer - 1) + 1
        unsure = {keys[k]["ja"] for k in FIGS[q["fig"]].get("unsure", [])}
        where = {k: v for k, v in where.items() if k not in unsure}
        expl_choices = []
        for i, c in enumerate(choices):
            if i + 1 == answer:
                expl_choices.append("正答。" + fill(q.get("why", "")))
            elif q["kind"] == "num":
                expl_choices.append(f"正答ではありません。{c}は{opts[i]['ja']}です。")
            elif c in where:
                expl_choices.append(f"正答ではありません。{c}は図の{mark(where[c])}です。")
            else:
                expl_choices.append("正答ではありません。" + q.get("notes", {}).get(c, ""))
        out.append({
            "id": "fig-" + qid, "genre": "fig", "level": q.get("level", 2), "fig": q["fig"],
            "examName": "図で覚える", "section": f["name"], "no": no,
            "stem": stem, "choices": choices, "answer": [answer],
            "source": {"title": "図：" + f["credit"]["title"], "publisher": f"{f['credit']['author']}／{f['credit']['license']}（{f['credit']['note']}）", "url": f["credit"]["url"]},
            "explanation": {"summary": fill(q["summary"]), "choices": expl_choices, "point": q.get("point", ""), "refs": q["refs"], "checked": q["checked"]},
            "related": q.get("related", []),
        })
    return out


if __name__ == "__main__":
    main()
