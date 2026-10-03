// オフラインでも開けるように、アプリ本体とデータをキャッシュする（ネットワーク優先）。
const CACHE = "moko-v3";
const CORE = ["./", "index.html", "style.css", "manifest.webmanifest", "js/main.js", "js/ui.js", "js/store.js", "js/data.js", "js/dog.js", "js/items.js", "js/videos.js", "data/questions.enc", "data/videos.json", "data/books.json", "icons/icon-192.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE).catch(() => {})).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  e.respondWith(
    fetch(e.request).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); }
      return res;
    }).catch(() => caches.match(e.request, { ignoreSearch: true }))
  );
});
