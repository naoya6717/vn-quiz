"""下書きの evidence（根拠の原文抜き出し）が、出典本文に本当にあるかを機械的に照合する。
使い方: python3 tools/check_evidence.py private/drafts/X1.json
空白・全角半角の違いは無視して照合。見つからない引用と、evidence が無い問題を一覧表示する。
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import get, norm  # noqa


def main():
    d = json.loads(Path(sys.argv[1]).read_text())
    ok = bad = 0
    for qid, e in d.items():
        if "skip" in e:
            continue
        ev = e.get("evidence") or []
        if not ev:
            print(f"NOEVIDENCE {qid}")
            continue
        for x in ev:
            try:
                src = norm(get(x["url"]))
            except (Exception, SystemExit) as err:  # noqa
                print(f"FETCHFAIL {qid} {x['url']} {err}")
                bad += 1
                continue
            if norm(x["quote"]) in src:
                ok += 1
            else:
                bad += 1
                print(f"NOTFOUND {qid} [{x.get('for','')}] {x['url']}\n    {x['quote'][:120]}")
    print(f"\nquotes found: {ok}, not found: {bad}")


if __name__ == "__main__":
    main()
