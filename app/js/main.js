import { store, today, addPoints } from "./store.js";
import { db, unlock, savedPass, autoUnlock } from "./data.js";
import { renderDog, levelInfo, stageOf, say, BREEDS, STAGES, dogName, breedOf } from "./dog.js";
import { ITEMS, itemVisual } from "./items.js";
import { videosView } from "./videos.js";
import { h, toast, modal } from "./ui.js";

const NUM = "①②③④⑤";
const LEVELS = { 1: "初級", 2: "中級", 3: "上級" };
const LEVEL_MUL = { 1: 1, 2: 1.5, 3: 2 };

const $ = (s, el = document) => el.querySelector(s);
const view = $("#view");
function confetti() {
  const box = document.createElement("div");
  box.className = "confetti";
  const colors = ["#e98a5c", "#f6c39f", "#3fa66b", "#e7b63c", "#ef6f86", "#6fa8ef"];
  for (let i = 0; i < 60; i++) {
    const c = document.createElement("i");
    c.style.left = Math.random() * 100 + "vw";
    c.style.background = colors[i % colors.length];
    c.style.animationDuration = 1.6 + Math.random() * 1.8 + "s";
    c.style.animationDelay = Math.random() * .5 + "s";
    box.appendChild(c);
  }
  document.body.appendChild(box);
  setTimeout(() => box.remove(), 4200);
}

function refreshTop() {
  const s = store.get();
  $("#ptsVal").textContent = s.points.toLocaleString();
  const li = levelInfo();
  $("#lvBadge").textContent = `Lv.${li.lv}`;
  $("#lvExp").style.width = `${li.pct}%`;
}
store.onChange(refreshTop);

// EXPを足し、レベルが上がったらお祝いポップアップ
async function gainExp(n) {
  const before = levelInfo().lv;
  store.update((s) => { s.exp += n; });
  const after = levelInfo().lv;
  if (after > before) {
    const st = stageOf(after), stBefore = stageOf(before);
    const { el, close } = modal(`<div class="levelup">
      <div class="t">LEVEL UP!</div>
      <div class="muted">Lv.${before} → <b style="font-size:20px;color:var(--accent)">Lv.${after}</b></div>
      ${st !== stBefore ? `<p><b>「${h(st.name)}」に成長したよ！</b></p>` : ""}
      <div class="dog" id="luDog"></div>
      <div class="bubble" id="luBubble"></div>
      <button class="btn" data-close style="margin-top:10px">やったね！</button></div>`);
    await renderDog($("#luDog", el), { happy: true });
    say($("#luBubble", el), "levelup");
    confetti();
    return close;
  }
}

// ---------- ルーター ----------
const routes = {};
function go(hash) { location.hash = hash; }
window.addEventListener("hashchange", render);
async function render() {
  const [, name = "home", arg] = location.hash.split("/");
  document.querySelectorAll(".tabbar a").forEach((a) => a.classList.toggle("on", a.dataset.tab === (TAB_OF[name] || name)));
  window.scrollTo(0, 0);
  document.body.classList.toggle("home-fixed", !routes[name] || name === "home"); // ホームは画面に固定（スクロールしない）
  const fn = routes[name] || routes.home;
  await fn(arg);
}
const TAB_OF = { play: "quiz", result: "quiz", shop: "home", lesson: "home", install: "home", unlock: "home", welcome: "home", settings: "stats" };

const isStandalone = () => window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
const isIOS = () => /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

async function ensureData() {
  if (db()) return db();
  try { return await autoUnlock(); } catch { /* 鍵ファイルが読めない場合は保存済みの合言葉を試す */ }
  const p = savedPass();
  if (p) { try { return await unlock(p); } catch { /* 合言葉が変わった */ } }
  go("#/unlock");
  return null;
}

