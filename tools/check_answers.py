"""解説の選択肢説明が公式正答と食い違っていないかを機械チェックする（入れ替わり事故の防止）。
使い方: python3 tools/check_answers.py private/explanations/*.json
- choices が5要素でない
- 正答の選択肢の説明が「正答ではありません」等の否定で始まる
- 正答でない選択肢の説明が「正答」「正しい」で始まる
"""
import json, re, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
Q = {q["id"]: q for q in json.loads((ROOT / "private" / "questions.raw.json").read_text())}

# 「誤っているのはどれか」型では正答の選択肢が「誤り（正答）」になるため、明示的な「正答」の印だけで判定する
NEG = re.compile(r"正答ではな|正答でない|不正解")
POS = re.compile(r"^\s*(正答[。：:]|正答です|正答（|正答\(|正答$)|[（(]正答[）)]")


def main():
    bad = 0
    for f in sys.argv[1:]:
        for qid, e in json.loads(Path(f).read_text()).items():
            if "summary" not in e:
                continue
            ans = Q[qid]["answer"]
            # 要旨・ポイント中の「正答は④」等の番号が公式正答と一致するか
            neg = bool(re.search(r"誤って|でない|でないの|含まれない|ではない|不適切|適切でない|行わない|ならない|しない", Q[qid]["stem"]))
            pats = [r"(?:正答|正解|答え)は\s*([①②③④⑤])"]
            pats.append(r"(?:誤っている|誤り|間違っている|適切でない|あてはまらない)(?:の|記述|もの)?は\s*([①②③④⑤])" if neg else r"(?:正しい|適切な|あてはまる)(?:の|記述|もの)?は\s*([①②③④⑤])")
            for field in ("summary", "point"):
                for pat in pats:
                    for m in re.finditer(pat, e.get(field, "")):
                        if "①②③④⑤".index(m.group(1)) + 1 not in ans:
                            print(f"SUMMARY-NUMBER {f} {qid} {field}: {m.group(0)}"); bad += 1
            # 「③「尿の産生量が増加する」」のような番号＋選択肢文の組が、実際の選択肢と一致するか
            norm = lambda t: re.sub(r"[\s　。、，,.]", "", unicodedata.normalize("NFKC", t))
            texts = [e.get("summary", ""), e.get("point", "")] + list(e.get("choices") or []) + list(e.get("lesson") or [])
            opts = [norm(c) for c in Q[qid]["choices"]]
            for t in texts:
                for m in re.finditer(r"([①②③④⑤])\s*[「『]([^」』]{2,})[」』]", t):
                    n, quoted = "①②③④⑤".index(m.group(1)), norm(m.group(2))
                    if quoted in opts[n] or opts[n] in quoted:
                        continue
                    other = [i + 1 for i, o in enumerate(opts) if quoted in o or o in quoted]
                    if other:
                        print(f"NUMBER-TEXT-MISMATCH {f} {qid}: {m.group(0)[:40]} → 実際は選択肢{other}"); bad += 1
            for j, raw in enumerate(Q[qid]["choices"]):  # 「⑤のSID」型（短い選択肢の語の前に番号）
                w = raw.strip()
                if not (1 <= len(w) <= 15):
                    continue
                for t in texts:
                    for m in re.finditer(r"([①②③④⑤])\s*(?:の|：|:)?\s*" + re.escape(w), t):
                        if "①②③④⑤".index(m.group(1)) != j:
                            print(f"NUMBER-TEXT-MISMATCH {f} {qid}: {m.group(0)[:40]} → 実際は選択肢[{j + 1}]"); bad += 1
            ch = e.get("choices")
            if not ch:
                continue
            if len(ch) != 5:
                print(f"LEN {f} {qid} {len(ch)}"); bad += 1; continue
            marked = all(c.lstrip().startswith(("正答。", "正答ではありません")) for c in ch)
            if marked:  # 冒頭マーカー方式：公式正答の番号と厳密に照合
                for i, c in enumerate(ch, 1):
                    if (i in ans) != c.lstrip().startswith("正答。"):
                        print(f"MARKER-MISMATCH {f} {qid} c{i}: {c[:60]}"); bad += 1
                continue
            for i, c in enumerate(ch, 1):
                if i in ans and NEG.search(c):
                    print(f"ANSWER-NEGATED {f} {qid} c{i}: {c[:60]}"); bad += 1
                if i not in ans and POS.search(c):
                    print(f"NONANSWER-POSITIVE {f} {qid} c{i}: {c[:60]}"); bad += 1
    print(f"problems: {bad}")


if __name__ == "__main__":
    main()
