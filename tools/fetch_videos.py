"""YouTube Data API v3 でジャンル別の高評価動画を集め、app/data/videos.json の候補を private/videos.candidates.json に出力する。
APIキーは環境変数 YOUTUBE_API_KEY、無ければ ../idol-zukan/.env から読む（公開ファイルには書き出さない）。
"""
import json, os, re, sys, urllib.parse, urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUERIES = [
    ("exam", "試験対策・勉強法", ["愛玩動物看護師 国家試験 対策", "愛玩動物看護師 国家試験 勉強法"]),
    ("K", "解剖・生理", ["愛玩動物看護師 解剖生理", "動物看護師 解剖学 犬 猫", "動物看護 生理学 わかりやすく"]),
    ("H", "繁殖・遺伝・行動", ["愛玩動物看護師 繁殖学", "犬 行動学 学習理論 動物看護", "動物行動学 犬 猫 問題行動 獣医"]),
    ("N", "栄養学", ["動物看護師 栄養学", "犬 猫 栄養学 獣医師 解説"]),
    ("I", "感染症・公衆衛生", ["愛玩動物看護師 感染症", "人獣共通感染症 獣医師 解説", "犬 猫 感染症 ワクチン 獣医師"]),
    ("PY", "病理・薬理", ["動物看護師 薬理学", "動物看護師 病理学"]),
    ("M", "内科疾患", ["愛玩動物看護師 内科", "犬 猫 病気 獣医師 解説 腎臓病", "犬 猫 内分泌疾患 獣医師"]),
    ("S", "外科・麻酔・手術", ["動物看護師 手術 器具 名前", "動物看護師 麻酔 モニタリング", "動物病院 手術 準備 看護師"]),
    ("T", "臨床検査", ["動物看護師 血液検査", "動物看護師 尿検査 糞便検査"]),
    ("R", "看護技術・保定", ["動物看護師 保定 犬 猫", "動物看護師 看護技術 採血 補助"]),
    ("L", "法規", ["愛玩動物看護師法 解説", "動物愛護管理法 解説", "愛玩動物看護師 法規 国家試験"]),
    ("A", "愛玩動物学・適正飼養", ["犬種 覚え方 動物看護", "エキゾチックアニマル 飼育 獣医師", "ペット 災害 同行避難 環境省"]),
]


def key():
    if os.environ.get("YOUTUBE_API_KEY"):
        return os.environ["YOUTUBE_API_KEY"]
    for line in (ROOT.parent / "idol-zukan" / ".env").read_text().splitlines():
        if line.startswith("YOUTUBE_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("YOUTUBE_API_KEY not found")


K = key()


def api(path, **params):
    params["key"] = K
    with urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/{path}?{urllib.parse.urlencode(params)}", timeout=30) as r:
        return json.load(r)


def dur(iso):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    h, mi, s = (int(x or 0) for x in m.groups()) if m else (0, 0, 0)
    return h * 3600 + mi * 60 + s


def main():
    out = []
    for gid, name, qs in QUERIES:
        ids = []
        for q in qs:
            r = api("search", part="id", q=q, type="video", maxResults=25, regionCode="JP", relevanceLanguage="ja", safeSearch="strict", videoEmbeddable="true")
            ids += [it["id"]["videoId"] for it in r.get("items", [])]
        ids = list(dict.fromkeys(ids))
        vids = []
        for i in range(0, len(ids), 50):
            r = api("videos", part="snippet,statistics,contentDetails,status", id=",".join(ids[i:i + 50]))
            for v in r.get("items", []):
                st, sn = v.get("statistics", {}), v["snippet"]
                d = dur(v["contentDetails"].get("duration"))
                if not v["status"].get("embeddable") or d < 120 or d > 3600:
                    continue
                vids.append({
                    "id": v["id"], "title": sn["title"], "channel": sn["channelTitle"],
                    "thumb": (sn["thumbnails"].get("high") or sn["thumbnails"]["default"])["url"],
                    "likes": int(st.get("likeCount", 0)), "views": int(st.get("viewCount", 0)),
                    "duration": d, "published": sn["publishedAt"][:10],
                })
        vids.sort(key=lambda v: v["likes"], reverse=True)
        out.append({"id": gid, "name": name, "videos": vids[:20]})
        print(gid, name, len(vids), file=sys.stderr)
    (ROOT / "private" / "videos.candidates.json").write_text(json.dumps({"generatedAt": date.today().isoformat(), "genres": out}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