// ---------- ホーム ----------
routes.home = async () => {
  const s = store.get();
  if (!s.seenIntro && !isStandalone()) return go("#/install");
  if (!s.dog) return go("#/welcome");
  const li = levelInfo(), st = stageOf(li.lv);
  const lessonDone = !!s.lessons[today()];
  view.innerHTML = `
    <div class="stage">
      <div class="bubble" id="bubble"></div>
      <div class="room" id="room"></div>
      <div class="namebar"><b>${h(st.name)}</b><span class="lvchip">Lv.${li.lv}</span></div>
      <div class="expbar"><i style="width:${li.pct}%"></i></div>
      <div class="muted">つぎのレベルまで あと <b>${li.toNext}</b> EXP</div>
    </div>
    <div class="menu">
      <a href="#/quiz" class="t-quiz"><span class="ico">✏️</span><span><b>過去問クイズ</b><br><span class="muted">10問で1セット！</span></span><span class="go">START</span></a>
      <a href="#/lesson" class="t-lesson ${lessonDone ? "done" : ""}"><span class="ico">💡</span><b>ワンポイント${lessonDone ? "" : '<span class="badge">NEW</span>'}</b><span class="muted">${lessonDone ? "今日はクリア済み" : "1日1回 +50pt"}</span></a>
      <a href="#/shop" class="t-shop"><span class="ico">🎁</span><b>ショップ</b><span class="muted">${h(dogName())}にプレゼント</span></a>
      <a href="#/videos" class="t-video"><span class="ico">🎬</span><b>動画</b><span class="muted">見終わると +30pt</span></a>
    </div>`;
  await renderRoom($("#room"));
  const dog = $("#dog");
  say($("#bubble"), null);
  dog.onclick = () => {
    dog.classList.remove("hop"); void dog.offsetWidth; dog.classList.add("hop");
    say($("#bubble"), "tap");
  };
};

// ---------- 部屋（買ったアイテムを飾る） ----------
async function renderRoom(el) {
  const owned = store.get().items;
  const has = (id) => !!owned[id];
  const placed = ITEMS.filter((it) => it.kind === "room" && it.place && has(it.id));
  const parts = await Promise.all(placed.map(async (it) => {
    const p = it.place, pos = p.top != null ? `top:${p.top}%` : `bottom:${p.bottom}%`;
    return `<div class="ritem" style="left:${p.x}%;${pos};width:${p.w}%;--w:${p.w};z-index:${p.z}" title="${h(it.name)}">${await itemVisual(it)}</div>`;
  }));
  el.className = `room${has("wallpaper") ? " wp-star" : ""}`;
  el.innerHTML = `
    <div class="wall"></div><div class="floor"></div>
    <div class="window${has("curtain") ? " curtain" : ""}"><i class="sky"></i><i class="drape l"></i><i class="drape r"></i><i class="valance"></i></div>
    ${has("rug") ? '<div class="rug"></div>' : ""}
    ${parts.join("")}
    <div class="dog" id="dog" title="なでる"></div>
    <span class="sparkle" style="left:8%;top:12%">✦</span><span class="sparkle" style="right:10%;top:44%;animation-delay:.9s">✧</span>`;
  await renderDog($("#dog", el));
}

// ---------- はじめに：相棒の犬と名前を決める ----------
routes.welcome = async () => {
  const cur = store.get().dog || {};
  let pick = cur.breed || BREEDS[0].id;
  view.innerHTML = `
    <h1>🐾 相棒をえらぼう！</h1>
    <p class="muted" style="margin-top:-6px">いっしょに国家試験合格をめざすパートナーです。あとから名前は変えられます。</p>
    <div class="breeds">${BREEDS.map((b) => `
      <button class="breed ${b.id === pick ? "on" : ""}" data-b="${b.id}">
        <span class="check">✓</span>
        <div class="dog" data-dog="${b.id}"></div>
        <b>${h(b.name)}</b><span class="muted">${h(b.desc)}</span>
      </button>`).join("")}</div>
    <div class="card" style="margin-top:14px">
      <b>名前をつけてね</b>
      <input type="text" id="dogName" maxlength="10" autocomplete="off" placeholder="例：もこ" value="${h(cur.name || "")}" style="margin-top:8px">
      <div style="margin-top:14px"><button class="btn" id="decide">この子に決める！</button></div>
    </div>`;
  for (const el of view.querySelectorAll("[data-dog]")) renderDog(el, { breed: el.dataset.dog, stage: STAGES[0] });
  view.querySelector(".breeds").onclick = (e) => {
    const b = e.target.closest("[data-b]"); if (!b) return;
    pick = b.dataset.b;
    view.querySelectorAll(".breed").forEach((x) => x.classList.toggle("on", x === b));
  };
  $("#decide").onclick = () => {
    const name = $("#dogName").value.trim().slice(0, 10);
    if (!name) { toast("名前を入れてね"); $("#dogName").focus(); return; }
    const first = !store.get().dog;
    store.update((st) => { st.dog = { breed: pick, name }; });
    toast(first ? `${name}がなかまになった！` : "設定を変えました");
    go("#/home");
  };
};

