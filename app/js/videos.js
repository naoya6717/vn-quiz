// おすすめ動画（ジャンル別・横スクロール）と視聴トラッキング。
import { store } from "./store.js";
import { h, modal } from "./ui.js";

let data = null;
async function load() {
  if (!data) {
    try { data = await (await fetch("data/videos.json")).json(); } catch { data = { genres: [] }; }
  }
  return data;
}

const fmt = (sec) => { sec = Math.round(sec || 0); return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`; };

function card(v) {
  const st = store.get().videos[v.id];
  const pct = st && st.dur ? Math.min(100, Math.round((st.watched || 0) / st.dur * 100)) : 0;
  return `<button class="vcard" data-v="${h(v.id)}">
    <div class="th"><img src="${h(v.thumb)}" alt="" loading="lazy">
      ${st && st.state === "done" ? '<span class="done">視聴済み</span>' : ""}
      ${st && st.state === "watching" ? `<span class="prog" style="width:${pct}%"></span>` : ""}</div>
    <div class="meta"><div class="t">${h(v.title)}</div><div class="c">${h(v.channel)}・${fmt(v.duration)}${v.likes ? `・👍${Number(v.likes).toLocaleString()}` : ""}</div></div></button>`;
}

export async function videosView(view, { onWatched }) {
  const d = await load();
  const all = Object.fromEntries(d.genres.flatMap((g) => g.videos.map((v) => [v.id, v])));
  const vs = store.get().videos;
  const watching = Object.entries(vs).filter(([id, s]) => s.state === "watching" && all[id]).sort((a, b) => b[1].at - a[1].at).map(([id]) => all[id]);
  const done = Object.entries(vs).filter(([id, s]) => s.state === "done" && all[id]).sort((a, b) => b[1].at - a[1].at).map(([id]) => all[id]);
  const row = (title, list, note = "") => list.length ? `<h2>${title} <span class="muted">${list.length}本${note}</span></h2><div class="hscroll">${list.map(card).join("")}</div>` : "";
  view.innerHTML = `<h1>▶️ おすすめ動画</h1>
    <p class="muted">YouTubeで評価の高い試験対策・解説動画をジャンル別に集めています。最後まで見ると +30pt。動画の内容は投稿者によるものなので、覚える内容は教科書や過去問の解説で確認しましょう。</p>
    ${row("視聴中", watching)}
    ${d.genres.map((g) => row(h(g.name), g.videos.filter((v) => !vs[v.id] || vs[v.id].state !== "done"))).join("")}
    ${row("視聴済み", done)}
    ${d.genres.length ? "" : '<div class="card muted">動画リストを準備中です。</div>'}
    ${d.generatedAt ? `<p class="muted">リスト更新日：${h(d.generatedAt)}（YouTube Data API で取得）</p>` : ""}`;
  view.onclick = (e) => {
    const b = e.target.closest("[data-v]"); if (!b) return;
    openVideo(all[b.dataset.v], async () => { await onWatched(); videosView(view, { onWatched }); }, () => videosView(view, { onWatched }));
  };
}

// YouTube IFrame Player API
let apiReady = null;
function loadAPI() {
  if (apiReady) return apiReady;
  apiReady = new Promise((res) => {
    window.onYouTubeIframeAPIReady = res;
    const s = document.createElement("script");
    s.src = "https://www.youtube.com/iframe_api";
    document.head.appendChild(s);
  });
  return apiReady;
}

// 実際に再生された秒数だけを数える（シークで飛ばした分は数えない）。8割以上見て最後まで到達したら視聴済み。
export async function openVideo(v, onDone, onClose) {
  let timer = null, player = null;
  const { el } = modal(`<div class="player"><div id="yt"></div></div>
    <p style="font-weight:700;margin:10px 0 2px">${h(v.title)}</p><p class="muted" style="margin:0">${h(v.channel)}</p>
    <p class="muted" id="vstat"></p>
    <a class="muted" href="https://www.youtube.com/watch?v=${h(v.id)}" target="_blank" rel="noopener">YouTubeで開く</a>
    <button class="btn ghost" data-close style="margin-top:10px">とじる</button>`, {
    onClose: () => { clearInterval(timer); save(); try { player && player.destroy(); } catch { /* */ } onClose && onClose(); },
  });
  const rec = () => (store.get().videos[v.id] ||= { state: "watching", watched: 0, t: 0, dur: v.duration || 0, at: Date.now() });
  let last = null;
  const save = () => {
    if (!player || !player.getCurrentTime) return;
    store.update(() => { const r = rec(); r.t = player.getCurrentTime(); r.at = Date.now(); });
  };
  const status = () => {
    const r = store.get().videos[v.id];
    el.querySelector("#vstat").textContent = r && r.state === "done" ? "✅ 視聴済み" : r ? `視聴 ${fmt(r.watched)} / ${fmt(r.dur)}` : "";
  };
  status();
  await loadAPI();
  const startAt = store.get().videos[v.id]?.state === "watching" ? Math.floor(store.get().videos[v.id].t || 0) : 0;
  player = new YT.Player(el.querySelector("#yt"), {
    videoId: v.id,
    playerVars: { playsinline: 1, rel: 0, start: startAt },
    events: {
      onStateChange: (e) => {
        if (e.data === YT.PlayerState.PLAYING) {
          store.update(() => { const r = rec(); r.dur = player.getDuration() || r.dur; });
          last = player.getCurrentTime();
          clearInterval(timer);
          timer = setInterval(() => {
            const now = player.getCurrentTime(), dt = now - last;
            last = now;
            if (dt > 0 && dt < 2.5) store.update(() => { const r = rec(); if (r.state !== "done") r.watched = (r.watched || 0) + dt; r.t = now; });
            status();
          }, 1000);
        } else {
          clearInterval(timer); save();
        }
        if (e.data === YT.PlayerState.ENDED) {
          const r = rec();
          if (r.state !== "done" && r.watched >= r.dur * 0.8) {
            store.update(() => { r.state = "done"; r.at = Date.now(); });
            status();
            onDone && onDone();
          }
        }
      },
    },
  });
}
