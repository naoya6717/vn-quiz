"""公式PDF（動物看護師統一認定機構）から問題文・選択肢・正答を抽出して private/questions.raw.json に出力する。

出典: https://www.ccrvn.jp/aigan.shiken.mondai.kakoshiken.html
      https://www.ccrvn.jp/aigan.yobishiken.mondai.kakoshiken.html
"""
import json
import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "private" / "pdf"

NAT_URL = "https://www.ccrvn.jp/aigan.shiken.mondai.kakoshiken.html"
YOBI_URL = "https://www.ccrvn.jp/aigan.yobishiken.mondai.kakoshiken.html"

# (試験ID, 表示名, 区分→PDF, 正答PDF, 出典ページ)
EXAMS = [
    ("k1", "第1回 愛玩動物看護師国家試験（2023年2月）", {"hissu": "1kokkasiken-hissu", "ippan": "1kokkasiken-ippan", "jitti": "1kokkasiken-jitti"}, "1kokkasiken-seitou", NAT_URL),
    ("k2", "第2回 愛玩動物看護師国家試験（2024年2月）", {"hissu": "hissu.d2kokkasiken", "ippan": "ippan.d2kokkasiken", "jitti": "jitti.d2kokkasiken"}, "seitou.d2kokkasiken", NAT_URL),
    ("k3", "第3回 愛玩動物看護師国家試験（2025年2月）", {"hissu": "d3-KHissuMD", "ippan": "d3-KippanMD", "jitti": "d3-KjittiMD"}, "d3-KseitoU", NAT_URL),
    ("k4", "第4回 愛玩動物看護師国家試験（2026年2月）", {"hissu": "KsHissu-d4mv2", "ippan": "KsIppan-d4mv2", "jitti": "KsJitti-d4mv2"}, "KsSeitou-d4sv2", NAT_URL),
    ("y1", "第1回 愛玩動物看護師国家試験 予備試験", {"hissu": "1yobi-hissu", "jitti": "1yobi-jitti"}, "1yobi-seitou", YOBI_URL),
    ("y2", "第2回 愛玩動物看護師国家試験 予備試験", {"hissu": "d2YG_hissumd", "jitti": "d2YG_jittimd"}, "d2YG_seitou", YOBI_URL),
    ("y3", "第3回 愛玩動物看護師国家試験 予備試験", {"hissu": "d3yobi-hissumondai_c", "jitti": "d3yobi-jittimondai_d"}, "d3yobi-seitou_e", YOBI_URL),
    ("y4", "第4回 愛玩動物看護師国家試験 予備試験", {"hissu": "D4ys-hsmd", "jitti": "D4ys-jtmd"}, "D4ys-seitoutiKT", YOBI_URL),
]
SECTION_LABEL = {"hissu": "必須問題", "ippan": "一般問題", "jitti": "実地問題"}
CHOICE_MARKS = "①②③④⑤⑥⑦⑧⑨"
FIGURE_RE = re.compile(r"図|写真|画像|グラフ|下表|表[はにの]|次の表")


def parse_questions(pdf_name):
    doc = fitz.open(PDF / f"{pdf_name}.pdf")
    lines = []
    for page in list(doc)[1:]:  # 表紙を除く
        for ln in page.get_text().split("\n"):
            s = ln.strip()
            if not s or re.fullmatch(r"\d+", s) or s == "図":
                continue
            lines.append(s)
    qs, cur = [], None
    for s in lines:
        m = re.match(r"^問\s*(\d+)\s*(.*)$", s)
        if m:
            cur = {"no": int(m.group(1)), "stem": m.group(2), "choices": []}
            qs.append(cur)
            continue
        if cur is None:
            continue
        if s[0] in CHOICE_MARKS:
            cur["choices"].append(s[1:].strip().lstrip("　").strip())
        elif cur["choices"]:
            cur["choices"][-1] += s
        else:
            cur["stem"] += s
    return qs


def parse_answers(pdf_name):
    """正答表を座標から読む。戻り値 {section: {no: [answers] or None(全員正解等)}}, notes"""
    doc = fitz.open(PDF / f"{pdf_name}.pdf")
    result, notes = {}, []
    for page in doc:
        words = page.get_text("words")
        heads = [w for w in words if w[4] in ("必須問題", "実地問題", "一般問題")]
        cols = sorted([w for w in words if w[4] == "設問番号"], key=lambda w: w[0])
        anscols = sorted([w for w in words if w[4] == "正答"], key=lambda w: w[0])
        if not cols:
            continue
        top = max(w[3] for w in cols)
        for w in words:
            if w[1] > top and not re.fullmatch(r"[\d,，、]+", w[4]):
                notes.append(f"{pdf_name} p{page.number}: '{w[4]}' @({w[0]:.0f},{w[1]:.0f})")
        for ci, qc in enumerate(cols):
            ac = anscols[ci]
            half_left = qc[0] < page.rect.width / 2
            head = [h for h in heads if (h[0] < page.rect.width / 2) == half_left][0][4]
            sec = {"必須問題": "hissu", "実地問題": "jitti", "一般問題": "ippan"}[head]
            qnums = [w for w in words if w[1] > top and abs(w[0] - qc[0]) < 25 and re.fullmatch(r"\d+", w[4])]
            for qw in qnums:
                cy = (qw[1] + qw[3]) / 2
                aw = [w for w in words if w[1] > top and abs((w[1] + w[3]) / 2 - cy) < 4 and ac[0] - 25 < w[0] < ac[0] + 40]
                txt = "".join(w[4] for w in sorted(aw, key=lambda w: w[0]))
                ans = [int(x) for x in re.findall(r"\d", txt)]
                result.setdefault(sec, {})
                no = int(qw[4])
                if sec in result and no in result[sec] and head == "一般問題":
                    no += 0  # 一般問題は左右で 1-50 / 51-100 なので番号自体が異なる
                result[sec][no] = ans or None
    return result, notes


def main():
    out, problems = [], []
    for eid, ename, sections, seitou, url in EXAMS:
        answers, notes = parse_answers(seitou)
        for n in notes:
            problems.append("NOTE " + n)
        for sec, pdf in sections.items():
            qs = parse_questions(pdf)
            for q in qs:
                ans = answers.get(sec, {}).get(q["no"])
                text = q["stem"] + "".join(q["choices"])
                item = {
                    "id": f"{eid}-{sec}-{q['no']:03d}",
                    "exam": eid,
                    "examName": ename,
                    "section": SECTION_LABEL[sec],
                    "no": q["no"],
                    "stem": q["stem"],
                    "choices": q["choices"],
                    "answer": ans,
                    "needsFigure": bool(FIGURE_RE.search(text)),
                    "source": {"title": f"{ename} {SECTION_LABEL[sec]} 問{q['no']}・正答", "publisher": "一般財団法人動物看護師統一認定機構", "url": url},
                }
                if len(q["choices"]) != 5:
                    problems.append(f"{item['id']}: choices={len(q['choices'])}")
                if not ans:
                    problems.append(f"{item['id']}: answer missing")
                out.append(item)
    (ROOT / "private" / "questions.raw.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    usable = [q for q in out if not q["needsFigure"] and q["answer"] and len(q["choices"]) == 5]
    print(f"total={len(out)} usable(no figure)={len(usable)}")
    print("\n".join(problems), file=sys.stderr)


if __name__ == "__main__":
    main()