// ---------- インストール案内 ----------
let deferredPrompt = null;
window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); deferredPrompt = e; });
routes.install = async () => {
  const ios = isIOS();
  view.innerHTML = `
    <h1>ようこそ！🐩</h1>
    <div class="card">
      <p>このアプリは<b>ホーム画面に追加</b>すると、ふつうのアプリのように全画面で使えます。外出先でもワンタップで開けるので、最初に追加しておきましょう。</p>
    </div>
    ${ios ? `
    <div class="card"><h2 style="margin-top:0">iPhone（Safari）の場合</h2>
      <ol class="steps">
        <li>このページを <b>Safari</b> で開きます（LINEなどのアプリ内ブラウザでは追加できません）</li>
        <li>画面下の <span class="kbd">共有ボタン（□に↑）</span> をタップ</li>
        <li>メニューを下にスクロールして <span class="kbd">ホーム画面に追加</span> をタップ</li>
        <li>右上の <span class="kbd">追加</span> をタップ</li>
        <li>ホーム画面にできた「VN PASS」のアイコンから開きます</li>
      </ol></div>` : `
    <div class="card"><h2 style="margin-top:0">Android（Chrome）の場合</h2>
      ${deferredPrompt ? `<button class="btn" id="installBtn">ホーム画面に追加する</button><p class="muted">ボタンが動かない場合は下の手順で追加できます。</p>` : ""}
      <ol class="steps">
        <li>このページを <b>Chrome</b> で開きます</li>
        <li>右上の <span class="kbd">︙</span> メニューをタップ</li>
        <li><span class="kbd">ホーム画面に追加</span> または <span class="kbd">アプリをインストール</span> をタップ</li>
        <li>ホーム画面のアイコンから開きます</li>
      </ol></div>`}
    <div class="card"><p class="muted">⚠️ 学習記録はこの端末のブラウザに保存されます。ホーム画面に追加したアイコンから開いたものと、Safari/Chromeで開いたものは別の記録になります。いつも同じアイコンから開いてください。機種変更のときは「記録」→「バックアップ」で引き継げます。</p></div>
    <button class="btn ghost" id="skip">あとで（このまま使う）</button>`;
  const ib = $("#installBtn");
  if (ib) ib.onclick = async () => { deferredPrompt.prompt(); await deferredPrompt.userChoice; deferredPrompt = null; };
  $("#skip").onclick = () => { store.update((s) => { s.seenIntro = true; }); go("#/home"); };
};

// ---------- 合言葉 ----------
routes.unlock = async () => {
  view.innerHTML = `
    <h1>合言葉を入力</h1>
    <div class="card">
      <p>過去問データは著作権に配慮して暗号化しています。最初の1回だけ合言葉を入力してください（この端末に保存されます）。</p>
      <input type="text" id="pass" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" placeholder="合言葉（ひらがなで入力できます）">
      <p class="muted" id="err"></p>
      <button class="btn" id="ok">ひらく</button>
    </div>`;
  $("#ok").onclick = async () => {
    $("#err").textContent = "確認中…";
    try { await unlock($("#pass").value.normalize("NFC").replace(/[\s\u3000]/g, "")); toast("データをひらきました"); go("#/quiz"); }
    catch { $("#err").textContent = "合言葉がちがうようです。"; }
  };
};

// ---------- クイズ設定 ----------
const quizConf = { level: "mix", genre: "random" };
routes.quiz = async () => {
  const data = await ensureData(); if (!data) return;
  const counts = {};
  data.questions.forEach((q) => { counts[q.genre] = (counts[q.genre] || 0) + 1; });
  const s = store.get();
  const answered = Object.keys(s.answers).length;
  const lvBtn = (v, l) => `<button data-level="${v}" class="${quizConf.level === v ? "on" : ""}">${l}</button>`;
  view.innerHTML = `
    <h1>過去問クイズ</h1>
    <div class="card">
      <div class="muted" style="margin-bottom:6px">むずかしさ</div>
      <div class="seg" id="lvSeg">${lvBtn("mix", "ミックス")}${lvBtn("1", "初級")}${lvBtn("2", "中級")}${lvBtn("3", "上級")}</div>
      <p class="muted">※ 問題ごとの全国正答率は公表されていないため、難易度は「必須問題＝初級、一般問題＝中級、組合せ・計算・否定形の一般問題＝上級」で推定しています。</p>
      <div class="muted" style="margin:12px 0 6px">ジャンル</div>
      <select id="genre" style="width:100%;font:inherit;padding:10px;border-radius:12px;border:2px solid var(--line);background:var(--bg);color:var(--ink)">
        <option value="random">ランダム（全ジャンル）</option>
        <option value="weak">苦手ジャンルを重点的に</option>
        <option value="wrong">前回まちがえた問題だけ復習（${Object.values(s.answers).filter((a) => a.last === 0).length}問）</option>
        ${Object.entries(data.genres).map(([k, n]) => `<option value="${k}" ${quizConf.genre === k ? "selected" : ""}>${h(n)}（${counts[k] || 0}問）</option>`).join("")}
      </select>
      <div style="margin-top:16px"><button class="btn" id="start">10問スタート！</button></div>
    </div>
    <div class="card muted">
      収録：愛玩動物看護師国家試験 第1〜4回・予備試験 第1〜4回の必須/一般問題 ${data.questions.length}問（図・写真を使う実地問題は、公式PDFで図が非公開のため除外）。<br>
      これまでに解いた問題：${answered}問
    </div>`;
  $("#genre").value = quizConf.genre;
  $("#lvSeg").onclick = (e) => {
    const b = e.target.closest("button"); if (!b) return;
    quizConf.level = b.dataset.level;
    $("#lvSeg").querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
  };
  $("#genre").onchange = (e) => { quizConf.genre = e.target.value; };
  $("#start").onclick = () => startQuiz();
};

