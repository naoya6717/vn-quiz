// ショップのアイテム。プレゼントすると相棒が成長（EXP）し、家具・おもちゃは部屋に飾られる。
// kind: food=食べ物（何度でも買える・部屋には置かない） / room=部屋に置く（1回だけ）
// place: 部屋の中の位置（部屋の幅・高さに対する％）。x=左端からの中心位置、y=床からの高さ（bottom）または top、w=幅、z=重なり順
// look: 画像ではなく部屋の見た目そのものを変えるアイテム（ラグ・カーテン・壁紙）
export const ITEMS = [
  { id: "boro", emoji: "🍪", kind: "food", name: "たまごボーロ", price: 30, exp: 10, img: "boro", desc: "小さなごほうび" },
  { id: "jerky", emoji: "🍖", kind: "food", name: "ささみジャーキー", price: 80, exp: 30, img: "jerky", desc: "みんなの大好物" },
  { id: "bowl", emoji: "🥣", kind: "room", name: "ごはん皿セット", price: 120, exp: 50, img: "bowl", desc: "まずはここから", place: { x: 84, bottom: 3, w: 22, z: 6 } },
  { id: "ball", emoji: "🎾", kind: "room", name: "テニスボール", price: 200, exp: 80, img: "ball", desc: "おさんぽのおとも", place: { x: 33, bottom: 4, w: 10, z: 7 } },
  { id: "cushion", emoji: "🛋️", kind: "room", name: "ミニソファ", price: 320, exp: 130, img: "cushion", desc: "お昼寝スポット", place: { x: 15, bottom: 6, w: 26, z: 5 } },
  { id: "plant", emoji: "🪴", kind: "room", name: "観葉植物", price: 450, exp: 180, img: "plant", desc: "お部屋に緑を", place: { x: 92, bottom: 34, w: 15, z: 2 } },
  { id: "clock", emoji: "🕰️", kind: "room", name: "かべかけ時計", price: 600, exp: 240, img: "clock", desc: "勉強時間を見守る", place: { x: 80, top: 7, w: 14, z: 1 } },
  { id: "shelf", emoji: "📚", kind: "room", name: "参考書の本棚", price: 800, exp: 320, img: "shelf", desc: "知識がつまってる", place: { x: 12, bottom: 33, w: 22, z: 2 } },
  { id: "rug", emoji: "🟣", kind: "room", name: "まるいラグ", price: 1000, exp: 400, look: "rug", desc: "床がふかふかに" },
  { id: "cake", emoji: "🎂", kind: "food", name: "わんこケーキ", price: 1200, exp: 520, img: "cake", desc: "とくべつな日に" },
  { id: "curtain", emoji: "🪟", kind: "room", name: "レースのカーテン", price: 1400, exp: 560, look: "curtain", desc: "窓がおしゃれに" },
  { id: "wallpaper", emoji: "✨", kind: "room", name: "星柄の壁紙", price: 1800, exp: 720, look: "wallpaper", desc: "お部屋がきらきら" },
  { id: "bed", emoji: "🛏️", kind: "room", name: "ふかふかベッド", price: 2500, exp: 1000, img: "bed", desc: "王さまの寝ごこち", place: { x: 70, bottom: 30, w: 30, z: 3 } },
  { id: "chandelier", emoji: "💡", kind: "room", name: "おしゃれなライト", price: 4000, exp: 1700, img: "chandelier", desc: "お部屋をあかるく", place: { x: 50, top: -3, w: 22, z: 1 } },
  { id: "trophy", emoji: "🏆", kind: "room", name: "合格トロフィー", price: 6000, exp: 3000, img: "trophy", desc: "がんばりの証", place: { x: 12, bottom: 55, w: 11, z: 3 } },
];
export const itemImg = (it) => `data/items/${it.img}.png`;

// 画像（data/items/<img>.png）があれば画像、無ければ絵文字で表示する
const imgOk = {};
export async function hasItemImg(it) {
  if (!it.img) return false;
  if (!(it.img in imgOk)) {
    try { imgOk[it.img] = (await fetch(itemImg(it), { method: "HEAD" })).ok; } catch { imgOk[it.img] = false; }
  }
  return imgOk[it.img];
}
export async function itemVisual(it, cls = "") {
  return (await hasItemImg(it)) ? `<img class="${cls}" src="${itemImg(it)}" alt="${it.name}">` : `<span class="emo ${cls}">${it.emoji}</span>`;
}
