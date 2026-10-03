// 相棒の犬（犬種・名前はユーザーが最初に決める）の表示・成長・セリフ。
import { store } from "./store.js";

// 選べる犬種。画像は data/dog/<id>/stageN(_happy).png
export const BREEDS = [
  { id: "poodle", name: "トイプードル", desc: "ふわふわ巻き毛の甘えんぼ" },
  { id: "shiba", name: "柴犬", desc: "まっすぐ一途ながんばり屋" },
  { id: "pome", name: "ポメラニアン", desc: "もふもふ元気なムードメーカー" },
  { id: "dachs", name: "ミニチュアダックス", desc: "好奇心いっぱいの探検家" },
];
export const breedOf = () => BREEDS.find((b) => b.id === store.get().dog?.breed) || BREEDS[0];
export const dogName = () => store.get().dog?.name || "もこ";

// 成長段階。画像があればそれを使い、無ければ内蔵SVGで描く。
export const STAGES = [
  { from: 1, title: "こいぬの", img: "stage1", scale: 0.72 },
  { from: 5, title: "わんぱく", img: "stage2", scale: 0.82 },
  { from: 10, title: "がんばり", img: "stage3", scale: 0.9 },
  { from: 15, title: "りっぱな", img: "stage4", scale: 0.96 },
  { from: 25, title: "レジェンド", img: "stage5", scale: 1 },
];
export const stageName = (st) => `${st.title}${dogName()}`;

// レベルnに上がるのに必要な累計EXP
const need = (lv) => 40 * (lv - 1) * lv / 2 + 10 * (lv - 1);
export function levelInfo(exp = store.get().exp) {
  let lv = 1;
  while (exp >= need(lv + 1)) lv++;
  const cur = need(lv), nxt = need(lv + 1);
  return { lv, pct: Math.round(((exp - cur) / (nxt - cur)) * 100), toNext: nxt - exp };
}
const stageOfRaw = (lv) => [...STAGES].reverse().find((s) => lv >= s.from);
export const stageOf = (lv) => { const st = stageOfRaw(lv); return { ...st, name: stageName(st) }; };

const imgCache = {};
async function hasImg(name) {
  if (name in imgCache) return imgCache[name];
  try { imgCache[name] = (await fetch(`data/dog/${name}.png`, { method: "HEAD" })).ok; } // name は "<breed>/stageN"
  catch { imgCache[name] = false; }
  return imgCache[name];
}

export function dogSVG(happy = false, scale = 1) {
  const curl = (cx, cy, r) => `<circle cx="${cx}" cy="${cy}" r="${r}"/>`;
  const fluff = (pts, r) => pts.map(([x, y]) => curl(x, y, r)).join("");
  const eyes = happy
    ? `<path d="M84 104 q8 -9 16 0" /><path d="M140 104 q8 -9 16 0" />`
    : `<ellipse cx="92" cy="104" rx="7" ry="8" fill="#2b1a12" stroke="none"/><ellipse cx="148" cy="104" rx="7" ry="8" fill="#2b1a12" stroke="none"/>
       <circle cx="94.5" cy="101" r="2.4" fill="#fff" stroke="none"/><circle cx="150.5" cy="101" r="2.4" fill="#fff" stroke="none"/>`;
  const mouth = happy
    ? `<path d="M108 132 q12 18 24 0 z" fill="#e2706a" stroke="#5a3324"/>`
    : `<path d="M110 132 q10 8 20 0" />`;
  return `<svg viewBox="0 0 240 240" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="相棒の犬">
  <g transform="translate(120 130) scale(${scale}) translate(-120 -130)">
    <ellipse cx="120" cy="226" rx="70" ry="9" fill="#000" opacity=".08"/>
    <g fill="#c98a5a">${fluff([[70, 190], [92, 200], [120, 204], [148, 200], [170, 190], [80, 168], [160, 168], [120, 176]], 24)}</g>
    <g fill="#c98a5a">${fluff([[82, 214], [104, 216], [136, 216], [158, 214]], 14)}</g>
    <g fill="#b97a4c">${fluff([[44, 98], [40, 122], [46, 146], [196, 98], [200, 122], [194, 146]], 19)}</g>
    <g fill="#d39463">${fluff([[120, 52], [94, 58], [146, 58], [76, 78], [164, 78], [72, 104], [168, 104], [80, 128], [160, 128], [100, 140], [140, 140], [120, 80]], 26)}</g>
    <g fill="#e0a578">${fluff([[104, 44], [136, 44], [120, 36]], 16)}</g>
    <ellipse cx="120" cy="124" rx="24" ry="18" fill="#e6b58c"/>
    <ellipse cx="120" cy="117" rx="9" ry="7" fill="#3a2418"/>
    <g fill="none" stroke="#5a3324" stroke-width="3" stroke-linecap="round">${eyes}${mouth}</g>
    <ellipse cx="74" cy="122" rx="10" ry="6" fill="#f2a0a0" opacity=".55"/>
    <ellipse cx="166" cy="122" rx="10" ry="6" fill="#f2a0a0" opacity=".55"/>
    ${happy ? `<g fill="#ef6f86"><path d="M196 52 c-6 -10 -20 -2 -10 10 l10 9 l10 -9 c10 -12 -4 -20 -10 -10z"/><path d="M38 60 c-4 -7 -14 -1 -7 7 l7 6 l7 -6 c7 -8 -3 -14 -7 -7z"/></g>` : ""}
  </g></svg>`;
}