function genreStats() {
  const { answers } = store.get(), d = db(), st = {};
  for (const [id, a] of Object.entries(answers)) {
    const q = d.byId[id]; if (!q) continue;
    const g = (st[q.genre] ||= { c: 0, n: 0 });
    g.c += a.c; g.n += a.c + a.w;
  }
  return st;
}
function weakGenres(min = 5) {
  return Object.entries(genreStats()).filter(([, v]) => v.n >= min)
    .sort((a, b) => a[1].c / a[1].n - b[1].c / b[1].n).map(([k]) => k);
}

let session = null;
function startQuiz() {
  const d = db(), ans = store.get().answers;
  let pool = d.questions;
  if (quizConf.level !== "mix") pool = pool.filter((q) => q.level === +quizConf.level);
  let genres = null;
  if (quizConf.genre === "weak") genres = weakGenres().slice(0, 3);
  else if (quizConf.genre !== "random" && quizConf.genre !== "wrong") genres = [quizConf.genre];
  if (genres && genres.length) pool = pool.filter((q) => genres.includes(q.genre));
  if (quizConf.genre === "wrong") pool = pool.filter((q) => ans[q.id] && ans[q.id].last === 0);
  if (quizConf.genre === "weak" && !(genres && genres.length)) toast("まだ記録が少ないので全ジャンルから出題します");
  if (pool.length === 0) { toast("条件に合う問題がありません"); return; }
  // 未回答・前回まちがえた問題を出やすくする重み付き抽選
  const weight = (q) => { const a = ans[q.id]; return !a ? 3 : a.last === 0 ? 4 : 1; };
  const bag = pool.map((q) => ({ q, k: Math.random() ** (1 / weight(q)) })).sort((a, b) => b.k - a.k);
  session = { qs: bag.slice(0, 10).map((x) => x.q), i: 0, results: [], conf: { ...quizConf } };
  go("#/play");
}

// ---------- 出題 ----------
function renderExplanation(q) {
  const e = q.explanation;
  const official = `<li>${h(q.source.title)}（${h(q.source.publisher)}）<br><a href="${h(q.source.url)}" target="_blank" rel="noopener">${h(q.source.url)}</a></li>`;
  if (!e) {
    return `<div class="expl"><div class="pending">📝 この問題の解説は準備中です。正答は公式発表のものです。</div>
      <div class="src">出典<ul>${official}</ul></div></div>`;
  }
  return `<div class="expl">
    <h3>解説</h3><p>${h(e.summary)}</p>
    ${e.conflict ? `<div class="caution">⚠️ 注意：${h(e.conflict)}</div>` : ""}
    ${e.choices ? `<h3>選択肢ごとのポイント</h3><ol style="list-style:none;padding-left:0">${e.choices.map((c, i) => `<li><b>${NUM[i]}</b> ${h(c)}</li>`).join("")}</ol>` : ""}
    ${e.point ? `<h3>💡 覚えるポイント</h3><p>${h(e.point)}</p>` : ""}
    <div class="src">出典<ul>${official}${(e.refs || []).map((r) => `<li>${h(r.title)}${r.note ? `（${h(r.note)}）` : ""}<br><a href="${h(r.url)}" target="_blank" rel="noopener">${h(r.url)}</a></li>`).join("")}</ul>
    ${e.checked ? `解説の出典照合日：${h(e.checked)}` : ""}</div></div>`;
}

