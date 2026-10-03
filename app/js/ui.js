const $ = (s, el = document) => el.querySelector(s);
export const h = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// ---------- 共通UI ----------
export function toast(msg) {
  const t = $("#toast");
  t.textContent = msg; t.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), 2200);
}
export function modal(html, { onClose } = {}) {
  const m = $("#modal");
  m.innerHTML = `<div class="sheet">${html}</div>`;
  m.hidden = false;
  const close = () => { m.hidden = true; m.innerHTML = ""; onClose && onClose(); };
  m.onclick = (e) => { if (e.target === m || e.target.closest("[data-close]")) close(); };
  return { el: m.firstElementChild, close };
}
