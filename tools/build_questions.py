"""questions.raw.json + genres.txt + explanations/*.json → private/questions.json（平文。公開しない）"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIV = ROOT / "private"

GENRES = {
    "F": "生命倫理・動物福祉", "K": "形態機能学（解剖・生理）", "H": "繁殖学・遺伝", "B": "動物行動学",
    "N": "動物栄養学", "C": "比較動物学", "L": "関連法規", "G": "動物看護学概論・医療安全",
    "P": "動物病理学", "Y": "動物薬理学", "I": "感染症・免疫・公衆衛生", "M": "内科疾患",
    "S": "外科・麻酔・手術", "R": "臨床看護技術・ケア", "T": "臨床検査・画像", "Q": "コミュニケーション・人と動物",
    "A": "愛玩動物学・適正飼養",
}


def difficulty(q):
    """一般正答率は非公表のため、区分と出題形式からの推定値（1=初級 2=中級 3=上級）"""
    if q["section"] == "必須問題":
        return 1
    hard = re.search(r"ａ[：:]", q["stem"]) or re.search(r"\d+\s*(mL|mg|g|％|%)", q["stem"]) or re.search(r"誤って|でないの|適切でない|含まれない", q["stem"])
    return 3 if hard else 2


def main():
    raw = {q["id"]: q for q in json.loads((PRIV / "questions.raw.json").read_text())}
    genre = {}
    for line in (PRIV / "genres.txt").read_text().splitlines():
        pre, *items = line.split()
        for t in items:
            m = re.match(r"(\d+)([A-Z])", t)
            genre[f"{pre}-{int(m.group(1)):03d}"] = m.group(2)
    expl = {}
    for f in sorted((PRIV / "explanations").glob("*.json")):
        for k, v in json.loads(f.read_text()).items():
            if "summary" in v:
                expl[k] = {x: y for x, y in v.items() if x != "evidence"}  # 根拠抜き出しはアプリに載せない
    out = []
    for qid, g in genre.items():
        q = raw[qid]
        item = {k: q[k] for k in ("id", "exam", "examName", "section", "no", "stem", "choices", "answer", "source")}
        item["genre"] = g
        item["level"] = difficulty(q)
        if qid in expl:
            item["explanation"] = expl[qid]
        out.append(item)
    data = {"genres": GENRES, "questions": out}
    (PRIV / "questions.json").write_text(json.dumps(data, ensure_ascii=False))
    from collections import Counter
    print(len(out), "questions; explained:", sum("explanation" in q for q in out))
    print(Counter(q["level"] for q in out), Counter(q["genre"] for q in out).most_common())


if __name__ == "__main__":
    main()