function questionHTML(q, idx, total) {
  return `
    <div class="qmeta"><span class="tag">${h(db().genres[q.genre])}</span><span class="tag lv${q.level}">${LEVELS[q.level]}</span><span>${h(q.examName)} ${h(q.section)} 問${q.no}</span></div>
    <p class="stem">${idx != null ? `Q${idx + 1}. ` : ""}${h(q.stem).replace(/([ａｂｃｄｅ])[：:]/g, "\n$1：")}</p>
    <div class="opts">${q.choices.map((c, i) => `<button class="opt" data-n="${i + 1}" data-i="${i + 1}">${h(c)}</button>`).join("")}</div>
    <div id="after"></div>`;
}

function bindAnswer(root, q, onAnswered) {
  const opts = root.querySelectorAll(".opt");
  opts.forEach((b) => b.onclick = () => {
    const pick = +b.dataset.i, ok = q.answer.includes(pick);
    opts.forEach((o) => {
      o.disabled = true;
      if (q.answer.includes(+o.dataset.i)) o.classList.add("correct");
    });
    if (!ok) b.classList.add("wrong");
    store.update((s) => {
      const a = (s.answers[q.id] ||= { c: 0, w: 0 });
      ok ? a.c++ : a.w++; a.last = ok ? 1 : 0; a.at = Date.now();
    });
    const multi = q.answer.length > 1 ? `<p class="muted">※ この問題は公式発表で複数の選択肢（${q.answer.map((n) => NUM[n - 1]).join("・")}）が正解とされています。</p>` : "";
    onAnswered(ok, `<div class="verdict ${ok ? "ok" : "ng"}">${ok ? "GREAT! ⭕" : "ざんねん…"}<small>${ok ? "正解！この調子！" : "解説を読んで覚えちゃおう"}</small></div>
      <p style="text-align:center">正答：<b>${q.answer.map((n) => NUM[n - 1]).join("・")}</b></p>${multi}${renderExplanation(q)}`);
  });
}

routes.play = async () => {
  if (!session || !db()) return go("#/quiz");
  const { qs, i, results } = session, q = qs[i];
  view.innerHTML = `
    <div class="progress">${qs.map((_, k) => `<i class="${k < results.length ? (results[k] ? "ok" : "ng") : k === i ? "cur" : ""}"></i>`).join("")}</div>
    <div class="card">${questionHTML(q, i, qs.length)}</div>`;
  bindAnswer(view, q, (ok, html) => {
    results.push(ok);
    $(".progress i:nth-child(" + (i + 1) + ")").className = ok ? "ok" : "ng";
    $("#after").innerHTML = html + `<div class="sticky-next"><button class="btn" id="next">${i + 1 < qs.length ? "次の問題へ" : "結果を見る"}</button></div>`;
    $("#next").onclick = () => {
      session.i++;
      if (session.i < qs.length) render(); else finishQuiz();
    };
  });
};

function finishQuiz() {
  const { qs, results, conf } = session;
  const correct = results.filter(Boolean).length;
  let pts = 0;
  qs.forEach((q, k) => { if (results[k]) pts += Math.round(10 * LEVEL_MUL[q.level]); });
  const perfect = correct === qs.length;
  if (perfect) pts += 50;
  addPoints(pts);
  store.update((s) => s.history.unshift({ at: Date.now(), level: conf.level, genre: conf.genre, correct, total: qs.length, points: pts }));
  session.summary = { correct, pts, perfect };
  go("#/result");
}

