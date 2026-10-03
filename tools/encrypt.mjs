// private/questions.json を合言葉で AES-GCM 暗号化して app/data/questions.enc に出力する。
// 合言葉は private/passphrase.txt（git管理外）。公開リポジトリには暗号文だけが載る。
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { webcrypto as crypto } from "node:crypto";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const passFile = root + "private/passphrase.txt";
if (!existsSync(passFile)) {
  const words = crypto.getRandomValues(new Uint8Array(10));
  const kana = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわ";
  writeFileSync(passFile, Array.from(words, (b) => kana[b % kana.length]).join("") + "\n");
}
const pass = readFileSync(passFile, "utf8").trim();
const plain = readFileSync(root + "private/questions.json");

const salt = crypto.getRandomValues(new Uint8Array(16));
const iv = crypto.getRandomValues(new Uint8Array(12));
const base = await crypto.subtle.importKey("raw", new TextEncoder().encode(pass), "PBKDF2", false, ["deriveKey"]);
const key = await crypto.subtle.deriveKey(
  { name: "PBKDF2", salt, iterations: 200000, hash: "SHA-256" }, base,
  { name: "AES-GCM", length: 256 }, false, ["encrypt"]);
const ct = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, plain));
const b64 = (u) => Buffer.from(u).toString("base64");
writeFileSync(root + "app/data/questions.enc", JSON.stringify({ v: 1, salt: b64(salt), iv: b64(iv), ct: b64(ct) }));
// 合言葉の入力を省くため、アプリが自動で使う鍵ファイルも書き出す（ユーザー判断で合言葉入力を廃止）
writeFileSync(root + "app/data/k.txt", pass);
console.log(`encrypted ${plain.length} bytes → app/data/questions.enc (+ app/data/k.txt)`);
