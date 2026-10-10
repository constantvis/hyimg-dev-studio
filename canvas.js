// Hyimg Dev studio (owner 2026-10-06: «in the bottom menu a toggle like in Figma: Board, Image, Dev, 3D»; «Dev mode is for HTML, and on
// the left we'll have the HTML tree»; «dev studio and html are a plugin too»). Two things on the board:
//
// An HTML card. An .html or .htm file of the library (manifest "kinds": the server lists them as kind "html", its picture is the page's
// first screen drawn by Chromium, server.py) dropped from the library becomes {type: "html", src: <library path>, vw: 1280, x, y, w, h,
// pics: [src]}: vw is the page's width in css px, its height follows the card's shape. At rest the card shows that picture, as sharp as
// its size on screen needs; big on screen (from 360 px wide, gone under 280, at most 4 at a time, the cards nearest the centre of the view,
// never while the board moves: HY's view hook, cards.js) the page itself runs in the card, in <iframe sandbox="allow-scripts"> without
// allow-same-origin, served by Hyimg's /sandbox/<key>/ route, so it never reaches the app. Measured 2026-10-06 (tests/test_dev_studio.py
// perf): see README.
//
// Dev mode, the board's «Dev» mode (HY.mode), entered by a double click or the switch on one selected HTML card (the frames plugin's HTML
// frame too, when it is not live). It stays on the same canvas (as the 3D studio and the frame editor do): the card turns live in place
// and the camera brings it between two panels. Left, the page's DOM tree: the library's folder tree and the 3D outline's rows, chevrons and
// guides, the library's «Find folder» field on top. Right, the inspector of the picked element: tag, id, classes, its box, a few computed
// styles, its attributes. The page carries the plugin's inspector (agent.js, put first in its <head> by the server): hovering a row marks
// the element in the page. The page opens live, its buttons take the clicks (owner 2026-10-08: «по дефолту не очень удобно, что выбран
// Select: я, может быть, хочу покликать»); the select tool («Select» in the dock, or I) makes a click in the page select its element, ⇧
// adds one, a double click types a text in place. Dev mode opens without it every time, nothing is remembered per card. Done, Esc or
// Board in the switch leave it; the camera goes back. The board's host lifts the card while the mode is open (Hyimg ui/editlift.js).
//
// Editing (0.2, owner 2026-10-07: «Почему мы используем картинки, а не реальный HTML? ... Чтобы я как в Figma мог работать с нашими
// HTML-файлами»): the inspector's controls (inspect.js) change the selected elements' style attribute or the custom property behind a value,
// a double click (or Enter) on a text types it in place; each change shows in the page at once and is written into the file a moment
// later, in place, one step of Dev mode's ⌘Z and ⇧⌘Z (edits.js, the plugin's server routes). The file's first write in a session keeps
// a copy of it in the board's history. An element the file has not got (made by a script) is selectable but its controls are grey.
//
// Round 15 (r15/r15-dev.html, owner 2026-10-09: «Да, неплохо, делай. Только я бы еще добавил режим редактирования HTML»): the right block
// has the tabs Inspector | History and the picked element's crumbs (panel.js), and Edit mode, the mini toggle in its header or E: the
// HTML edited as in a browser's inspector, in the tree, the inspector's attributes and the page (treeedit.js).
import { translator } from "./lang.js";
import { makeEdits } from "./edits.js";
import { drawEdit, wire, why, CSS_EDIT } from "./inspect.js";
import { makeCards, TYPE } from "./cards.js";
import { makeTreeComments } from "./treecomments.js";
import { makePanel, CSS_PANEL, LED } from "./panel.js";
import { makeTreeEdit, CSS_TREEEDIT } from "./treeedit.js"; import { studioDock } from "./dock.js";   // Hyimg's one dock: step names, Actions (2026-10-10)