routes.result = async () => {
  if (!session || !session.summary) return go("#/quiz");
  const { qs, results, summary } = session, d = db();
  const by = {};
  qs.forEach((q, k) => { const g = (by[q.genre] ||= { c: 0, n: 0 }); g.n++; if (results[k]) g.c++; });
  const good = Object.entries(by).filter(([, v]) => v.c === v.n).map(([k]) => d.genres[k]);
  const bad = Object.entries(by).filter(([, v]) => v.c < v.n).sort((a, b) => a[1].c / a[1].n - b[1].c / b[1].n).map(([k]) => d.genres[k]);
  const rate = summary.correct / qs.length;
  const kind = rate >= .8 ? "quizGood" : rate >= .5 ? "quizMid" : "quizLow";
  const comment = rate >= .8
    ? "合格ラインを大きく上回るペースです。この調子で苦手ジャンルの穴を埋めていきましょう。"
    : rate >= .6
      ? "合格ライン付近の実力です。まちがえた問題の解説と出典を読み直すと、次は確実に取れるようになります。"
      : "まだ伸びしろがたっぷりあります。まずは初級（必須問題）で基本用語を固めるのがおすすめです。";
  view.innerHTML = `
    <div class="card score">
      <div class="muted">RESULT</div>
      <div class="stars">${[1, 2, 3].map((k) => `<i class="${summary.correct >= [4, 7, 10][k - 1] ? "on" : ""}">★</i>`).join("")}</div>
      <div class="big">${summary.correct}<span style="font-size:24px">/${qs.length}</span></div>
      <p style="margin:10px 0 0"><span class="reward">🦴 +${summary.pts}pt GET!</span>${summary.perfect ? '<br><span class="badge" style="margin-top:8px">全問正解ボーナス +50</span>' : ""}</p>
    </div>
    <div class="card">
      <h2 style="margin-top:0">総評</h2>
      <p>${comment}</p>
      ${good.length ? `<p>今回できたジャンル：${good.map((g) => `<span class="pill good">${h(g)}</span>`).join("")}</p>` : ""}
      ${bad.length ? `<p>見直したいジャンル：${bad.map((g) => `<span class="pill bad">${h(g)}</span>`).join("")}</p>` : ""}
      <div class="row" style="margin-top:8px"><div class="dog" id="rDog" style="width:90px;height:90px;flex:none"></div><div class="bubble" id="rBubble" style="margin:0"></div></div>
    </div>
    <div class="card">
      <h2 style="margin-top:0">ふりかえり</h2>
      ${qs.map((q, k) => `<details style="border-bottom:1px dashed var(--line);padding:6px 0"><summary>${results[k] ? "⭕" : "❌"} ${h(q.stem.slice(0, 40))}${q.stem.length > 40 ? "…" : ""}</summary>
        <p class="muted">正答：${q.answer.map((n) => `${NUM[n - 1]} ${h(q.choices[n - 1])}`).join(" / ")}</p>${renderExplanation(q)}</details>`).join("")}
    </div>
    <div class="grid2"><button class="btn" id="again">もう10問</button><button class="btn ghost" id="home">ホームへ</button></div>`;
  await renderDog($("#rDog"), { happy: rate >= .8 });
  say($("#rBubble"), kind);
  $("#again").onclick = () => startQuiz();
  $("#home").onclick = () => go("#/home");
};

// ---------- 今日のワンポイント ----------
routes.lesson = async () => {
  const d = await ensureData(); if (!d) return;
  const key = today();
  const pool = d.questions.filter((q) => q.explanation && q.explanation.lesson);
  const fallback = d.questions.filter((q) => q.explanation);
  const list = pool.length ? pool : fallback;
  if (!list.length) {
    view.innerHTML = `<h1>今日のワンポイント</h1><div class="card"><p>レッスンは準備中です。解説の照合が済んだ問題から順に追加されます。</p></div>`;
    return;
  }
  let seed = 0; for (const c of key) seed = (seed * 31 + c.charCodeAt(0)) >>> 0;
  const q = list[seed % list.length];
  const done = store.get().lessons[key];
  view.innerHTML = `<h1>💡 今日のワンポイント</h1>
    <p class="muted">${key}｜まずは1問、考えてみよう。答えたあとに詳しい解説と周辺知識が出てくるよ。</p>
    <div class="card">${questionHTML(q)}</div>`;
  bindAnswer(view, q, async (ok, html) => {
    const more = q.explanation.lesson;
    $("#after").innerHTML = html + (more ? `<div class="lessonbox"><h3>📖 もっと詳しく・周辺知識</h3>${more.map((p) => `<p>${h(p)}</p>`).join("")}</div>` : "");
    if (!done) {
      store.update((s) => { s.lessons[key] = { qid: q.id, correct: ok }; });
      addPoints(50);
      toast("今日のワンポイント クリア！ +50pt");
    }
  });
};

