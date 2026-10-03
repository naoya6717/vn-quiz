// 学習データ・ポイント・犬の成長をこの端末の localStorage に保存する。
const KEY = "vnq:v1";

const blank = () => ({
  points: 0,
  exp: 0,
  items: {},          // itemId -> 個数
  answers: {},        // qid -> { c: 正解数, w: 不正解数, last: 最後の結果(1/0), at }
  history: [],        // { at, level, genre, correct, total, points }
  videos: {},         // videoId -> { state: "watching"|"done", t: 秒, dur: 秒, at }
  lessons: {},        // "YYYY-MM-DD" -> { qid, correct }
  settings: { voice: false },
  dog: null,          // { breed, name } 最初に選ぶ相棒
  seenIntro: false,
  createdAt: Date.now(),
});

let state;
try { state = Object.assign(blank(), JSON.parse(localStorage.getItem(KEY) || "{}")); }
catch { state = blank(); }

const listeners = new Set();
export const store = {
  get: () => state,
  save() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch { /* 容量超過などは無視 */ }
    listeners.forEach((fn) => fn(state));
  },
  update(fn) { fn(state); store.save(); },
  onChange(fn) { listeners.add(fn); },
  export: () => JSON.stringify(state),
  import(json) { state = Object.assign(blank(), JSON.parse(json)); store.save(); },
  reset() { state = blank(); store.save(); },
};

export const today = (d = new Date()) => {
  const z = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
};

export function addPoints(n) {
  store.update((s) => { s.points += n; });
}