const FRAME_TYPE = "htmlframe";   // the frames plugin's HTML frame, a library page as well
const VW = 1280, VH = 800, ROWS = 3000;
const PLUGIN = (new URL(import.meta.url).pathname.match(/\/plugins\/([^/]+)\//) || [])[1] || "dev";
const enc = encodeURIComponent, pathUrl = p => p.split("/").map(enc).join("/");
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
// the studio's icons are the app's (ui/icons.js hyIcon, owner 2026-10-07: «одно значение, одна иконка»): a page's code, picking an element
// (the select arrow, the same as the editors' Select), an element, search
const svg = (n, s = 16, cls = "") => hyIcon(n, s, 1.85, cls);
const IC = { code: "code", pick: "select", tag: "tag", find: "search" };   // hy-icon-names
const CHEV = () => window.HY_CHEV;
let HY, t = k => k, D = null, EDITS = null, C = null, TC = null, PN = null, TE = null;   // C: the cards at rest, their stills and live pages (cards.js)
const cardEl = id => document.querySelector(`.plg[data-id="${CSS.escape(id)}"]`);
const vwOf = it => it.vw || VW;
const vhOf = it => Math.max(1, Math.round(vwOf(it) * it.h / it.w));
const isPage = it => !!it && (it.type === TYPE || (it.type === FRAME_TYPE && typeof it.src === "string"));
// a card of another plugin with a view of its own (an HTML frame's live view, the frames plugin): Dev mode's dock offers it (HY.ownOpen)
const liveOf = id => { const it = HY.board.items[id]; return !!(it && it.type !== TYPE && HY.ownOpen && HY.ownOpen(id, true)); };
const mark = () => `<span class="mk mk-br mk-kind" title="${esc(t("HTML page: double-click for Dev Studio"))}"><b class="kp">${window.hyMarkIcon ? window.hyMarkIcon("doc") : ""}</b><span class="kw"><span><span class="kt">HTML</span></span></span></span>`;

const sizeTo = (f, it) => C.sizeTo(f, it);

/* ---------- Dev mode ---------- */
// The camera brings the card between the two panels as Dev Studio opens and takes the board back as it closes: Hyimg does that for every
// Studio now (ui/modes.js, owner decision 2026-10-10, P4 S-61), as Dev Studio alone did before
const toPage = m => { if (D && D.frame && D.frame.contentWindow) D.frame.contentWindow.postMessage(Object.assign({ hydev: 2 }, m), "*"); };
// the marks in the page (agent.js: the hover, the pick, its label) in Dev Studio's green, the light theme's when the board is light (owner
// 2026-10-09, the picked element in blue: «опять мы что-то выделяем, у нас это синего цвета вместо зеленого»)
const accent = () => toPage({ a: "accent", c: getComputedStyle(document.documentElement).getPropertyValue("--dev").trim() });
new MutationObserver(() => { if (D) accent(); }).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

async function openDev(id) {
  if (D) await closeDev();
  const it = HY.board.items[id], el = cardEl(id); if (!isPage(it) || !el) return;
  const b = await C.base(); if (!b) return HY.toast(t("Dev Studio: this Hyimg shows no sandboxed pages, update it"), "error");
  if (D) await closeDev();
  C.unpreview(id, el);
  D = { id, el, tree: null, open: new Set(), sel: null, sels: new Set(), detail: null, more: [], q: "", picking: false, info: {},
    src: it.src, sid: Math.random().toString(36).slice(2, 10), rev: null, vars: [], srcErr: "", past: [], future: [], gen: 0, scope: {}, redraw: () => drawInspector(),
    edit: false, tab: "insp", opened: Date.now(), touched: new Set(), done: () => closeDev() };   // done: ⌘↵ in a field (inspect.js)
  el.classList.add("plg-live", "dvlive"); document.body.classList.add("dvedit");
  const f = document.createElement("iframe"); f.className = "dvf"; f.setAttribute("sandbox", "allow-scripts"); f.title = it.src;
  f.src = b + pathUrl(it.src) + "?hyp=" + enc(PLUGIN); sizeTo(f, it); el.appendChild(f); D.frame = f;
  // a pinch over the page zooms the board, ⌥ with it the page (Hyimg ui/framezoom.js; agent.js sends the gestures)
  D.zoom = window.hyFrameZoom ? hyFrameZoom.attach(f) : null;
  D.wait = setTimeout(() => { if (D && !D.tree) { D.info.none = true; drawTree(); } }, 6000);
  D.ui = buildUI(); HY.dock(D.bar); drawBar(); PN.sync();
  D.sdock = studioDock({ D: () => D, t: (k, v) => t(k, v), svg, EDITS, PN, pick: () => setPicking(!D.picking), comment: () => setCommenting(!D.commenting),
    edit: () => setEdit(!D.edit), del: () => TE.del(), reload: () => reload(), done: () => closeDev() });
  D.ui.right.addEventListener("focusout", () => setTimeout(() => { if (D && D.dirty) drawInspector(); }, 0));
  if (HY.full) HY.full(true);   // the library folds while the editor is open, it comes back on Done, as for the 3D studio
  if (HY.select) HY.select([]);   // the board's selection (its bar, the card's corners) stays off the page being edited
  HY.render(); if (HY.modeChanged) HY.modeChanged();
  D.t0 = performance.now();
}
// what is still on its way into the file goes there first (P4 S-17: Done, Reload or Board lost a change still settling): the text being
// typed in the page ends and comes over, the inspector's settling change is written, and both writes are waited for
async function settleEdits(d) {
  if (d.frame) { const got = new Promise(ok => { d.finished = ok; setTimeout(ok, 500); }); toPage({ a: "finish" }); await got; d.finished = null; }
  await EDITS.flush();
}
function closeDev() {   // resolves once Dev Studio is closed; a second call waits for the same closing
  if (!D) return Promise.resolve(); if (D.closing) return D.closing;
  const d0 = D; return (d0.closing = settleEdits(d0).then(() => { if (D === d0) teardown(); }));
}
function teardown() {
  const d = D; D = null;
  clearTimeout(d.wait); if (d.zoom) d.zoom.detach();
  d.frame.remove(); d.el.classList.remove("plg-live", "dvlive"); document.body.classList.remove("dvedit");
  // the pins a tree row lit go dark (Esc leaves with the pointer still on that row, whose pointerleave never comes); the live points go
  if (window.hyComments && hyComments.light) hyComments.light([]); WHERE.clear();
  clearTimeout(d.still); if (d.wrote) C.BUST.set(d.src, d.rev);   // the card's picture of the page as it is now
  if (d.sdock) d.sdock.destroy(); d.unplace(); d.ui.root.remove(); HY.dock(null);
  if (HY.full) HY.full(false);
  const it = HY.board.items[d.id];
  if (it && d.wrote) { if (it.type === TYPE) C.card(d.el, it); else if (HY.changed) HY.changed(d.id); }   // a frame: its own plugin draws its still again
  if (it && HY.select) HY.select([d.id]);
  HY.render(); if (HY.modeChanged) HY.modeChanged();
}
function setPicking(on) {
  if (!D) return; const was = D.picking; D.picking = !!on; if (on) D.commenting = false; toPage({ a: "inspect", on: D.picking || D.commenting });
  D.bar.querySelectorAll("[data-tool]").forEach(b => { const v = !!(b.dataset.tool === "pick" ? D.picking : D.commenting); b.classList.toggle("on", v); b.setAttribute("aria-pressed", String(v)); });
  if (was !== D.picking && !D.detail) drawInspector();   // its footnote says what a click in the page does now
}
// Edit mode (treeedit.js): the mini toggle in the right block's header or E; Select comes on with it (a click picks, a double click types),
// and goes back to how it was when Edit mode ends
function setEdit(on) {
  if (!D || !!on === !!D.edit) return;
  D.edit = !!on; toPage({ a: "edit", on: D.edit });
  if (D.edit) { D.pickBefore = D.picking; if (!D.picking) setPicking(true); } else if (D.pickBefore === false && D.picking) setPicking(false);
  PN.sync(); drawTree(); drawInspector();
}
// Comments on the page's elements (owner 2026-10-07: «чтобы я мог добавлять либо поверх картинки статичной, либо еще как»): the Comment tool
// (C) makes a click in the page pin a thread to the element under it (Hyimg's ui/comments.js): its key in the tree, a css selector, its tag
// and text, the point in the page; the pin follows the element in the live page (the page reports where its elements are) and stands at
// that point of the card's still on the board. Draw (P) is the board's Annotate over the page, anchored to the card
function setCommenting(on) {
  if (!D) return; if (on && !D.commenting) D.pickWas = D.picking;   // Esc gives back the tool before it
  D.commenting = !!on; if (on) D.picking = false; setPicking(D.picking);
  if (on) HY.toast(t("Click an element of the page to annotate it"), "info");
}
function comment(d) {
  const it = HY.board.items[D.id], el = cardEl(D.id), C = window.hyComments; if (!it || !el || !C || !C.newAt || !d.el) return;
  const s = it.w / vwOf(it), [vx, vy] = d.vp || [0, 0], [px, py] = d.pt || [vx, vy];
  const p = { x: it.x + vx * s, y: it.y + vy * s }, at = [Math.min(1, Math.max(0, px / vwOf(it))), Math.min(.98, Math.max(0, py / vhOf(it)))];
  const n = d.n, id = D.id;   // a comment from the tree (agent.js spot): cancelled, the boxes the page scrolled to show its element go back
  const cancel = n ? () => { if (D && D.id === id) toPage({ a: "unspot", n }); } : null;
  C.newAt(p, { anchor: { obj: D.id, kind: "html", file: it.src, r: [it.x, it.y, it.w, it.h] }, at, element: { ...d.el, page: d.pt, ...(d.pin ? { pin: d.pin } : {}) },
    ...(cancel ? { cancel } : {}) });
}
// the pins of this page's elements: the point the page gives (agent.js «One rule», the same a new comment from the tree takes), scaled to
// the card; out of sight (a scroller, a slider, the page scrolled past it) no pin, but a thread made at the edge stays on it; at rest the
// card's share
const WHERE = new Map();
function watchPins() {
  const C = window.hyComments; if (!D || !C || !C.threads) return;
  const keys = C.threads().filter(x => x.element && x.anchor && x.anchor.obj === D.id).map(x => x.element.key);
  const k = keys.join("|"); if (k === D.watching) return; D.watching = k; toPage({ a: "where", keys });
}
function pinAt(th) {
  if (!D || !th.element || !th.anchor || th.anchor.obj !== D.id || !WHERE.has(th.element.key)) return undefined;
  const p = WHERE.get(th.element.key), it = HY.board.items[D.id];
  if (!p || !it || (p[2] && th.element.pin !== "edge")) return null;
  const s = it.w / vwOf(it); return { x: it.x + p[0] * s, y: it.y + p[1] * s };
}
// the selection: one element, or ⇧ adds and takes away one (the primary is the last one added)
function select(i, scroll, add) {
  if (!D) return;
  if (add && i && D.sels.has(i) && D.sels.size > 1) { D.sels.delete(i); i = [...D.sels].at(-1); }
  else if (add && i) D.sels.add(i); else D.sels = new Set(i ? [i] : []);
  D.sel = i || null;
  toPage({ a: "sel", i: D.sel, all: [...D.sels], scroll: !!scroll });
  drawTree(); if (i) revealRow(i);
}
function unselect() { if (!D) return; D.sel = null; D.sels = new Set(); D.detail = null; D.more = []; toPage({ a: "sel", i: null, all: [] }); drawTree(); drawInspector(); }
// typing an element's text in place: only one the file has, with nothing but text inside
function typeText(d) {
  if (!D || !d) return;
  const off = why(D, t, d);
  if (off) return HY.toast(off.replace(/<[^>]+>/g, ""), "info");
  if (!d.src || typeof d.src.text !== "string") return HY.toast(t("Only an element with nothing but text inside can be typed"), "info");
  D.typed = { i: d.i, file: d.src.text }; D.frame.focus(); toPage({ a: "type", i: d.i });   // the file's text now: edits.js text() (P4 S-05)
}
// after a write: the undo buttons, and the card's picture drawn again once the edits settle
function wrote() {
  if (!D) return; D.wrote = true; drawBar();
  clearTimeout(D.still); const d = D;
  D.still = setTimeout(() => { C.BUST.set(d.src, d.rev); const it = HY.board.items[d.id];
    if (it && it.type === TYPE) fetch(C.stillUrl(it, d.el._s || 640)).catch(() => {}); }, 1500);
}
// one step of ⌘Z or ⇧⌘Z (redo true), then its name over the dock's button for 2 s (dock.js)
function step(redo) { const d = D; Promise.resolve((redo ? EDITS.redo : EDITS.undo)()).then(() => { if (d && D === d && d.sdock) d.sdock.done(redo ? "redo" : "undo"); }); }
function drawBar() {
  if (!D) return;
  const u = D.bar.querySelector("[data-a=undo]"), r = D.bar.querySelector("[data-a=redo]");
  if (u) u.disabled = !D.past.length; if (r) r.disabled = !D.future.length;
}
function revealRow(i) { const r = D && D.ui.tree.querySelector(`.row[data-i="${i}"]`); if (r) r.scrollIntoView({ block: "nearest" }); }

addEventListener("message", e => {
  const d = e.data; if (!D || !D.frame || e.source !== D.frame.contentWindow || !d || d.hydev !== 1) return;
  if (d.tree) {
    D.tree = d.tree;
    if (d.ready) {
      D.info = { title: d.title, vw: d.vw, vh: d.vh }; D.open = new Set(); const r = d.tree.root;
      if (r) { D.open.add(r.i); (r.k || []).forEach(k => { if (k.t === "body") { D.open.add(k.i); } }); }
      // a page (again): the select tool, the source, the pins, the marks' colour, Edit mode
      setPicking(D.picking); EDITS.load(); D.watching = null; watchPins(); accent(); toPage({ a: "edit", on: !!D.edit });
    }
    drawTree(); if (!D.detail) drawInspector();
  }
  if ("hover" in d) { D.ui.tree.querySelectorAll(".row.hov").forEach(r => r.classList.remove("hov")); if (d.hover) { const r = D.ui.tree.querySelector(`.row[data-i="${d.hover}"]`); if (r) r.classList.add("hov"); } }
  if (d.where) { for (const [k, r] of Object.entries(d.where)) WHERE.set(k, r); if (window.hyComments) hyComments.draw(); }
  if (d.zoom && typeof d.zoom === "object" && D.zoom) D.zoom.wheel(d.zoom);   // checked there: numbers in range only
  if (d.spot) { TC.spot(d.spot); return; }   // where a comment from the tree goes (treecomments.js)
  if (d.pick && D.commenting) { comment(d); return; }
  if (d.pick) { (d.path || []).slice(0, -1).forEach(i => D.open.add(i)); select(d.pick, false, d.shift); }
  if (d.dbl) { (d.path || []).slice(0, -1).forEach(i => D.open.add(i)); if (D.sel !== d.dbl) select(d.dbl); typeText(d.detail); }
  if ("detail" in d) { D.detail = d.detail; D.more = d.more || []; if (d.rev) EDITS.seen(d.rev); drawInspector(); }
  if (d.text) EDITS.text(d.text.i, d.text.was, d.text.text);
  if (d.finished && D.finished) D.finished();   // the page ended its typing (settleEdits)
  if (d.key === "Escape") onKey({ key: "Escape", preventDefault() {} });
  if (d.key === "z") step(d.shift);
  if (d.key === "acts" && D.sdock) D.sdock.toggle();   // ⌘K in the page
  if (d.key === "Enter" && D.detail) typeText(D.detail);
  if (d.key === "i") setPicking(!D.picking);
  if (d.key === "done") closeDev();   // ⌘↵ in the page (P4 S-28)
  if (d.key === "reload") reload();   // ⌥R in the page (owner 2026-10-10)
  if (d.key === "e") setEdit(!D.edit);
  if (d.key === "Backspace") TE.del();
  if (d.key === "c") setCommenting(!D.commenting);
  if (d.key === "p" && window.hyAnnot && hyAnnot.drawing) hyAnnot.tool("pen");   // the drawing tools wait for later (hyimg docs/LATER.md)
});

/* the panels: the 3D studio's places (under the top band, right of the library, clear of the dock) and the library's rows */
function buildUI() {
  const root = document.createElement("div"); root.className = "dvui";
  root.innerHTML = `
    <div class="dvp dvl hy-blk" data-hyui><div class="lhd"><label class="hy-search">${svg(IC.find, 15)}<input data-q type="search" placeholder="${esc(t("Find element"))}" aria-label="${esc(t("Find element"))}" autocomplete="off" spellcheck="false"></label></div>
      <div class="dvh hy-sh"><span>${esc(t("Elements"))}</span><span class="cnt hy-sh-n"></span></div><div class="dvt" role="tree" tabindex="0" aria-label="${esc(t("Elements"))}"></div></div>
    <div class="dvp dvr hy-blk" data-hyui>${PN.head()}<div class="ih"></div><div class="inf"></div><div class="dvhl" role="list" aria-label="${esc(t("History"))}"></div></div>`;
  document.body.appendChild(root);
  const q = s => root.querySelector(s);
  const ui = { root, left: q(".dvl"), right: q(".dvr"), tree: q(".dvt") };
  PN.wire(ui.right);
  const place = () => {
    const r = HY.stage.getBoundingClientRect(), inset = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--inset")) || 0;
    root.style.setProperty("--l", (r.left + inset + 12) + "px"); root.style.setProperty("--r", (innerWidth - r.right + 12) + "px");
    const crumb = document.getElementById("crumb"), band = crumb && crumb.getClientRects().length ? crumb.getBoundingClientRect().bottom + 8 : 0;
    root.style.setProperty("--t", Math.max(r.top + 12, band) + "px"); root.style.setProperty("--b", (innerHeight - r.bottom + 76) + "px");
  };
  const mo = new MutationObserver(place); mo.observe(document.documentElement, { attributes: true, attributeFilter: ["style"] });
  place(); addEventListener("resize", place);
  const onHide = ev => toPage({ a: "marks", on: !(ev.detail && ev.detail.on) });   // ⌘. hides the marks in the page with the panels
  document.addEventListener("hy:hideui", onHide);
  D.unplace = () => { removeEventListener("resize", place); mo.disconnect(); document.removeEventListener("hy:hideui", onHide); };
  // the search: matching rows and the rows they sit in
  q("[data-q]").addEventListener("input", e => { D.q = e.target.value.trim(); drawTree(); });
  q("[data-q]").addEventListener("keydown", e => { e.stopPropagation(); if (e.key === "Escape") { if (e.target.value) { e.target.value = ""; D.q = ""; drawTree(); } else e.target.blur(); } });
  const tree = ui.tree;
  tree.addEventListener("pointerover", e => {
    const r = e.target.closest(".row"); if (!r || r._hl) return;
    tree.querySelectorAll(".row.hov").forEach(x => { x.classList.remove("hov"); x._hl = false; }); r.classList.add("hov"); r._hl = true; toPage({ a: "hl", i: +r.dataset.i });
    TC.hover(r); TE.hover(r);   // its pins lit on the board, the comment button on it; in Edit mode + and the bin
  });
  tree.addEventListener("pointerleave", () => {
    tree.querySelectorAll(".row.hov").forEach(x => { x.classList.remove("hov"); x._hl = false; }); toPage({ a: "hl", i: null }); TC.hover(null); TE.hover(null);
  });
  tree.addEventListener("click", e => {
    if (TE.click(e) || TC.click(e)) return;   // Edit mode's + and bin (treeedit.js), a row's comment button or its count (treecomments.js)
    if (e.detail === 2 && TE.dbl(e)) return;   // a double click in Edit mode: the second click, the row the first one drew again still under it
    const r = e.target.closest(".row"); if (!r) return; const i = +r.dataset.i;
    if (e.target.closest(".chev")) { D.open.has(i) ? D.open.delete(i) : D.open.add(i); return drawTree(); }
    select(i, true, e.shiftKey);
  });
  // a row's right click: the app's menu (the board's #ctx) with the notes' colours, «no colour» first (owner 2026-10-07: «в layers при нажатии
  // правой кнопки добавить colors как в notes ... и так в любых»); the tree picks one element at a time, so the colour goes to that row;
  // then «Comment» on its element (owner 2026-10-08, treecomments.js)
  tree.addEventListener("contextmenu", e => {
    const r = e.target.closest(".row[data-p]"), m = document.getElementById("ctx");
    e.preventDefault(); e.stopPropagation(); if (!r || !m || !window.hyMenuColors || !window.hyColorPick) return;
    const key = r.dataset.p, i = +r.dataset.i;
    m.innerHTML = hyMenuColors(colorsOf()[key] || "") + TC.item();
    m.onclick = ev => {
      if (ev.target.closest('[data-act="comment"]')) { m.classList.remove("open"); TC.start(i); return; }
      const c = hyColorPick(ev); if (c === null) return; m.classList.remove("open"); setColor(key, c);
    };
    m.classList.add("open");
    m.style.left = Math.min(e.clientX, innerWidth - m.offsetWidth - 8) + "px"; m.style.top = Math.min(e.clientY, innerHeight - m.offsetHeight - 8) + "px";
  });
  tree.addEventListener("dblclick", e => {   // in Edit mode a tag, #id, .classes or text goes into a field (treeedit.js); elsewhere the row folds
    if (TE.dbl(e)) return;
    const r = e.target.closest(".row"); if (!r || e.target.closest(".chev, .dvcb, .dvcn, .dvea, .dved, .dvin")) return;
    const i = +r.dataset.i; D.open.has(i) ? D.open.delete(i) : D.open.add(i); drawTree();
  });
  // the dock: Select, Annotation (Draw only with the drawing tools on, hyimg docs/LATER.md), Undo, Redo (the board's own dock, in its look); Live view, Reload, Open in <Browser> and Done stand
  // top right, Hyimg's one place for a Studio's session actions (ui/hy/actions.js; owner 2026-10-09: «кнопки Done у нас всегда
  // стандартизированы справа вверху, а не внизу»)
  const bar = document.createElement("span"); bar.className = "dvbar";
  bar.innerHTML = `<button class="hy-dkb" data-tool="pick" aria-pressed="false" title="${esc(t("Select elements in the page; off, the page takes the clicks · V"))}" aria-label="${esc(t("Select"))}">${svg(IC.pick, 17)}<kbd>V</kbd></button>`
    + `<button class="hy-dkb" data-tool="comment" aria-pressed="false" title="${esc(t("Annotation on an element: click it in the page · C"))}" aria-label="${esc(t("Annotation"))}">`
    + `${svg("comment", 17)}<kbd>C</kbd></button>`
    + (window.hyAnnot && hyAnnot.drawing
      ? `<button class="hy-dkb" data-a="draw" title="${esc(t("Draw over the page · P"))}" aria-label="${esc(t("Draw"))}">${svg("marker", 17)}<kbd>P</kbd></button>` : "")
    + `<span class="sep" aria-hidden="true"></span>`
    + `<button class="hy-dkb" data-a="undo" disabled title="${esc(t("Undo the last edit of the file · ⌘Z"))}" aria-label="${esc(t("Undo"))}">${svg("undo", 17)}</button>`
    + `<button class="hy-dkb" data-a="redo" disabled title="${esc(t("Redo · ⇧⌘Z"))}" aria-label="${esc(t("Redo"))}">${svg("redo", 17)}</button>`
    + `<span class="sep" aria-hidden="true"></span><span class="dgrp" data-dk="view"></span><span class="sep" aria-hidden="true"></span><span data-dk="acts"></span>`;
  bar.addEventListener("click", e => {
    const b = e.target.closest("button"); if (!b || !D) return;
    if (b.dataset.tool === "pick") return setPicking(!D.picking);
    if (b.dataset.tool === "comment") return setCommenting(!D.commenting);
    if (b.dataset.a === "draw" && window.hyAnnot && hyAnnot.drawing) return hyAnnot.tool("pen");
    if (b.dataset.a === "undo" || b.dataset.a === "redo") step(b.dataset.a === "redo");
  });
  D.bar = bar;
  // Live view (the frames plugin's own view of its HTML frame), Reload, Open in <Browser> (the page alone, still sandboxed), Done
  const acts = document.createElement("hy-studio-actions"); root.appendChild(acts);
  const live = { id: "live", label: t("Live view"), tip: t("The frame's live view: device sizes, its edges resize the page"),
    run: async () => { if (!D) return; const id = D.id; await closeDev(); HY.ownOpen(id); } };
  acts.actions = [...(liveOf(D.id) ? [live] : []), { id: "reload", label: t("Reload"), tip: t("Reload the page"), key: "⌥R", run: () => reload() },
    { id: "open", open: () => (D ? D.frame.src.replace(/\?.*$/, "") : ""), tip: t("Open the page alone in a new tab, still sandboxed") },
    { id: "done", label: t("Done"), title: t("Done · ⌘↵ or Esc"), key: "⌘↵", primary: true, run: () => closeDev() }];   // P4 S-28, S-60
  return ui;
}

// a row's colour (the right click above): kept in the card's own item on the board, {treeColors: {<row path>: <colour name>}}, never in the
// page or its file; a row is keyed by its place, «html>body:1>main:0» (each element's tag and index among its parent's elements), which
// stays the same between loads while the ids of the tree (data-i) do not. A colour is one step of the board's undo
const colorsOf = () => (D && HY.board.items[D.id] && HY.board.items[D.id].treeColors) || {};
const rowHex = name => (name && window.hyRowColor && hyRowColor(name)) || "";
function setColor(key, name) {
  const it = D && HY.board.items[D.id]; if (!it) return;
  const before = HY.snap(), c = Object.assign({}, it.treeColors);
  if (name) c[key] = name; else delete c[key];
  if (Object.keys(c).length) it.treeColors = c; else delete it.treeColors;
  HY.commit(before); drawTree();
}

// the page loaded again (Reload, or an undo of a step made before it): its ids are new, the selection goes
async function reload() {
  if (!D) return; const d0 = D; await settleEdits(d0); if (D !== d0) return;
  D.tree = null; D.detail = null; D.more = []; D.sel = null; D.sels = new Set(); D.gen++; D.info.none = false; D.touched = new Set();   // ids are new: the dots stay by row (D.tk)
  clearTimeout(D.wait); D.wait = setTimeout(() => { if (D && !D.tree) { D.info.none = true; drawTree(); } }, 6000);   // a page that never answers says so again (P4 S-41)
  D.frame.src = D.frame.src; drawTree(); drawInspector();
}

// a node of the page's tree by its id (the crumbs of the picked element, panel.js)
function nodeById(i) {
  const T = D && D.tree; if (!T || !T.root) return null;
  if (!D.byId || D.byId.tree !== T) { const m = new Map(), walk = n => { m.set(n.i, n); (n.k || []).forEach(walk); }; walk(T.root); D.byId = { tree: T, m }; }
  return D.byId.m.get(i) || null;
}
function label(n) {
  return `<span class="dtg">${esc(n.t)}</span>${n.d ? `<span class="dia">#${esc(n.d)}</span>` : ""}${n.c ? `<span class="dic">.${esc(n.c.split(" ").slice(0, 3).join("."))}</span>` : ""}${n.x ? `<span class="dtx">${esc(n.x)}</span>` : ""}`;
}
function drawTree() {
  if (!D || TE.busy()) return;   // a row's field open in Edit mode: the tree waits for it
  const box = D.ui.tree, cnt = D.ui.left.querySelector(".cnt"), T = D.tree;
  if (!T || !T.root) { box.innerHTML = `<div class="dnone">${esc(D.info.none ? t("The page did not answer: it may block scripts or its file is gone") : t("Loading the page…"))}</div>`; cnt.textContent = ""; return; }
  cnt.textContent = t("{n} elements", { n: T.n });
  TC.count();   // the threads on this page's elements, by row (treecomments.js)
  const q = D.q.toLowerCase(); let keep = null;
  if (q) {
    keep = new Set();
    const hit = n => (n.t + (n.d ? "#" + n.d : "") + (n.c ? "." + n.c.replace(/ /g, ".") : "") + " " + (n.x || "")).toLowerCase().includes(q);
    const walk = n => { let any = hit(n); for (const k of n.k || []) if (walk(k)) any = true; if (any) keep.add(n.i); return any; };
    walk(T.root);
  }
  const out = [], cols = colorsOf(); let more = 0;
  const walk = (n, depth, key) => {
    if (keep && !keep.has(n.i)) return;
    if (out.length >= ROWS) { more++; return; }
    const kids = n.k && (keep ? n.k.some(k => keep.has(k.i)) : true), open = !!kids && (keep ? true : D.open.has(n.i)), hex = rowHex(cols[key]);
    const ch = D.touched.has(n.i) || (D.tk && D.tk.has(key)); if (D.touched.has(n.i)) (D.tk || (D.tk = new Set())).add(key);   // changed, by its place
    const tint = hex ? ` hy-rc" style="--hy-rc:${hex}` : "";   // the row's colour: a stripe on its left (Hyimg ui/menu.js .hy-rc)
    out.push(`<div class="row hy-hovrow${D.sels.has(n.i) ? " sel" : ""}${kids && !open ? " closed" : ""}${tint}" data-i="${n.i}" data-p="${esc(key)}" role="treeitem" aria-level="${depth + 1}"`
      + `${kids ? ` aria-expanded="${open}"` : ""}${D.sels.has(n.i) ? ' aria-selected="true"' : ""}>`
      + `${'<span class="g"></span>'.repeat(depth)}${kids ? `<button class="chev" tabindex="-1" aria-hidden="true">${CHEV()}</button>` : '<span class="chev"></span>'}<span class="nm">${label(n)}</span>`
      + `${ch ? `<span class="hy-dot dvchd" title="${esc(t("Changed, written to the file"))}"></span>` : ""}`
      + `${TC.mark(key, !!kids && !open)}</div>`);
    if (open) n.k.forEach((k, j) => walk(k, depth + 1, `${key}>${k.t}:${j}`));
  };
  walk(T.root, 0, T.root.t);
  box.innerHTML = (out.length ? out.join("") : `<div class="dnone">${esc(t("Nothing found"))}</div>`)
    + (more ? `<div class="dnone">${esc(t("{n} more rows: narrow the search", { n: more }))}</div>` : "") + (T.cut ? `<div class="dnone">${esc(t("Only the first {n} elements", { n: T.n }))}</div>` : "");
  TC.place();
}
function kv(k, v, mono) { return `<div class="dkv"><span class="dk">${esc(k)}</span><span class="dv${mono ? " dmono" : ""}">${v}</span></div>`; }
function drawInspector() {
  if (!D) return;
  const head = D.ui.right.querySelector(".ih"), inf = D.ui.right.querySelector(".inf"), it = HY.board.items[D.id] || {}, d = D.detail;
  // a control in use (a field being typed in, the colour picker open, the slider held) is not drawn again under the pointer
  const ae = document.activeElement;
  // (the header's Edit toggle is a checkbox: it holds the focus after a click and is not in use), or a number being dragged by its label
  if (D.scrubbing || (ae && D.ui.right.contains(ae) && ae.matches("input:not([type=checkbox]), hy-segmented button"))) { D.dirty = true; return; }
  D.dirty = false;
  D.ledOff = d ? why(D, t, d).replace(/<[^>]+>/g, "") : D.srcErr ? t("Can't save this file: {why}", { why: D.srcErr }) : "";
  if (!d) {
    head.innerHTML = `<span class="dvth">${svg(IC.code, 14)}</span><div><b>${esc(t("Page"))}</b><span class="dvq">${esc(D.info.title || "")}</span></div>${LED}`;
    PN.led();
    inf.innerHTML = `<div class="dsec">${kv(t("Page"), esc(it.src || ""), true)}${kv(t("Viewport"), `${D.info.vw || vwOf(it)} × ${D.info.vh || vhOf(it)}`)}${D.tree ? kv(t("Elements"), esc(String(D.tree.n))) : ""}</div>`
      + `<p class="hy-hint dhint">${D.srcErr ? t("<b>Can't save</b> this file: {why}", { why: esc(D.srcErr) })
        : D.picking ? t("<b>Click</b> an element in the page or the tree to edit it, <b>⇧</b> adds one")
        : t("The page takes the clicks: <b>I</b> turns on Select to pick its elements, or pick one in the tree")}</p>`   /* the app's footnote (ui/look.css .hy-hint) */
      + (D.picking ? "" : `<p class="hy-hint dhint">${t("Pinch zooms the board, with <b>⌥</b> the page")}</p>`);
    return;
  }
  const n = 1 + D.more.length;
  head.innerHTML = PN.crumb(d, n, nodeById); PN.led();
  const swatch = v => /^(rgb|#|hsl|oklch|color)/.test(v) ? `<i class="dsw" style="background:${esc(v)}"></i>` : "";
  inf.innerHTML = drawEdit(D, t, svg) + `<div class="dsec"><div class="dsh hy-sh">${esc(t("Box"))}</div>${kv(t("Size"), `${d.box.w} × ${d.box.h}`)}${kv(t("Position"), `${d.box.x}, ${d.box.y}`)}${kv(t("Children"), String(d.kids))}</div>`
    + `<div class="dsec"><div class="dsh hy-sh">${esc(t("Styles"))} <small>${esc(t("computed"))}</small></div>${d.styles.map(([k, v]) => kv(k, swatch(v) + esc(v), true)).join("")}</div>`
    + (D.edit ? TE.attrsHtml(d, why(D, t, d))   // Edit mode: every attribute a field (treeedit.js)
      : `<div class="dsec"><div class="dsh hy-sh">${esc(t("Attributes"))}</div>`
        + `${d.attrs.length ? d.attrs.map(([k, v]) => kv(k, esc(v), true)).join("") : `<p class="dnote">${esc(t("none"))}</p>`}</div>`);
  wire(inf, D, EDITS, t); if (D.edit) TE.wireAttrs(inf, d);
}

function onKey(e) {
  if (!D) return false;
  const mod = e.metaKey || e.ctrlKey;
  // ⌥R reloads the page, in the app and in a browser alike (owner 2026-10-10: «option + R, так будет лучше и в браузере будет работать»);
  // ⌘R is never ours: the app's menu item has no key, a browser reloads its tab. By the physical key: ⌥R types «®» on a Mac
  if (e.altKey && !mod && !e.shiftKey && e.code === "KeyR") { e.preventDefault(); reload(); return true; }
  if (mod) {   // ⌘Z, ⇧⌘Z and ⌘Y are Dev's own, also with nothing to take back (P4 S-07: ⌘Z then undid the board); ⌘. and the rest the app's
    const z = /^[zZяЯ]$/.test(e.key), y = /^[yYнН]$/.test(e.key) && !e.shiftKey;
    if (!e.altKey && (z || y)) { e.preventDefault(); step(e.shiftKey || y); return true; }
    if (!e.altKey && !e.shiftKey && (e.code === "KeyK" || /^[kKлЛ]$/.test(e.key))) { e.preventDefault(); if (D.sdock) D.sdock.toggle(); return true; }   // ⌘K Actions
    if (e.key === "Enter" && !e.altKey && !e.shiftKey) { e.preventDefault(); closeDev(); return true; }   // ⌘↵ Done, the primary (P4 S-28)
    return false;
  }
  if (e.key === "Escape") {   // Esc steps out: an open comment thread, the comment tool, the selection, then Dev mode
    if (e.preventDefault) e.preventDefault();
    if (window.hyComments && hyComments.escape && hyComments.escape()) return true;   // a thread opened from a pin or a row's count
    if (D.commenting) { D.commenting = false; setPicking(!!D.pickWas); } else if (D.sels.size) unselect(); else closeDev();
    return true;
  }
  if (e.key === "Enter" && D.detail) { e.preventDefault(); typeText(D.detail); return true; }
  if (/^[eEуУ]$/.test(e.key) && !e.altKey) { e.preventDefault(); setEdit(!D.edit); return true; }   // Edit mode (treeedit.js)
  if ((e.key === "Backspace" || e.key === "Delete") && D.edit) { e.preventDefault(); TE.del(); return true; }
  // V selects, as in Image and 3D (P4 S-30), I too (the browser's inspector key)
  if (/^[vVмМiIшШ]$/.test(e.key) && !e.altKey) { e.preventDefault(); setPicking(!D.picking); return true; }
  if (/^[cCсС]$/.test(e.key) && !e.altKey) {   // the tree has the focus and a row: a comment on its element (treecomments.js); else the Comment tool
    e.preventDefault();
    if (D.sel && D.ui.tree.contains(document.activeElement)) TC.start(D.sel); else setCommenting(!D.commenting);
    return true;
  }
  return true;   // nothing else of the board while Dev mode is open (Delete must not remove the card)
}

export function register(hy) {
  HY = hy; t = translator(hy);
  C = makeCards(hy, { mark, pathUrl, vwOf, vhOf, devId: () => D && D.id });
  TC = makeTreeComments({ D: () => D, HY: hy, t: (k, v) => t(k, v), esc, toPage, select, comment, drawTree });
  EDITS = makeEdits({ D: () => D, toPage, t: (k, v) => t(k, v), toast: (m, k, o) => HY.toast(m, k, o), plugin: PLUGIN, reload: () => reload(),
    picked: ids => { if (!ids.length) return unselect(); select(ids[0]); ids.slice(1).forEach(i => select(i, false, true)); },   // after ⌫ and its ⌘Z (P4 S-51)
    changed: w => { if (w) wrote(); drawBar(); drawInspector(); if (D) { PN.sync(); if (w) drawTree(); } }, busy: () => { if (D) PN.led(); } });
  PN = makePanel({ D: () => D, t: (k, v) => t(k, v), svg, EDITS, select, setEdit });
  TE = makeTreeEdit({ D: () => D, t: (k, v) => t(k, v), svg, EDITS, select, toast: (m, k) => HY.toast(m, k), toPage, drawTree, drawInspector, done: () => closeDev() });
  const st = document.createElement("style"); st.textContent = CSS_EDIT + CSS_PANEL + CSS_TREEEDIT + `
    .plg[data-type=${TYPE}] { background: var(--raise); overflow: hidden; --dv-page: #fff; }   /* a page's own ground when it sets none */
    .plg[data-type=${TYPE}] img.dvi { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: top; pointer-events: none; }
    /* the live page at rest (cards.js): .dvpg, not .dvp, the panels' class: their z-index 60 lay the page over the card's marks, the
       notes' dots and the ♥ of a card big enough to be live (owner 2026-10-08: «почему у HTML точки не появляется сверху?») */
    .plg[data-type=${TYPE}] iframe.dvpg { position: absolute; left: 0; top: 0; border: 0; transform-origin: 0 0; background: var(--dv-page); pointer-events: none; opacity: 0; transition: opacity .25s cubic-bezier(.32,.72,0,1); }
    .plg[data-type=${TYPE}].pv iframe.dvpg { opacity: 1; }
    .plg.dvlive { overflow: hidden !important; }   /* no outline (owner 2026-10-08): the board lifts the card with a shadow instead */
    .plg.dvlive > :not(iframe.dvf) { visibility: hidden; }
    .plg.dvlive iframe.dvf { position: absolute; left: 0; top: 0; border: 0; transform-origin: 0 0; background: #fff; visibility: visible; }
    body.dvedit #info { display: none !important; }
    /* the panels are blocks of the app, round 12 «A · Line» (owner 2026-10-09: «реализуй уже A Line версию на весь интерфейс»): Hyimg
       ui/hy/block.css draws their surface, the sections' heads and the wells; ⌘. hides them with the board's interface (data-hyui), each
       toward its own edge */
    /* Dev Studio wears its colour, its green (--dev, the owner's glossary of modes, Concepts/html/editors-concepts/_shared/gloss.css), in
       both looks (owner 2026-10-09, «конечно» to «3D Studio и Dev Studio пока остаются синими. Дать им их цвета?»; as Image Studio's purple,
       hyimg-image-studio 6e04f1a, and 3D Studio's pink): every chosen, checked or primary thing of the studio (the picked row, a chosen option, a
       value's fill, the tool in hand and Done in the dock) and the Dev segment of the dock's switch (HY.mode color). On the board's root
       because the dock reads it; the light value is the same hue darker, 3.2:1 on the light paper and 4:1 under white words. Blue stays the
       board's selection; the tree's tag, attribute and class colours are the code's own */
    :root { --dev: #2fae6a; } :root[data-theme="light"] { --dev: #279058; }
    .dvui { --sel: var(--dev); --hy-sel: var(--dev); --hy-acc: var(--dev); --hy-tint-bg: color-mix(in srgb, var(--dev) 16%, transparent); --hy-tint-ink: var(--dev);
      --hy-trow-on: color-mix(in srgb, var(--dev) 14%, transparent); --hy-trow-ring: inset 0 0 0 1px color-mix(in srgb, var(--dev) 55%, transparent);
      --hy-val: color-mix(in srgb, var(--dev) 30%, transparent); --hy-val-drag: color-mix(in srgb, var(--dev) 44%, transparent);
      --hy-val-on: color-mix(in srgb, var(--dev) 30%, var(--hy-well)); --hy-val-ink: color-mix(in srgb, var(--dev) 14%, var(--ink)); }
    /* the dock's buttons are Image Studio's tools in the dock (hyimg-image-studio studiodock.js, round 11 D3): 36 × 34, round, no ground until
       pointed at, never squeezed by a narrow dock; one size for Select, Comment, Draw, Undo and Redo (owner 2026-10-09, an arrow at the
       dock: «размеры элементов внизу не соответствуют»: Select and Comment were 34 px circles, Draw, Undo and Redo 45 px pills). The width
       !important and :not(#_): the 3D studio's own rule for its dock's tools, 34 px !important, is not scoped to its dock and reached here */
    #dock .plgdock.dvbar:not(#_) button:not(.wide) { width: 36px !important; padding: 0 !important; justify-content: center; background: transparent !important; flex: none; }
    #dock .plgdock.dvbar:not(#_) button:not(.wide):hover:not(.on, .pri, :disabled) { background: var(--raise) !important; }
    #dock .plgdock.dvbar:not(#_) button:is(.on, .pri) { background: var(--dev) !important; color: var(--hy-on-accent, #fff) !important; }   /* over canvas.html's ink */
    .dvui { --dv-r: var(--hy-trow-r, 8px); color: var(--ink); font: 400 13px/1.4 var(--sans, system-ui); }
    .dvp { position: fixed; z-index: 60; box-shadow: var(--plate-sh, 0 16px 50px rgba(0,0,0,.35)); }
    .dvl { --hx: -16px; left: var(--l); top: var(--t); bottom: var(--b); width: 260px; display: flex; flex-direction: column; padding: 8px 8px 6px; overflow: hidden; }
    .dvr { --hx: 18px; right: var(--r); top: var(--t); bottom: var(--b); width: 290px; overflow: hidden; display: flex; flex-direction: column; }
    /* under the block's header (.hy-bh, Inspector | History, panel.js) the picked element stays, the inspector or History scrolls under it */
    .dvr > .ih { flex: none; } .dvr > .inf, .dvr > .dvhl { flex: 1 1 auto; min-height: 0; overflow: auto; overscroll-behavior: contain; }
    .dvl, .dvr { transition: left var(--inset-ms, 0ms) cubic-bezier(.32,.72,0,1), right var(--inset-ms, 0ms) cubic-bezier(.32,.72,0,1); }
    .dvl .lhd { display: flex; flex: none; padding-bottom: 6px; } .dvl .lhd .hy-search > input { color: var(--ink); }
    .dvl .dvh { cursor: default; }   /* the tree's title: a section's head of the app (.hy-sh), its count at the right end */
    .dvt { flex: 1; min-height: 0; overflow: auto; overscroll-behavior: contain; scrollbar-width: none; }
    .dvt::-webkit-scrollbar { display: none; }
    .dvt .dnone { color: var(--muted); padding: 12px 8px; font-size: 12px; }
    /* the rows are the library's folder rows (review/v2.html .frow, ui/look.css --hy-trow-*): 28 px, 8 px corners, grey hover, the picked one
       a grey fill with a hairline; the 3D outline's guides and the app's chevron, turned with the app's curve */
    .dvt .row { display: flex; align-items: center; height: var(--hy-trow-h, 28px); padding: 0 6px 0 2px; border-radius: var(--dv-r); color: var(--sub); user-select: none; cursor: default; white-space: nowrap; }
    .dvt .row:hover, .dvt .row.hov { background: var(--hy-trow-hover, var(--raise)); color: var(--ink); }
    .dvt .row.sel { color: var(--ink); background: var(--hy-trow-on, var(--raise)); box-shadow: var(--hy-trow-ring, inset 0 0 0 1px var(--line)); }
    .dvt .g { width: 12px; height: var(--hy-trow-h, 28px); flex: none; position: relative; } .dvt .g::before { content: ""; position: absolute; left: 7px; top: -1px; bottom: -1px; border-left: 1px solid var(--line); }
    .dvt .chev { width: 16px; height: 16px; padding: 0; border: 0; background: none; color: var(--muted); display: grid; place-items: center; flex: none; margin-right: 3px; }
    .dvt .chev .hy-chev { width: 12px; height: 12px; transition: transform .32s cubic-bezier(.32,.72,0,1); }
    .dvt .row:not(.closed) .chev .hy-chev { transform: rotate(90deg); }
    .dvt .nm { min-width: 0; overflow: hidden; text-overflow: ellipsis; font: 400 12px/1 ui-monospace, "SF Mono", Menlo, monospace; }
    /* a row's comments (treecomments.js): the count opens them, the button starts one; a folded row with threads further in, a dot */
    .dvt .row .dvcn, .dvt .row .dvcb, .dvt .row .dvcd { margin-left: auto; } .dvt .row .dvcb + .dvcn { margin-left: 0; } .dvt .row .dvcn { color: var(--sel); } .dvt .row .dvcd { margin-right: 6px; }
    .dvt .dtg { color: var(--ink); } .dvt .dia { color: #e8a24a; } .dvt .dic { color: #7dbbf5; } .dvt .dtx { color: var(--muted); margin-left: 8px; font-family: var(--sans, system-ui); }
    :root[data-theme=light] .dvt .dia { color: #b06a10; } :root[data-theme=light] .dvt .dic { color: #1f6fc0; }
    .dvr .inf { padding: 4px 8px 16px; }
    .dvr .dsec { padding: 6px 0 4px; } .dvr .dsec + .dsec { border-top: 1px solid var(--hy-pline); }   /* Line: a hairline between two sections */
    .dvr .dsh small { font: 400 11px var(--sans, system-ui); color: var(--muted); }   /* .dsh is a section's head of the app (.hy-sh) */
    .dvr .dkv { display: flex; align-items: baseline; gap: 10px; min-height: 24px; padding: 3px 6px; border-radius: var(--dv-r); }
    .dvr .dkv:hover { background: var(--hy-trow-hover, var(--raise)); }
    .dvr .dkv .dk { flex: 0 0 104px; color: var(--sub); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .dvr .dkv .dv { flex: 1; min-width: 0; color: var(--ink); font-size: 12px; overflow-wrap: anywhere; user-select: text; }
    .dvr .dkv .dv.dmono { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 11.5px; }
    .dvr .dsw { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--ink) 25%, transparent); }
    .dvr .dnote { color: var(--muted); font-size: 12px; margin: 8px 6px; line-height: 1.45; } .dvr .dhint { margin: 10px 6px; }
    #dock .dvbar { display: contents; }
    body.dvedit #ctx { z-index: 70; } #ctx > .msw:only-child { margin-bottom: 0; border-bottom: 0; }   /* the right-click menu over the panels */`;
  document.head.appendChild(st);
  hy.register(TYPE, {
    opacity: true,   // the pictures' opacity: the bar's slider, the keys 1…9 and 0, «Copy properties» (owner 2026-10-06)
    render(el, it, id) {
      id = id || el.dataset.id;
      if (D && D.id === id) { if (D.frame && !el.contains(D.frame)) el.appendChild(D.frame); if (D.frame) sizeTo(D.frame, it); return; }
      C.card(el, it);
    },
    view: (id, el, px, moving) => C.view(id, el, px, moving),   // the still as sharp as the card is big, the live pages (cards.js)
    resized(id) { const el = cardEl(id), it = HY.board.items[id]; if (el && it && el._pv) sizeTo(el._pv, it); },
    dblclick(id) { openDev(id); },
    onKey,
    info(id, it) {
      return { name: it.src.split("/").pop(), meta: `HTML · ${vwOf(it)}×${vhOf(it)} · ${it.src}`,
        text: t("Double-click or Dev Studio in the dock to edit the page") };
    },
  });
  if (hy.restored) hy.restored(() => { if (D) drawTree(); });   // the board's undo takes a row's colour back
  // an HTML file of the library dropped on the board is a page card, 1280 × 800 like the picture the library shows of it
  if (hy.placeAs) hy.placeAs(p => /\.html?$/i.test(p) ? { type: TYPE, src: p, vw: VW, ar: VW / VH, pics: [p] } : null);
  // color: the chosen segment in Dev Studio's green, not the board's blue (owner 2026-10-09: «конечно», to giving Dev Studio its colour)
  if (hy.mode) hy.mode("dev", { label: t("Dev"), name: t("Dev Studio"), order: 20, icon: svg(IC.code), color: "var(--dev)",
    title: t("Dev Studio for the selected HTML card: the page's tree, the live page, the inspector"), hint: t("Select an HTML card or enter one: Dev Studio opens for it"),
    hintStudio: t("Open an HTML card to use Dev Studio"),   // the tooltip while another Studio is open (owner decision 2026-10-10)
    isOpen: () => !!D, card: () => D && D.id,
    target: ids => { const it = ids.length === 1 && HY.board.items[ids[0]], el = it && cardEl(ids[0]); return isPage(it) && !(it.type === FRAME_TYPE && el && el.classList.contains("plg-live")) ? ids[0] : null; },
    enter: id => openDev(id),
    leave: () => closeDev(),   // Done: nothing in Dev Studio waits to be saved, it never asks (owner decision 2026-10-10, S-26)
    // the Hint bar as it opens (Hyimg ui/modes.js, P4 S-29): V Select, C Annotation, E Edit HTML, Esc / ⌘↵ Done
    primary: "Done", hints: [{ id: "edit", keys: ["e"], t: "dev::Edit HTML" }, { id: "reload", keys: ["alt", "r"], t: "dev::Reload" }],   // ⌥R (2026-10-10)
  });
  // a double-click on the frames plugin's HTML frame opens Dev mode too (owner 2026-10-07: «зашел в режим Dev вроде как, но по факту не
  // зашел»), through the board's generic hook; its live view stays one click away: «Live view» in Dev mode's dock, the bar over the frame.
  // Not while the frame is live already (the page takes the clicks then). With this plugin off the frame opens its live view, as before
  if (hy.opener) hy.opener(FRAME_TYPE, id => { const el = cardEl(id); if (!isPage(HY.board.items[id]) || (el && el.classList.contains("plg-live"))) return false; openDev(id); return true; });
  addEventListener("hy-comments", () => { watchPins(); TC.refresh(); });   // a thread added or gone: the page is asked where its elements are, the rows' counts
  addEventListener("hy-comment-open", e => TC.opened(e));   // a pin opened on the board selects its row (Hyimg ui/comments.js)
  if (window.hyComments && hyComments.position) hyComments.position(pinAt);
  else addEventListener("load", () => { if (window.hyComments && hyComments.position) hyComments.position(pinAt); }, { once: true });
  window.__dev = { openDev, closeDev, select, setPicking, setEdit, get D() { return D; }, get LIVE() { return C.LIVE; }, get BUST() { return C.BUST; }, C, get EDITS() { return EDITS; } };
}