// ---------- ショップ ----------
routes.shop = async () => {
  const s = store.get();
  view.innerHTML = `<h1>🛍️ ショップ</h1>
    <div class="shophead"><div class="dog" id="sDog" style="width:80px;height:80px;flex:none"></div><div class="bubble" id="sBubble" style="margin:0">なにを買ってくれるの？わくわく…！</div></div>
    <p class="muted">アイテムをプレゼントすると、${h(dogName())}が成長します（EXPアップ）。</p>
    <div class="items">${(await Promise.all(ITEMS.map(async (it) => {
      const owned = s.items[it.id] || 0, soldout = it.kind === "room" && owned;
      const rar = it.price >= 4000 ? "SSR" : it.price >= 1000 ? "SR" : it.price >= 300 ? "R" : "N";
      return `<div class="item r-${rar}"><span class="rar">${rar}</span><span class="kind">${it.kind === "food" ? "おやつ" : "お部屋"}</span>
        <div class="e">${await itemVisual(it)}</div><b>${h(it.name)}</b>
        <div class="muted">${h(it.desc)}</div><div class="muted">EXP +${it.exp}</div>
        ${owned ? `<div class="owned">${it.kind === "room" ? "お部屋に飾ってあるよ" : `これまで ${owned}こ`}</div>` : ""}
        <button class="btn small" data-buy="${it.id}" ${soldout || s.points < it.price ? "disabled" : ""}>${soldout ? "GET済み" : `🦴 ${it.price.toLocaleString()}`}</button></div>`;
    }))).join("")}</div>`;
  await renderDog($("#sDog"));
  view.querySelector(".items").onclick = async (e) => {
    const b = e.target.closest("[data-buy]"); if (!b) return;
    const it = ITEMS.find((x) => x.id === b.dataset.buy);
    if (store.get().points < it.price) return;
    store.update((st) => { st.points -= it.price; st.items[it.id] = (st.items[it.id] || 0) + 1; });
    toast(it.kind === "room" ? `${it.emoji} ${it.name} をお部屋に飾ったよ！` : `${it.emoji} ${it.name} をプレゼントしました`);
    const leveled = await gainExp(it.exp);
    if (!leveled) { await routes.shop(); say($("#sBubble"), "buy"); }
    else { $("#modal").addEventListener("click", () => routes.shop(), { once: true }); }
  };
};

// ---------- 記録 ----------
routes.stats = async () => {
  const d = await ensureData(); if (!d) return;
  const s = store.get(), gs = genreStats();
  let c = 0, n = 0; Object.values(gs).forEach((v) => { c += v.c; n += v.n; });
  const rows = Object.entries(d.genres).map(([k, name]) => ({ k, name, ...(gs[k] || { c: 0, n: 0 }) }));
  const rated = rows.filter((r) => r.n >= 5).sort((a, b) => b.c / b.n - a.c / a.n);
  const strong = rated.slice(0, 3).filter((r) => r.c / r.n >= .7), weak = rated.slice(-3).reverse().filter((r) => r.c / r.n < .7);
  view.innerHTML = `<h1 id="statsTitle" data-multitap style="user-select:none;-webkit-user-select:none">📊 学習の記録</h1>
    <div class="grid2">
      <div class="card score"><div class="muted">累計回答</div><div class="big" style="font-size:40px">${n}</div></div>
      <div class="card score"><div class="muted">正答率</div><div class="big" style="font-size:40px">${n ? Math.round(c / n * 100) : 0}<span style="font-size:18px">%</span></div></div>
    </div>
    <div class="card">
      <h2 style="margin-top:0">得意・苦手</h2>
      ${rated.length ? `
        <p>得意：${strong.length ? strong.map((r) => `<span class="pill good">${h(r.name)}</span>`).join("") : '<span class="muted">まだなし</span>'}</p>
        <p>苦手：${weak.length ? weak.map((r) => `<span class="pill bad">${h(r.name)}</span>`).join("") : '<span class="muted">まだなし</span>'}</p>`
      : `<p class="muted">各ジャンル5問以上解くと、得意・苦手が表示されます。</p>`}
      <div class="bars">${rows.map((r) => {
        const p = r.n ? Math.round(r.c / r.n * 100) : 0;
        return `<div class="bar"><span>${h(r.name)}</span><div class="track"><i class="${r.n >= 5 ? (p >= 70 ? "hi" : p < 50 ? "lo" : "") : ""}" style="width:${p}%"></i></div><span class="pct">${r.n ? p + "%" : "-"}<br><span class="muted">${r.n}問</span></span></div>`;
      }).join("")}</div>
    </div>
    <div class="card"><h2 style="margin-top:0">最近のクイズ</h2>
      ${s.history.slice(0, 10).map((x) => `<div class="row" style="justify-content:space-between;border-bottom:1px dashed var(--line);padding:4px 0"><span class="muted">${new Date(x.at).toLocaleDateString("ja-JP")}</span><span>${x.correct}/${x.total}</span><span style="color:var(--accent)">+${x.points}pt</span></div>`).join("") || '<p class="muted">まだありません</p>'}
    </div>
    <div class="card"><h2 style="margin-top:0">設定</h2>
      <label class="row" style="justify-content:space-between"><span>${h(dogName())}のセリフを読み上げる</span><input type="checkbox" id="voice" ${s.settings.voice ? "checked" : ""}></label>
      <div class="grid2" style="margin-top:12px"><button class="btn ghost small" id="exp" style="width:100%">バックアップを保存</button><button class="btn ghost small" id="imp" style="width:100%">バックアップから復元</button></div>
      <button class="btn ghost small" id="partner" style="width:100%;margin-top:10px">相棒の犬・名前を変える</button>
      <button class="btn ghost small" id="guide" style="width:100%;margin-top:10px">ホーム画面への追加方法</button>
      <p class="muted" style="margin-top:12px">過去問：一般財団法人動物看護師統一認定機構が公表した問題・正答を、個人の学習目的でのみ利用しています。図や写真を使う問題は除外しています。</p>
    </div>`;
  // テスト用の隠し機能：タイトルを5回続けてタップするとポイントを追加できる
  let taps = 0, tapTimer = null;
  $("#statsTitle").onpointerup = () => {
    taps++; clearTimeout(tapTimer); tapTimer = setTimeout(() => (taps = 0), 2000);
    if (taps < 5) return;
    taps = 0;
    const n = parseInt(prompt("テスト用：追加するポイント数（減らすときはマイナス）", "1000") || "", 10);
    if (Number.isFinite(n) && n !== 0) {
      store.update((st) => { st.points = Math.max(0, st.points + n); });
      toast(`${n > 0 ? "+" : ""}${n}pt（テスト用）`);
    }
  };
  $("#voice").onchange = (e) => store.update((st) => { st.settings.voice = e.target.checked; });
  $("#guide").onclick = () => go("#/install");
  $("#partner").onclick = () => go("#/welcome");
  $("#exp").onclick = async () => {
    const blob = new Blob([store.export()], { type: "application/json" });
    const file = new File([blob], `moko-backup-${today()}.json`, { type: "application/json" });
    if (navigator.canShare && navigator.canShare({ files: [file] })) { try { await navigator.share({ files: [file] }); return; } catch { /* キャンセル */ } }
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = file.name; a.click();
  };
  $("#imp").onclick = () => {
    const inp = document.createElement("input"); inp.type = "file"; inp.accept = "application/json,.json";
    inp.onchange = async () => {
      try { store.import(await inp.files[0].text()); toast("復元しました"); render(); }
      catch { toast("ファイルを読み込めませんでした"); }
    };
    inp.click();
  };
};

