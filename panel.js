// Dev Studio's right block, round 15 (Concepts/html/editors-concepts/r15/r15-dev.html, owner 2026-10-09: «Да, неплохо, делай. Только я бы
// еще добавил режим редактирования HTML ... как в браузере в инспекторе можно редактировать ... Может быть, переключать туда-сюда»).
//
// The header is a block header of the app (Hyimg ui/hy/block.css, round 12 «A · Line», standard 24 px tabs): Inspector | History with the
// count of this session's writes, and at its right end Edit, a mini toggle (E) between Inspect, the studio as it was, and Edit, the HTML
// edited as in a browser's inspector (treeedit.js). Under it the picked element: its tag on a tile of the studio's green, the crumbs of
// its parents (a click picks one), its size, and a 6 px status LED of the file: steady green when this session wrote to it, blinking while
// a write is on its way, a ring before the first write and when this element or the file can't be saved (its title says which). History
// lists the writes of this session, the undone ones quiet; a click on one takes the file to the state right after it (one ⌘Z or ⇧⌘Z a
// step), «Opened» to the file as Dev Studio found it.
//
// The mini toggle and the LED are Hyimg's micro primitives (review/ui/hy: <hy-minitoggle>, <hy-led>; round 15's micro sheet
// r15/r15-micro.html, owner 2026-10-09: «Все топ, все делай»): their look is the app's, the Studio's green comes from --hy-sel on .dvui.
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// an element's short name: its tag and its id, else its first class (section.hero, h1#title)
export const nameOf = n => { if (!n) return ""; const c = Array.isArray(n.c) ? n.c[0] : String(n.c || "").split(" ")[0]; return n.t + (n.d ? "#" + n.d : c ? "." + c : ""); };

// the timeline History shows: the writes made, oldest first, then the ones undone (future is a stack, its top the next ⇧⌘Z)
export const timeline = D => [...D.past.map(s => ({ s, on: true })), ...[...D.future].reverse().map(s => ({ s, on: false }))];
// the steps to the state right after entry j of the timeline (-1: the file as the session opened it): negative undoes, positive redoes
export const stepsTo = (D, j) => (j + 1) - D.past.length;

// the file's LED, as markup: led() sets its state and its words
export const LED = `<hy-led class="dvled" state="off"></hy-led>`;