export async function renderDog(el, { happy = false, breed = breedOf().id, stage } = {}) {
  const st = stage || stageOf(levelInfo().lv);
  const name = `${breed}/${happy ? `${st.img}_happy` : st.img}`;
  const inner = (await hasImg(name))
    ? `<div style="width:100%;height:100%;transform:scale(${st.scale});transform-origin:50% 100%"><img src="data/dog/${name}.png" alt="${st.name}"></div>`
    : dogSVG(happy, st.scale);
  el.innerHTML = inner;
}

// ---------- セリフ ----------
const LINES = {
  morning: ["おはよう！朝の1問は頭がすっきりするよ☀️", "朝ごはん食べた？ぼくはもう食べたよ🐶"],
  day: ["今日もいっしょにがんばろうね！", "ちょっとずつでも、毎日やるのがいちばん強いんだよ"],
  evening: ["おつかれさま！今日もよくがんばったね", "夜ごはんのあとに10問だけ、どう？"],
  late: ["もう遅いよ…今日はここまでにして、ゆっくり休もう？🌙", "睡眠も勉強のうちだよ。おやすみの前に深呼吸しよっか"],
  tap: ["くすぐったいよ〜！", "なでなでありがとう♪", "わん！（応援してるよ！）", "つかれたら、ぼくをなでて休憩してね", "きみならきっと合格できる！", "まちがえた問題こそ、伸びしろだよ✨", "水分補給もわすれずにね💧", "がんばりすぎてない？肩の力ぬいていこう"],
  quizGood: ["すごい！ほとんど正解！天才かも…！", "その調子！ぼくも誇らしいよ✨"],
  quizMid: ["いい感じ！まちがえたところは解説をもう一回見てみよう", "半分以上正解！確実に力がついてるよ"],
  quizLow: ["今日はむずかしかったね。でも挑戦したきみはえらい！", "大丈夫、まちがえた分だけ覚えられるよ。いっしょに復習しよ"],
  lesson: ["今日のワンポイント、おわったね！えらい！"],
  video: ["動画おつかれさま！見るだけでも記憶に残るよ"],
  buy: ["わーい！ありがとう！大事にするね", "うれしい！しっぽが止まらないよ〜"],
  levelup: ["レベルアップしたよ！きみのおかげだよ、ありがとう！"],
};
export function pickLine(kind) {
  let k = kind;
  if (!k) {
    const h = new Date().getHours();
    k = h >= 23 || h < 4 ? "late" : h < 10 ? "morning" : h < 17 ? "day" : "evening";
  }
  const arr = LINES[k] || LINES.tap;
  return arr[Math.floor(Math.random() * arr.length)];
}

export function speak(text) {
  if (!store.get().settings.voice || !("speechSynthesis" in window)) return;
  try {
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text.replace(/[\p{Extended_Pictographic}]/gu, ""));
    u.lang = "ja-JP"; u.pitch = 1.6; u.rate = 1.05;
    speechSynthesis.speak(u);
  } catch { /* 読み上げ非対応 */ }
}

export function say(bubbleEl, kind, text) {
  const t = text || pickLine(kind);
  bubbleEl.textContent = "";
  let i = 0;
  const tick = () => { bubbleEl.textContent = t.slice(0, ++i); if (i < t.length) setTimeout(tick, 28); };
  tick();
  speak(t);
}