// ---------- 動画・参考書 ----------
routes.videos = async () => videosView(view, { onWatched: async () => { addPoints(30); toast("動画を見終わりました +30pt"); } });
routes.books = async () => {
  let books = [];
  try { books = await (await fetch("data/books.json")).json(); } catch { /* なし */ }
  view.innerHTML = `<h1>📚 おすすめ参考書</h1>
    <p class="muted">書誌情報（書名・ISBN・発行年）は出版社の公式ページで確認したものです。リンク先で目次や立ち読みも見られます。表紙画像：各出版社の公式サイトより。</p>
    ${books.map((b) => `<div class="card book">
      ${b.cover ? `<img src="${h(b.cover)}" alt="${h(b.title)}の表紙" loading="lazy" onerror="this.outerHTML='<div class=noimg>📘</div>'">` : `<div class="noimg">📘</div>`}
      <div><b>${h(b.title)}</b><div class="muted">${h(b.author)}｜${h(b.publisher)}${b.pubdate ? `｜${h(b.pubdate)}` : ""}</div>
      ${b.isbn ? `<div class="muted">ISBN ${h(b.isbn)}</div>` : ""}
      <p style="font-size:14px;margin:6px 0">${h(b.note)}</p>
      ${b.url ? `<a href="${h(b.url)}" target="_blank" rel="noopener" style="font-size:13px">出版社ページ・書誌情報</a>` : ""}</div></div>`).join("") || '<div class="card muted">準備中です</div>'}`;
};

// ---------- 拡大の防止（ピンチ・ダブルタップ） ----------
["gesturestart", "gesturechange"].forEach((t) => document.addEventListener(t, (e) => e.preventDefault(), { passive: false }));
document.addEventListener("touchmove", (e) => { if (e.touches.length > 1) e.preventDefault(); }, { passive: false });
let lastTouch = 0;
document.addEventListener("touchend", (e) => {
  const now = Date.now();
  if (now - lastTouch < 300 && !e.target.closest("input, textarea, select, [data-multitap]")) e.preventDefault();
  lastTouch = now;
}, { passive: false });

// ---------- 起動 ----------
refreshTop();
render();
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
