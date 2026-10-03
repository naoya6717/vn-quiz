"""問題をまたいだ矛盾チェック用に、同じ用語が複数の問題の解説に出てくる箇所を集める。
使い方: python3 tools/cross_terms.py > private/cross/terms.txt
出力: 用語ごとに、その用語を含む文を（問題IDつきで）並べる。2問以上に出る用語だけ。
"""
import json, re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TERM = re.compile(r"[ァ-ヴー]{4,}|[一-龥]{1,6}(?:症|病|炎|薬|剤|ホルモン|ウイルス|菌|法|期間|日|週齢|か月)")
STOP = {"ポイント", "ガイドライン", "マニュアル", "ページ", "プロフェッショナル", "ハンドブック", "テキスト", "ベテリナリーマニュアル", "ベテリナリー", "センター", "方法", "感染症", "細菌", "ウイルス", "疾病", "薬剤", "医薬", "同法", "動物病", "治療法", "タンパク", "エネルギー", "ストレス", "アセスメント", "カロリー"}


def main():
    sents = defaultdict(list)  # term -> [(qid, sentence)]
    for f in sorted((ROOT / "private" / "explanations").glob("*.json")):
        for qid, e in json.loads(f.read_text()).items():
            if "summary" not in e:
                continue
            texts = [e["summary"], e.get("point", ""), e.get("conflict", "")] + list(e.get("lesson") or []) + list(e.get("choices") or [])
            seen = set()
            for t in texts:
                for s in re.split(r"(?<=[。！？])", t):
                    s = s.strip()
                    if len(s) < 8 or s.startswith("正答ではありません") and len(s) < 15:
                        continue
                    for m in set(TERM.findall(s)):
                        if m in STOP or (m, s) in seen:
                            continue
                        seen.add((m, s))
                        sents[m].append((qid, s))
    import sys
    chunks, cur, size = [], [], 0
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10**9
    out = []
    for term, rows in sorted(sents.items(), key=lambda kv: -len({q for q, _ in kv[1]})):
        qids = {q for q, _ in rows}
        if len(qids) < 2 or len(qids) > 25:
            continue
        out.append(f"## {term}  ({len(qids)}問)")
        for q, s in rows:
            out.append(f"- [{q}] {s}")
    # limit 文字ごとに用語の切れ目で分割して private/cross/part_N.txt に書く
    part, buf = 1, []
    for line in out:
        if line.startswith("## ") and sum(len(x) for x in buf) > limit:
            (ROOT / "private" / "cross" / f"part_{part}.txt").write_text("\n".join(buf)); part += 1; buf = []
        buf.append(line)
    (ROOT / "private" / "cross" / f"part_{part}.txt").write_text("\n".join(buf))
    print(f"{part} parts, {sum(len(x) for x in out)} chars, {sum(1 for x in out if x.startswith('## '))} terms")


if __name__ == "__main__":
    main()
