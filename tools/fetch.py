"""出典の本文を取得してテキストで共有キャッシュ（private/sources/）に保存する。
2回目以降はキャッシュから読むので、同じ資料を何度もダウンロードしない。

使い方:
  python3 tools/fetch.py URL                 # 本文の文字数と保存先だけ表示
  python3 tools/fetch.py URL --grep 語1 語2  # 語を含む箇所だけ前後つきで表示（全文は読まない）
  python3 tools/fetch.py URL --head 3000     # 先頭3000文字を表示
  python3 tools/fetch.py --list              # キャッシュ済みURL一覧
e-Gov法令URL（https://laws.e-gov.go.jp/law/<law_id>）は現行条文の全文（附則を除く）になる。
"""
import hashlib, html, json, os, re, subprocess, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "private" / "sources"
INDEX = DIR / "index.json"
PY = ROOT / "tools" / ".venv" / "bin" / "python"


def norm(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", s))


def _index():
    return json.loads(INDEX.read_text()) if INDEX.exists() else {}


def _law_text(law_id):
    sys.path.insert(0, str(ROOT / "tools"))
    import law  # noqa
    d = law.get(f"{law.API}/law_data/{law_id}?response_format=json&law_full_text_format=json")
    arts = []
    law.walk(d["law_full_text"], arts)
    title = d.get("revision_info", {}).get("law_title", "")
    return f"{title}\n\n" + "\n\n".join(law.fmt_article(a) for a in arts)


def _download(url):
    m = re.match(r"https?://laws\.e-gov\.go\.jp/law/(\w+)", url)
    if m:
        return _law_text(m.group(1))
    r = subprocess.run(["curl", "-sL", "--max-time", "90", "-A", "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/126 Safari/537.36",
                        "-w", "\n__HTTP_STATUS__%{http_code}", url], capture_output=True).stdout
    raw, _, status = r.rpartition(b"\n__HTTP_STATUS__")
    if not status.isdigit() or int(status) >= 400:
        return f"__HTTP_ERROR__ {status.decode(errors='ignore')}"
    if raw[:5] == b"%PDF-":
        tmp = DIR / f"_tmp_{os.getpid()}_{hashlib.sha1(url.encode()).hexdigest()[:8]}.pdf"  # 同時実行で衝突しないように
        tmp.write_bytes(raw)
        out = subprocess.run([str(PY), "-c", "import fitz,sys;print('\\n'.join(f'[p.{i+1}]\\n'+p.get_text() for i,p in enumerate(fitz.open(sys.argv[1]))))", str(tmp)],
                             capture_output=True, text=True).stdout
        tmp.unlink()
        return out
    text = raw.decode("utf-8", errors="ignore")
    if "charset=shift_jis" in text.lower() or "charset=sjis" in text.lower():
        text = raw.decode("cp932", errors="ignore")
    text = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h\d|dt|dd)>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"[ \t　]+", " ", re.sub(r"\n\s*\n+", "\n\n", text)).strip()


BROKEN = ("__http_error__", "recaptcha", "access denied", "404 not found", "page not found", "there doesn't seem to be anything here", "ページが見つかりません", "just a moment", "are you a robot")


def _looks_broken(text):
    t = text.lower()
    return len(text.strip()) < 200 or (len(text) < 5000 and any(b in t for b in BROKEN))


def get(url):
    DIR.mkdir(parents=True, exist_ok=True)
    idx = _index()
    if url in idx and (DIR / idx[url]).exists():
        cached = (DIR / idx[url]).read_text()
        if not _looks_broken(cached):
            return cached
    text = _download(url)
    if _looks_broken(text):
        raise SystemExit(f"取得失敗（エラー/ボット対策ページ）のためキャッシュしません: {url}")
    name = hashlib.sha1(url.encode()).hexdigest()[:16] + ".txt"
    (DIR / name).write_text(text)
    idx = _index()
    idx[url] = name
    INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=0))
    return text


def main():
    a = sys.argv[1:]
    if not a or a[0] == "--list":
        for u, f in _index().items():
            print(f, u)
        return
    if not a[0].startswith("http"):
        print(__doc__); return
    url, rest = a[0], a[1:]
    text = get(url)
    print(f"# {url}\n# {len(text)} chars, cached: private/sources/{_index().get(url)}")
    if rest[:1] == ["--head"]:
        print(text[: int(rest[1]) if len(rest) > 1 else 3000])
    elif rest[:1] == ["--grep"]:
        text = unicodedata.normalize("NFKC", text)  # 全角半角を区別せず検索
        for w in rest[1:]:
            w = unicodedata.normalize("NFKC", w)
            hits = [m.start() for m in re.finditer(re.escape(w), text)]
            print(f"\n## '{w}': {len(hits)} hits")
            for p in hits[:8]:
                print("…" + text[max(0, p - 200): p + 300].replace("\n", " ") + "…\n")


if __name__ == "__main__":
    main()
