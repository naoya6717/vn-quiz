// 暗号化された過去問データを合言葉で復号する。合言葉はこの端末にだけ保存する。
const PASS_KEY = "vnq:pass";
let cache = null;

const unb64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));

async function decrypt(blob, pass) {
  const base = await crypto.subtle.importKey("raw", new TextEncoder().encode(pass), "PBKDF2", false, ["deriveKey"]);
  const key = await crypto.subtle.deriveKey(
    { name: "PBKDF2", salt: unb64(blob.salt), iterations: 200000, hash: "SHA-256" }, base,
    { name: "AES-GCM", length: 256 }, false, ["decrypt"]);
  const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(blob.iv) }, key, unb64(blob.ct));
  return JSON.parse(new TextDecoder().decode(plain));
}

export const savedPass = () => { try { return localStorage.getItem(PASS_KEY); } catch { return null; } };

export async function unlock(pass) {
  const blob = await (await fetch("data/questions.enc", { cache: "no-cache" })).json();
  const data = await decrypt(blob, pass); // 合言葉が違うとここで例外
  try { localStorage.setItem(PASS_KEY, pass); } catch { /* 保存できなくても今回は使える */ }
  cache = data;
  cache.byId = Object.fromEntries(data.questions.map((q) => [q.id, q]));
  return cache;
}

export const db = () => cache;
