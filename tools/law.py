"""e-Gov法令API v2 から現行条文を取得して表示する。
使い方: python3 tools/law.py <法令名の一部 or law_id> [条番号 例: 4 / 44 / 41]
"""
import json, re, sys, urllib.parse, urllib.request
from pathlib import Path

CACHE = Path(__file__).resolve().parent.parent / "private" / "cache"
API = "https://laws.e-gov.go.jp/api/2"


def get(url):
    key = CACHE / (re.sub(r"[^\w]", "_", url)[-180:] + ".json")
    if key.exists():
        return json.loads(key.read_text())
    with urllib.request.urlopen(url, timeout=60) as r:
        d = json.load(r)
    key.write_text(json.dumps(d, ensure_ascii=False))
    return d


def find_law(q):
    if re.fullmatch(r"\w{10,}", q) and re.search(r"\d", q):
        return q, None
    d = get(f"{API}/laws?law_title={urllib.parse.quote(q)}")
    laws = d.get("laws", [])
    laws.sort(key=lambda l: (l["revision_info"]["law_title"] != q, len(l["revision_info"]["law_title"])))
    l = laws[0]
    return l["law_info"]["law_id"], l["revision_info"]["law_title"]


def text(node):
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        return "".join(text(c) for c in node.get("children", []))
    return "".join(text(c) for c in node)


def walk(node, out):
    if isinstance(node, dict):
        if node.get("tag") == "SupplProvision":
            return
        if node.get("tag") == "Article":
            out.append(node)
            return
        for c in node.get("children", []):
            walk(c, out)


def fmt_article(a):
    lines = []
    for c in a.get("children", []):
        if not isinstance(c, dict):
            continue
        t = c.get("tag")
        if t in ("ArticleCaption", "ArticleTitle"):
            lines.append(text(c))
        elif t == "Paragraph":
            num = c.get("attr", {}).get("Num", "")
            body = []
            for p in c.get("children", []):
                if isinstance(p, dict) and p.get("tag") == "ParagraphSentence":
                    body.append(text(p))
                elif isinstance(p, dict) and p.get("tag") == "Item":
                    body.append("\n    " + text(p))
            lines.append(f"  [{num}] " + "".join(body))
    return "\n".join(lines)


def main():
    law_id, title = find_law(sys.argv[1])
    d = get(f"{API}/law_data/{law_id}?response_format=json&law_full_text_format=json")
    ri = d.get("revision_info", {})
    print(f"# {ri.get('law_title', title)} ({law_id}) 施行日:{ri.get('amendment_enforcement_date')} 更新:{ri.get('updated')}")
    print(f"# https://laws.e-gov.go.jp/law/{law_id}")
    arts = []
    walk(d["law_full_text"], arts)
    want = sys.argv[2:] or None
    for a in arts:
        n = a.get("attr", {}).get("Num", "")
        if want is None or n in want:
            print(fmt_article(a))
            print()


if __name__ == "__main__":
    main()