export function makePanel({ D, t, svg, EDITS, select, setEdit }) {
  const head = () => `<div class="hy-bh"><span class="dvtabs" role="tablist" aria-label="${esc(t("Inspector"))}">`
    + `<button class="hy-bh-tab on" role="tab" aria-selected="true" data-tab="insp">${svg("properties", 14)}${esc(t("Inspector"))}</button>`
    + `<button class="hy-bh-tab" role="tab" aria-selected="false" data-tab="hist">${svg("history", 14)}${esc(t("History"))}<em class="dvhn"></em></button></span>`
    + `<span class="hy-bh-sp"></span><hy-minitoggle class="dvmt" data-edit title="${esc(t("Edit the HTML, as in a browser's inspector · E"))}">`
    + `${esc(t("Edit"))}</hy-minitoggle></div>`;

  function wire(right) {
    right.querySelector(".dvtabs").addEventListener("click", e => { const b = e.target.closest("[data-tab]"); if (b) tab(b.dataset.tab); });
    right.querySelector("[data-edit]").addEventListener("hy-change", e => { const d = D(); if (d) setEdit(!!e.detail.checked); });
    right.querySelector(".dvhl").addEventListener("click", e => { const r = e.target.closest("[data-j]"); if (r) go(+r.dataset.j); });
    right.querySelector(".ih").addEventListener("click", e => { const c = e.target.closest("[data-up]"); if (c) select(+c.dataset.up, true); });
  }
  function tab(name) {
    const d = D(); if (!d) return; d.tab = name === "hist" ? "hist" : "insp";
    const r = d.ui.right;
    r.querySelectorAll("[data-tab]").forEach(b => { const on = b.dataset.tab === d.tab; b.classList.toggle("on", on); b.setAttribute("aria-selected", String(on)); });
    r.classList.toggle("hist", d.tab === "hist");
    if (d.tab === "hist") history();
  }
  // the toggle and the History count follow the session
  function sync() {
    const d = D(); if (!d) return;
    const r = d.ui.right, m = r.querySelector("[data-edit]");
    m.toggleAttribute("checked", !!d.edit);
    r.querySelector(".dvhn").textContent = d.past.length ? String(d.past.length) : "";
    d.ui.root.classList.toggle("dvedit-on", !!d.edit);
    led(); if (d.tab === "hist") history();
  }
  // the picked element: tag, the crumbs of its two nearest parents (a click picks one), its size; the LED of the file at the right end
  function crumb(det, n, byId) {
    const tile = `<span class="dvth">${svg("code", 14)}</span>`;
    if (!det) return "";
    let q;
    if (n > 1) q = esc(t("{n} elements", { n }));
    else {
      const up = (det.path || []).slice(-2, -1).map(i => byId(i)).filter(Boolean);   // its parent, as round 15 draws it
      q = up.map(u => `<button class="dvup" data-up="${u.i}" title="${esc(t("Select {el}", { el: nameOf(u) }))}">${esc(nameOf(u))}</button><span class="dvsep">›</span>`).join("")
        + `<span class="dvme">${esc(nameOf({ t: det.t, d: det.d, c: det.c }))}</span><span class="dvsz">· ${Math.round(det.box.w)} × ${Math.round(det.box.h)}</span>`;
    }
    return `${tile}<div><b>${esc(det.t)}</b><span class="dvq">${q}</span></div>${LED}`;
  }
  // the LED (<hy-led>): busy blinks, written steady in the Studio's green, nothing written yet or can't be saved a ring; data-s keeps
  // which of the four it is (idle, busy, on, off) and its title says it
  function led() {
    const d = D(), l = d && d.ui.right.querySelector(".dvled"); if (!l) return;
    const off = d.ledOff || "", st = EDITS.busy() ? "busy" : d.saveErr ? "err" : off ? "off" : d.past.length ? "on" : "idle";   // err: a write refused (S-39)
    if (l.dataset.s !== st) { l.dataset.s = st; l.setAttribute("state", st === "idle" ? "off" : st); }
    const tip = st === "busy" ? t("Writing to the file…") : st === "err" ? t("Not saved: {why}", { why: d.saveErr }) : st === "off" ? off : st === "on" ? t("Written to the file")
      : t("Edits go into the file as you make them");
    if (l.title !== tip) l.title = tip;
  }
  const KIND = { style: "properties", text: "editText", attrs: "tag", tag: "rename", remove: "trash", var: "palette" };
  // a style's step named as the inspector names its control, not by its CSS property (P4 S-59: «border-radius» where it says «Corners»)
  const NAMES = { width: "W", height: "H", padding: "Padding", gap: "Gap", opacity: "Opacity", "border-radius": "Corners", filter: "Blur", "background-color": "Fill",
    color: "Colour", "font-size": "Text size", "font-weight": "Weight", "border-color": "Stroke", "border-width": "Stroke width" };
  const whatOf = L => (L.k === "style" && NAMES[L.what] ? (NAMES[L.what].length > 1 ? t(NAMES[L.what]) : NAMES[L.what]) : L.what) || t("Edit");
  function history() {
    const d = D(); if (!d) return;
    const box = d.ui.right.querySelector(".dvhl"), list = timeline(d);
    const when = s => { const x = new Date(s.at || Date.now()); return `${String(x.getHours()).padStart(2, "0")}:${String(x.getMinutes()).padStart(2, "0")}`; };
    const row = (j, ic, what, el, v, on, time) => `<button class="dvhr${on ? "" : " undone"}${j === d.past.length - 1 ? " cur" : ""}" data-j="${j}">`
      + `<span class="dvh-i">${svg(ic, 14)}</span><span class="dvh-w">${esc(what)}</span>${el ? `<span class="dvh-e">${esc(el)}</span>` : ""}`
      + `${v ? `<span class="dvh-v">${esc(v)}</span>` : ""}<span class="dvh-t">${esc(time)}</span></button>`;
    box.innerHTML = row(-1, "doc", t("Opened"), "", "", true, when({ at: d.opened }))
      + list.map(({ s, on }, j) => { const L = s.label || {}; return row(j, KIND[L.k] || "undo", whatOf(L), L.el || "", L.v || "", on, when(s)); }).join("")
      + (list.length ? "" : `<p class="hy-hint dhint">${t("<b>Edits</b> of this session show here, a click goes back to one")}</p>`);
  }
  // a click on History: the file to the state right after that write, one undo or redo a step (edits.js queues them)
  function go(j) {
    const d = D(); if (!d) return;
    const n = stepsTo(d, j);
    for (let k = 0; k < Math.abs(n); k++) (n < 0 ? EDITS.undo : EDITS.redo)();
  }
  return { head, wire, tab, sync, crumb, led, history };
}

