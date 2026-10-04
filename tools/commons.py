"""Wikimedia Commons の画像の利用条件・作者・説明を調べ、原本をダウンロードする（図で覚えるコーナー用）。
使い方: python3 tools/commons.py "File:名前.svg" [...]
出力: private/figs/<ファイル名> と private/figs/meta.json（ライセンス・作者・説明・URL）
"""
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "private" / "figs"
UA = {"User-Agent": "VNquizStudyApp/1.0 (personal exam study; contact via github.com/naoya6717)"}


def get(url, raw=False, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                data = r.read()
            return data if raw else json.loads(data)
        except Exception as e:  # 混雑時は待って再試行
            time.sleep(3 * (i + 1))
            err = e
    raise err


def info(title):
    q = urllib.parse.urlencode({"action": "query", "prop": "imageinfo", "iiprop": "url|extmetadata|size", "format": "json", "titles": title})
    p = list(get(f"https://commons.wikimedia.org/w/api.php?{q}")["query"]["pages"].values())[0]
    ii = p["imageinfo"][0]
    m = ii["extmetadata"]
    clean = lambda k: re.sub(r"<[^>]+>", "", m.get(k, {}).get("value", "")).strip()
    return {"title": p["title"], "url": ii["url"].split("?")[0], "page": f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(p['title'].replace(' ', '_'))}",
            "width": ii["width"], "height": ii["height"], "license": clean("LicenseShortName"), "license_url": clean("LicenseUrl"),
            "artist": clean("Artist"), "credit": clean("Credit"), "description": clean("ImageDescription")}


def main():
    DIR.mkdir(parents=True, exist_ok=True)
    metaf = DIR / "meta.json"
    meta = json.loads(metaf.read_text()) if metaf.exists() else {}
    for t in sys.argv[1:]:
        i = info(t)
        name = i["url"].rsplit("/", 1)[-1]
        (DIR / urllib.parse.unquote(name)).write_bytes(get(i["url"], raw=True))
        meta[urllib.parse.unquote(name)] = i
        print(f"{urllib.parse.unquote(name)} | {i['width']}x{i['height']} | {i['license']} | {i['artist'][:40]} | {i['description'][:120]}")
        time.sleep(2)
    metaf.write_text(json.dumps(meta, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
