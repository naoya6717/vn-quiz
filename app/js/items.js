// ショップのアイテム。once=1つだけ買える、wear=もこが身につける（表示位置のCSS）
export const ITEMS = [
  { id: "boro", emoji: "🍪", name: "たまごボーロ", price: 30, exp: 10, desc: "小さなごほうび" },
  { id: "jerky", emoji: "🍖", name: "ささみジャーキー", price: 80, exp: 30, desc: "もこの大好物" },
  { id: "gum", emoji: "🦴", name: "ミルクガム", price: 150, exp: 60, desc: "かみかみで歯もすっきり" },
  { id: "ball", emoji: "🎾", name: "テニスボール", price: 250, exp: 100, once: true, desc: "おさんぽのおとも" },
  { id: "rope", emoji: "🪢", name: "ロープのおもちゃ", price: 350, exp: 140, once: true, desc: "ひっぱりっこしよう" },
  { id: "ribbon", emoji: "🎀", name: "リボン", price: 500, exp: 200, once: true, wear: "left:58%;top:2%;transform:rotate(18deg)", desc: "頭にちょこんとつけるよ" },
  { id: "bed", emoji: "🛏️", name: "ふわふわベッド", price: 700, exp: 280, once: true, desc: "よく寝てよく育つ" },
  { id: "scarf", emoji: "🧣", name: "マフラー", price: 900, exp: 360, once: true, wear: "left:38%;top:58%", desc: "冬もぬくぬく" },
  { id: "cake", emoji: "🎂", name: "わんこケーキ", price: 1200, exp: 520, desc: "とくべつな日に" },
  { id: "glasses", emoji: "👓", name: "はかせメガネ", price: 1500, exp: 650, once: true, wear: "left:36%;top:34%", desc: "かしこさアップ（気分）" },
  { id: "cap", emoji: "🎓", name: "合格ぼうし", price: 3000, exp: 1400, once: true, wear: "left:34%;top:-6%", desc: "合格への願いをこめて" },
  { id: "crown", emoji: "👑", name: "王冠", price: 6000, exp: 3000, once: true, wear: "left:36%;top:-8%", desc: "がんばりの証" },
];