export const CSS_PANEL = `
  .dvr .dvtabs { display: contents; }
  .dvr .dvtabs .hy-bh-tab em { margin-left: 0; }
  .dvr .dvtabs .hy-bh-tab em:empty { display: none; }
  /* the picked element (r15 .ph): a 30 px tile in the studio's green, its tag, the crumbs and the size under it, the LED at the end */
  .dvr .ih { display: flex; align-items: center; gap: 10px; min-height: 46px; box-sizing: border-box; padding: 4px 14px 8px;
    background: var(--hy-blk); }
  .dvr .ih:empty { display: none; }
  .dvr .ih .dvth { width: 30px; height: 30px; flex: none; display: grid; place-items: center; border-radius: 7px; color: var(--dev); background: color-mix(in srgb, var(--dev) 16%, var(--hy-blk)); }
  .dvr .ih > div { display: flex; flex-direction: column; gap: 1px; min-width: 0; flex: 1; }
  .dvr .ih b { font: 600 13px var(--sans, system-ui); color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .dvr .ih .dvq { display: flex; align-items: baseline; min-width: 0; color: var(--muted); font: 400 11.5px var(--sans, system-ui); white-space: nowrap; overflow: hidden; }
  .dvr .ih .dvq > * { flex: none; } .dvr .ih .dvq .dvme { flex: 0 1 auto; overflow: hidden; text-overflow: ellipsis; }
  .dvr .ih .dvup { border: 0; padding: 0; background: none; color: var(--muted); font: inherit; cursor: pointer; } .dvr .ih .dvup:hover { color: var(--ink); }
  .dvr .ih .dvsep { margin: 0 4px; } .dvr .ih .dvsz { margin-left: 4px; }
  .dvr .dvhl { display: none; padding: 2px 8px 16px; }
  .dvr.hist .dvhl { display: block; } .dvr.hist > .ih, .dvr.hist > .inf { display: none; }
  .dvr .dvhr { box-sizing: border-box; display: flex; align-items: center; gap: 8px; width: 100%; height: var(--hy-trow-h, 28px); padding: 0 8px 0 6px; border: 0;
    border-radius: var(--hy-trow-r, 8px); background: none; color: var(--ink); font: 400 12px var(--sans, system-ui); text-align: left; cursor: pointer; white-space: nowrap; }
  .dvr .dvhr:hover { background: var(--hy-trow-hover, var(--raise)); }
  .dvr .dvhr.cur { background: var(--hy-trow-on); box-shadow: var(--hy-trow-ring); }
  .dvr .dvhr.undone { color: var(--muted); } .dvr .dvhr.undone .dvh-i { opacity: .55; }
  .dvr .dvhr .dvh-i { display: grid; place-items: center; width: 16px; flex: none; color: var(--sub); }
  .dvr .dvhr .dvh-w { flex: none; } .dvr .dvhr .dvh-e { flex: none; color: var(--sub); font: 400 11.5px ui-monospace, "SF Mono", Menlo, monospace; }
  .dvr .dvhr .dvh-v { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; color: var(--muted); font: 400 11.5px ui-monospace, "SF Mono", Menlo, monospace; }
  .dvr .dvhr .dvh-t { margin-left: auto; flex: none; color: var(--muted); font: 400 11px var(--sans, system-ui); font-variant-numeric: tabular-nums; }`;
