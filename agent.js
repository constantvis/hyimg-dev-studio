// Dev studio's inspector inside a library page (owner 2026-10-06: «Dev mode is for HTML, and on the left we'll have the HTML tree»; 0.2,
// 2026-10-07: «Выделить объекты и поменять им цвет. Дописать какой-то текст»). Hyimg's server puts this file first in the page's <head>
// when Dev mode opens the page (/sandbox/<key>/<path>?hyp=<plugin>, the manifest's "pageScript"). The page runs in <iframe
// sandbox="allow-scripts"> with an opaque origin, so the board cannot reach into it: this script and the board talk only by postMessage.
// It reads the page (its elements, their boxes, computed styles, the rules that set them, attributes), draws its marks in a closed shadow
// root of one element of its own, shows an edit live when the board asks, and lets the person type an element's text in place. It never
// writes the file: the board does, through Hyimg's server, and only what the person changed.
//
// To the board, {hydev: 1, ...}: ready + tree, tree (again when the page changes, at most once a second), hover, pick {pick, shift, path,
// detail} (a press with the select tool), dbl {dbl, detail} (a double click), detail (the selected element) + more (the other selected
// ones), text {i, was, text} (typing in place ended), key: "Escape" | "z" (with shift) | "Enter" | "i" | "c" | "p"; a pick carries the element's
// key («html>body:1>main:0», the tree's row path), a css selector, its tag and text and the press's point in the page (pt) and the
// viewport (vp), so a comment can be pinned to it; where {key: [x, y] | [x, y, 1] | null}, its pin's point in the viewport, answers "where"
// (and again on scroll).
// From the board, {hydev: 2, a}: "tree"; "hl" {i | null}; "sel" {i, all, scroll}; "inspect" {on}: the select tool (a press picks instead
// of reaching the page); "marks" {on}; "source" {html, rev}: the file's source with each start tag marked by its offset (data-hy-at);
// "live" {ops}: an edit shown in the page ({i, style: {prop: value | ""}}, {i, text}, {var, value}); "type" {i}: typing in place;
// "where" {keys}: the pins' points of these elements now (see «One rule» below), and after each scroll or resize until asked for other
// keys; "zoom" {on}: the page has the zoom (the person clicked into it), its pinch stays its own; "spot" {i}: where a comment on that
// element goes, answered {spot: {i, el, pt, vp, n, pin?}} as a pick (a comment from the board's tree, treecomments.js); "unspot" {n}:
// that comment was cancelled, the boxes its spot scrolled go back.
// Zoom (owner 2026-10-08, Hyimg ui/framezoom.js): a pinch, ⌃ or ⌘ with the wheel go to the board as {zoom: {x, y, dx, dy, mode, ctrl, meta}}
// and never zoom the page, unless the page has the zoom or ⌥ is held; a press while the select tool is off sends {press: 1} (it gives the
// page the zoom). The page cannot pinch-zoom its own viewport by touch either (touch-action, in a sheet of ours outside the DOM).
// A tree node: {i: id, t: tag, d: its id attribute, c: classes, x: the text of a leaf, k: children}; at most 15000 elements (cut: true).
//
// Where an element is in the file: the source is parsed by the browser's own parser (DOMParser, no scripts run) and its tree lined up
// with the live one, level by level, by the best matching subsequence of children (tag, id, classes, own text, attributes). A live
// element with no partner was made by a script; a partner without data-hy-at was implied by the parser (a tbody, an html or body never
// written). The board gets {at, tag, text} for the file, or {why}.
(() => {
  "use strict";
  if (window.__hyDevAgent || window.parent === window) return;
  window.__hyDevAgent = true;
  const UP = window.parent, MAX = 15000, MARK = "data-hy-at";
  const ids = new WeakMap(), nodes = new Map(); let next = 1;
  const idOf = n => { let i = ids.get(n); if (!i) { i = next++; ids.set(n, i); nodes.set(i, new WeakRef(n)); } return i; };
  const byId = i => { const r = nodes.get(i), n = r && r.deref(); return n && n.isConnected ? n : null; };
  const send = m => { try { UP.postMessage(Object.assign({ hydev: 1 }, m), "*"); } catch (e) { /* the board is gone */ } };
  let host = null, R = null, hov = null, sel = null, sels = [], inspecting = false, editing = null, SRC = null, epoch = 0, zoomOwn = false;
  // the zoom goes to the board (see the top): registered first, so the page's own listeners never see a gesture that is not theirs
  const zopt = { capture: true, passive: false };
  addEventListener("wheel", e => {
    if (!(e.ctrlKey || e.metaKey) || e.altKey || zoomOwn) return;
    e.preventDefault(); e.stopImmediatePropagation();
    send({ zoom: { x: e.clientX, y: e.clientY, dx: e.deltaX, dy: e.deltaY, mode: e.deltaMode, ctrl: e.ctrlKey, meta: e.metaKey } });
  }, zopt);
  ["gesturestart", "gesturechange", "gestureend"].forEach(t => addEventListener(t, e => { if (!e.altKey && !zoomOwn) { e.preventDefault(); e.stopImmediatePropagation(); } }, zopt));
  addEventListener("pointerdown", () => { if (!inspecting && !editing) send({ press: 1 }); }, { capture: true });
  try { const zs = new CSSStyleSheet(); zs.replaceSync("html { touch-action: pan-x pan-y; }"); document.adoptedStyleSheets = [...document.adoptedStyleSheets, zs]; } catch (e) { /* an old engine */ }
  const mine = n => n === host || (n.tagName === "SCRIPT" && /\/~hyp\//.test(n.getAttribute("src") || ""));
  const clsOf = el => (el.getAttribute("class") || "").replace(/\s+/g, " ").trim();

  function tree() {
    let n = 0, cut = false;
    const walk = el => {
      if (n >= MAX) { cut = true; return null; }
      n++;
      const o = { i: idOf(el), t: el.tagName.toLowerCase() };
      if (el.id) o.d = el.id.slice(0, 120);
      const c = clsOf(el); if (c) o.c = c.slice(0, 200);
      const k = [];
      for (const ch of el.children) { if (mine(ch)) continue; const w = walk(ch); if (w) k.push(w); if (cut) break; }
      if (k.length) o.k = k;
      else if (!/^(script|style|noscript|template|svg)$/.test(o.t)) { const x = (el.textContent || "").replace(/\s+/g, " ").trim(); if (x) o.x = x.slice(0, 80); }
      return o;
    };
    return { root: document.documentElement ? walk(document.documentElement) : null, n, cut };
  }
  const pathOf = el => { const p = []; for (let e = el; e && e.nodeType === 1; e = e.parentElement) p.unshift(idOf(e)); return p; };
  // an element's place, as the board's tree keys its rows (canvas.js drawTree): the root's tag, then each element's tag and its index among
  // its parent's elements (ours left out); and a css selector for people and agents: #id, else the path of :nth-of-type from one with an id
  const kids = el => [...el.children].filter(c => !mine(c));
  const keyOf = el => { const p = []; for (let e = el; e && e.parentElement; e = e.parentElement) p.unshift(`${e.tagName.toLowerCase()}:${kids(e.parentElement).indexOf(e)}`);
    return [document.documentElement.tagName.toLowerCase(), ...p].join(">"); };
  const byKey = key => { const parts = String(key || "").split(">"); let el = document.documentElement;
    if (!el || parts[0] !== el.tagName.toLowerCase()) return null;
    for (const s of parts.slice(1)) { const [t, j] = s.split(":"); el = kids(el)[+j]; if (!el || el.tagName.toLowerCase() !== t) return null; }
    return el; };
  const cssOf = el => {
    const q = s => { try { return document.querySelectorAll(s).length === 1; } catch (e) { return false; } };
    const p = [];
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      if (e.id && q("#" + CSS.escape(e.id))) { p.unshift("#" + CSS.escape(e.id)); break; }
      const t = e.tagName.toLowerCase(), same = e.parentElement ? [...e.parentElement.children].filter(c => c.tagName === e.tagName) : [e];
      p.unshift(same.length > 1 ? `${t}:nth-of-type(${same.indexOf(e) + 1})` : t);
      if (t === "body" || t === "html") break;
    }
    return p.join(" > ");
  };
  const where = el => ({ key: keyOf(el), css: cssOf(el), tag: el.tagName.toLowerCase(), text: (el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 80) });
  // an element's box in the viewport for its pin: its own, its contents' when it draws none (display: contents: pin "kids"), its nearest
  // ancestor's when it is not drawn at all (display: none: pin "parent"); on: the element that box belongs to, to scroll into sight
  const boxOf = el => {
    if (el.getClientRects().length) return { r: el.getBoundingClientRect(), on: el };
    try {
      const rg = document.createRange(); rg.selectNodeContents(el); const r = rg.getBoundingClientRect();
      const on = [...el.querySelectorAll("*")].find(x => x.getClientRects().length);
      if ((r.width || r.height) && on) return { r, on, pin: "kids" };
    } catch (e) { /* no ranges */ }
    for (let a = el.parentElement; a; a = a.parentElement) if (a.getClientRects().length) return { r: a.getBoundingClientRect(), on: a, pin: "parent" };
    return null;
  };
  // One rule for where a pin stands on an element, in the page (owner 2026-10-08: «в дереве я точно так же смогу нажать и оставить
  // комментарий»): a point inside the part of its box one can see, the middle of a small one, 12 and 8 px in from the top left of a big
  // one (as the board's pin stands on it). The live pins (where) and a new comment (spot) both take it. "Seen" is at least 8 px of the box
  // each way, or all of a smaller one: a row flush with its list's bottom edge, or a slide flush with its slider's right one, is out of
  // sight. Out of sight, the nearest point in sight, marked edge; null when its clipping boxes are out of the viewport themselves
  const clipIn = (a, memo) => {   // what clips a's contents: the viewport cut by a and every ancestor of it that clips its overflow
    if (!a || a === document.documentElement) return { l: 0, t: 0, r: innerWidth, b: innerHeight };
    if (memo && memo.has(a)) return memo.get(a);
    const c = { ...clipIn(a.parentElement, memo) }, s = getComputedStyle(a), x = s.overflowX !== "visible", y = s.overflowY !== "visible";
    if (x || y) {
      const q = a.getBoundingClientRect(), l = q.left + a.clientLeft, t = q.top + a.clientTop;
      if (x) { c.l = Math.max(c.l, l); c.r = Math.min(c.r, l + a.clientWidth); }
      if (y) { c.t = Math.max(c.t, t); c.b = Math.min(c.b, t + a.clientHeight); }
    }
    if (memo) memo.set(a, c);
    return c;
  };
  const inside = (l, t, w, h) => [l + Math.min(w / 2, 12), t + Math.min(h / 2, 8)];
  const enough = (v, d) => v >= Math.min(d, 8);   // d = 0: a box with no width (or height) is seen when it lies inside the clip
  function sight(el, memo) {
    const b = boxOf(el); if (!b) return null;
    const c = clipIn(b.on.parentElement, memo), r = b.r, l = Math.max(r.left, c.l), t = Math.max(r.top, c.t);
    const w = Math.min(r.right, c.r) - l, h = Math.min(r.bottom, c.b) - t;
    if (enough(w, r.width) && enough(h, r.height)) return { b, p: inside(l, t, w, h) };
    if (c.r - c.l < 1 || c.b - c.t < 1) return { b, p: null };
    const [x, y] = inside(r.left, r.top, r.width, r.height), fit = (v, lo, hi) => Math.min(Math.max(v, lo), hi - 1);
    return { b, p: [fit(x, c.l, c.r), fit(y, c.t, c.b)], edge: true };
  }
  // where {key: [x, y] | [x, y, 1] (out of sight, the nearest point in sight) | null} in the viewport: the board scales it to the card
  let WATCH = [], wraf = 0;
  const sendWhere = () => {
    wraf = 0; const out = {}, memo = new Map();
    for (const k of WATCH) { const el = byKey(k), s = el && sight(el, memo); out[k] = s && s.p ? (s.edge ? [s.p[0], s.p[1], 1] : s.p) : null; }
    send({ where: out });
  };
  // where the pin of a comment from the board's tree goes: the point above; out of sight, the element is scrolled into it first (its
  // scrollers and the page); still out of sight, the nearest point in sight (pin "edge"). The answer is what a click on the element with
  // the Comment tool sends, and n: the scroll offsets it changed are given back by unspot n when the comment is cancelled (an overflow:
  // hidden slider cannot be scrolled back by hand), each only while the box is still where the comment left it
  const UNDO = new Map(); let spots = 0;
  function spot(el) {
    let s = sight(el); if (!s) return null;
    const n = ++spots;
    if (!s.p || s.edge) {
      const on = s.b.on, all = [document.scrollingElement || document.documentElement];
      for (let a = on.parentElement; a; a = a.parentElement) if (a !== all[0]) all.push(a);
      const was = all.map(a => [a.scrollLeft, a.scrollTop]);
      try { on.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "instant" }); } catch (e) { on.scrollIntoView(false); }
      const moved = all.map((a, k) => ({ a, from: was[k], to: [a.scrollLeft, a.scrollTop] })).filter(m => m.from[0] !== m.to[0] || m.from[1] !== m.to[1]);
      if (moved.length) { UNDO.set(n, moved); for (const k of UNDO.keys()) if (UNDO.size > 8) UNDO.delete(k); }
      s = sight(el) || s;
    }
    let p = s.p, pin = s.b.pin || "";
    if (!p || s.edge) {
      pin = "edge";
      if (!p) { const r = s.b.r, [x, y] = inside(r.left, r.top, r.width, r.height); p = [Math.min(Math.max(x, 0), innerWidth - 1), Math.min(Math.max(y, 0), innerHeight - 1)]; }
    }
    return Object.assign({ el: where(el), vp: p, pt: [p[0] + scrollX, p[1] + scrollY], n }, pin ? { pin } : {});
  }
  function unspot(n) {
    const moved = UNDO.get(n); UNDO.delete(n); if (!moved) return;
    for (const m of moved) {
      if (Math.abs(m.a.scrollLeft - m.to[0]) > 1 || Math.abs(m.a.scrollTop - m.to[1]) > 1) continue;   // the person scrolled it since
      try { m.a.scrollTo({ left: m.from[0], top: m.from[1], behavior: "instant" }); } catch (e) { m.a.scrollLeft = m.from[0]; m.a.scrollTop = m.from[1]; }
    }
  }
  const watchLater = () => { if (WATCH.length && !wraf) wraf = requestAnimationFrame(sendWhere); };
  addEventListener("scroll", watchLater, { passive: true, capture: true }); addEventListener("resize", watchLater);

  /* ---------- the element in the file ---------- */
  const own = el => { let s = ""; for (const c of el.childNodes) if (c.nodeType === 3) s += c.data; return s.replace(/\s+/g, " ").trim().slice(0, 200); };
  const names = el => [...el.attributes].map(a => a.name).filter(n => !/^(style|class|id|contenteditable|data-hy-at)$/.test(n)).sort().join(" ");
  function weight(l, s) {
    if (l.localName !== s.localName) return 0;
    let w = 1;
    const li = l.getAttribute("id"), si = s.getAttribute("id");
    if (li || si) { if (li !== si) return .2; w += 4; }
    if (clsOf(l) === clsOf(s)) w += 2;
    if (own(l) === own(s)) w += 3;
    if (names(l) === names(s)) w += 1;
    return w;
  }
  // the live children paired with the file's: the heaviest common subsequence (a script's element in between pairs with nothing)
  const pairs = new WeakMap();
  function align(lp, sp) {
    const c = pairs.get(lp); if (c && c.e === epoch && c.sp === sp) return c.m;
    const L = [...lp.children].filter(x => !mine(x)), S = [...sp.children], n = L.length, m = S.length, map = new Map();
    if (n * m > 4e6) { L.forEach((x, k) => { if (S[k] && weight(x, S[k]) >= 1) map.set(x, S[k]); }); }
    else {
      const W = new Float64Array((n + 1) * (m + 1)), at = (i, j) => i * (m + 1) + j;
      for (let i = 1; i <= n; i++) for (let j = 1; j <= m; j++) {
        const w = weight(L[i - 1], S[j - 1]);
        W[at(i, j)] = Math.max(W[at(i - 1, j)], W[at(i, j - 1)], w > 0 ? W[at(i - 1, j - 1)] + w : 0);
      }
      for (let i = n, j = m; i > 0 && j > 0;) {
        const w = weight(L[i - 1], S[j - 1]);
        if (w > 0 && W[at(i, j)] === W[at(i - 1, j - 1)] + w) { map.set(L[i - 1], S[j - 1]); i--; j--; }
        else if (W[at(i - 1, j)] >= W[at(i, j - 1)]) i--; else j--;
      }
    }
    pairs.set(lp, { e: epoch, sp, m: map });
    return map;
  }
  const LEAF_NO = /^(script|style|svg|img|input|br|hr|textarea|select|video|audio|canvas|iframe|template|object|embed|math)$/;
  function srcOf(el) {
    if (!SRC) return { why: "wait" };
    if (el === host) return { why: "script" };
    const chain = []; for (let e = el; e; e = e.parentElement) chain.unshift(e);
    if (chain[0] !== document.documentElement) return { why: "script" };
    let s = SRC.doc.documentElement;
    for (let k = 1; k < chain.length && s; k++) s = align(chain[k - 1], s).get(chain[k]) || null;
    if (!s) return { why: "script" };
    const at = s.getAttribute(MARK);
    if (at === null) return { why: "implied" };
    const o = { at: +at, tag: s.localName, rev: SRC.rev };
    if (!el.children.length && !s.children.length && !LEAF_NO.test(s.localName)) o.text = s.textContent;
    return o;
  }

  /* ---------- where a value comes from: the rules of the page's readable sheets (a linked sheet of another address is not readable) ---------- */
  const EP = ["color", "background-color", "border-color", "border-width", "border-style", "border-radius", "font-size", "font-weight", "opacity", "padding", "gap", "width", "height"];
  const INH = new Set(["color", "font-size", "font-weight"]);
  const SHORT = { "background-color": ["background"], "border-color": ["border"], "border-width": ["border"], "border-style": ["border"], "font-size": ["font"], "font-weight": ["font"] };
  const splitTop = s => {   // a selector list split at its top-level commas
    const out = []; let d = 0, b = 0;
    for (let i = 0; i < s.length; i++) { const c = s[i]; if (c === "(" || c === "[") d++; else if (c === ")" || c === "]") d--; else if (c === "," && !d) { out.push(s.slice(b, i)); b = i + 1; } }
    out.push(s.slice(b)); return out.map(x => x.trim()).filter(Boolean);
  };
  const specOf = s => { s = s.replace(/:where\([^)]*\)/g, "").replace(/::?[\w-]+\(/g, m => /:(not|is|has)\(/.test(m) ? " (" : m);
    return (s.match(/#[\w-]+/g) || []).length * 1e6 + (s.match(/\.[\w-]+|\[[^\]]*\]|:(?!:)[\w-]+/g) || []).length * 1e3 + (s.match(/(^|[\s>+~(])[a-zA-Z][\w-]*/g) || []).length; };
  let RULES = null;
  function rules() {
    if (RULES && RULES.e === epoch) return RULES.l;
    const l = [];
    const walk = list => { for (const r of list) {
      if (r.selectorText !== undefined && r.style) l.push(r);
      else if (r.cssRules) { if (r.media && r.media.mediaText && !matchMedia(r.media.mediaText).matches) continue; try { walk(r.cssRules); } catch (e) { /* unreadable */ } }
    } };
    for (const sh of document.styleSheets) {
      if (sh.disabled || (sh.media && sh.media.mediaText && !matchMedia(sh.media.mediaText).matches)) continue;
      let rs; try { rs = sh.cssRules; } catch (e) { continue; }
      walk(rs);
    }
    RULES = { e: epoch, l }; return l;
  }
  const decl = (st, p) => {   // [value, priority] of a property in a declaration block, from its shorthand when the longhand waits for a var()
    const v = st.getPropertyValue(p); if (v) return [v, st.getPropertyPriority(p)];
    for (const s of SHORT[p] || []) { const w = st.getPropertyValue(s); if (w) return [w, st.getPropertyPriority(s)]; }
    return null;
  };
  function specified(el, props) {
    const hits = [], all = rules();
    all.forEach((r, k) => {
      let best = -1;
      for (const part of splitTop(r.selectorText)) { try { if (el.matches(part)) best = Math.max(best, specOf(part)); } catch (e) { /* a selector this browser can't match */ } }
      if (best >= 0) hits.push({ r, s: best, k });
    });
    const out = {};
    for (const p of props) {
      let top = null;
      for (const h of hits) { const d = decl(h.r.style, p); if (!d) continue; const key = [d[1] ? 1 : 0, h.s, h.k];
        if (!top || key[0] > top.key[0] || (key[0] === top.key[0] && (key[1] > top.key[1] || (key[1] === top.key[1] && key[2] > top.key[2])))) top = { v: d[0], key }; }
      const inl = decl(el.style, p);
      if (inl && (!top || !top.key[0] || inl[1])) top = { v: inl[0], key: [inl[1] ? 1 : 0, 1e9, 0] };
      if (top) out[p] = top.v;
    }
    return out;
  }
  const varIn = (v, p) => {   // the custom property a value is, or the one colour property inside a shorthand
    const m = /^\s*var\(\s*(--[\w-]+)\s*(?:,[^)]*)?\)\s*$/.exec(v); if (m) return m[1];
    const all = [...v.matchAll(/var\(\s*(--[\w-]+)/g)]; return all.length === 1 && /color/.test(p) ? all[0][1] : null;
  };
  function edInfo(el) {
    const cs = getComputedStyle(el), here = specified(el, EP), out = {};
    for (const p of EP) {
      const v = p === "padding" ? sides(cs, "padding") : p === "border-width" ? sides(cs, "border", "-width") : p === "border-color" ? cs.getPropertyValue("border-top-color")
        : p === "border-style" ? cs.getPropertyValue("border-top-style") : p === "border-radius" ? cs.getPropertyValue("border-top-left-radius") : cs.getPropertyValue(p);
      const o = { v: String(v) }, inl = el.style.getPropertyValue(p); if (inl) o.inl = inl;
      let set = here[p], up = null;
      if (!set && INH.has(p)) for (let a = el.parentElement, n = 0; a && n < 40; a = a.parentElement, n++) { const s = specified(a, [p])[p]; if (s) { set = s; up = a.tagName.toLowerCase(); break; } }
      if (set) { o.set = set; const m = varIn(set, p); if (m) { o.var = m; o.varVal = getComputedStyle(document.documentElement).getPropertyValue(m).trim(); if (up) o.from = up; } }
      out[p] = o;
    }
    return { p: out, flex: /flex|grid/.test(cs.display) };
  }

  // the four sides of a box property as CSS writes them short: «0px», «8px 16px», «1px 2px 3px 4px»
  function sides(cs, pre, post = "") {
    const v = ["top", "right", "bottom", "left"].map(s => cs.getPropertyValue(`${pre}-${s}${post}`));
    return v[0] === v[1] && v[1] === v[2] && v[2] === v[3] ? v[0] : v[0] === v[2] && v[1] === v[3] ? `${v[0]} ${v[1]}` : v.join(" ");
  }
  const KEYS = ["display", "position", "box-sizing", "width", "height", "margin", "padding", "border-width", "border-radius", "color", "background-color",
    "font-family", "font-size", "font-weight", "line-height", "opacity", "z-index", "overflow", "flex-direction", "gap"];
  function detail(el) {
    const r = el.getBoundingClientRect(), cs = getComputedStyle(el), flex = /flex|grid/.test(cs.display);
    const val = k => k === "margin" ? sides(cs, "margin") : k === "padding" ? sides(cs, "padding") : k === "border-width" ? sides(cs, "border", "-width")
      : k === "border-radius" ? cs.getPropertyValue("border-top-left-radius") : cs.getPropertyValue(k);
    const styles = KEYS.filter(k => flex || (k !== "flex-direction" && k !== "gap")).map(k => [k, String(val(k)).slice(0, 160)]);
    const r1 = v => Math.round(v * 10) / 10;
    const d = { i: idOf(el), t: el.tagName.toLowerCase(), d: el.id || "", c: [...el.classList].slice(0, 40), kids: el.children.length,
      attrs: [...el.attributes].filter(a => a.name !== "contenteditable").slice(0, 60).map(a => [a.name, a.value.slice(0, 500)]),
      box: { x: r1(r.left + scrollX), y: r1(r.top + scrollY), w: r1(r.width), h: r1(r.height) }, styles, path: pathOf(el) };
    try { d.src = srcOf(el); d.ed = edInfo(el); } catch (e) { d.src = { why: "error", msg: String(e && e.message || e).slice(0, 120) }; }
    return d;
  }
  const brief = el => {   // another selected element: where it is in the file, and its inline values (an undo puts them back)
    const o = { i: idOf(el), t: el.tagName.toLowerCase(), inl: {} };
    try { o.src = srcOf(el); for (const p of EP) { const v = el.style.getPropertyValue(p); if (v) o.inl[p] = v; } } catch (e) { o.src = { why: "error" }; }
    return o;
  };
  const sendSel = () => send({ detail: sel && sel.isConnected ? detail(sel) : null, more: sels.filter(e => e !== sel && e.isConnected).map(brief), rev: SRC && SRC.rev });

  /* ---------- the marks: a closed shadow root on one element of ours, fixed over the page, never catching the pointer (but the select tool's catcher) ---------- */
  function ensure() {
    if (host) return;
    host = document.createElement("hy-dev-marks");
    host.setAttribute("style", "all:initial;position:fixed;left:0;top:0;width:0;height:0;z-index:2147483647;pointer-events:none");
    R = host.attachShadow({ mode: "closed" });
    R.innerHTML = `<style>
      .b{position:fixed;box-sizing:border-box;pointer-events:none;display:none;border-radius:2px}
      .h{background:rgba(10,132,255,.16);outline:1px solid rgba(10,132,255,.95)}
      .s{outline:2px solid #0a84ff;outline-offset:-1px}
      .s.t{outline-style:dashed}
      .l{position:fixed;display:none;font:600 11px/1 -apple-system,system-ui,sans-serif;color:#fff;background:#0a84ff;padding:4px 6px;border-radius:5px;white-space:nowrap;pointer-events:none}
      .c{position:fixed;inset:0;display:none;pointer-events:auto;cursor:default;background:transparent}
    </style><div class="b h"></div><div class="b s"></div><div class="l"></div><div class="c"></div>`;
    (document.documentElement || document).appendChild(host);
    const c = R.querySelector(".c");
    const under = (x, y) => { c.style.pointerEvents = "none"; const el = document.elementFromPoint(x, y); c.style.pointerEvents = "auto"; return el && el !== host ? el : null; };
    c.addEventListener("pointermove", e => { const el = under(e.clientX, e.clientY); if (el && el !== hov) { hov = el; place(); send({ hover: idOf(el) }); } });
    c.addEventListener("pointerleave", () => { hov = null; place(); send({ hover: null }); });
    c.addEventListener("pointerdown", e => {
      e.preventDefault(); e.stopPropagation();
      const el = under(e.clientX, e.clientY); if (!el) return;
      if (!e.shiftKey) { sel = el; sels = [el]; } hov = null; place();
      send({ pick: idOf(el), shift: !!e.shiftKey, path: pathOf(el), detail: detail(el), el: where(el), pt: [e.clientX + scrollX, e.clientY + scrollY], vp: [e.clientX, e.clientY] });
    });
    c.addEventListener("dblclick", e => { e.preventDefault(); e.stopPropagation(); const el = under(e.clientX, e.clientY); if (el) send({ dbl: idOf(el), path: pathOf(el), detail: detail(el) }); });
    ["click", "mousedown", "mouseup", "contextmenu"].forEach(t => c.addEventListener(t, e => { e.preventDefault(); e.stopPropagation(); }));
  }
  const catcher = () => R && R.querySelector(".c");
  function box(b, el) {
    if (!el || !el.isConnected) { b.style.display = "none"; return null; }
    const r = el.getBoundingClientRect();
    Object.assign(b.style, { display: "block", left: r.left + "px", top: r.top + "px", width: r.width + "px", height: r.height + "px" });
    return r;
  }
  let raf = 0;
  function place() {
    if (!host) return;
    const [h, s, l] = [R.querySelector(".h"), R.querySelector(".s"), R.querySelector(".l")];
    const rh = box(h, editing ? null : hov); box(s, sel); s.classList.toggle("t", !!editing);
    const extra = sels.filter(e => e !== sel), have = [...R.querySelectorAll(".b.x")];
    while (have.length < extra.length) { const b = document.createElement("div"); b.className = "b s x"; R.appendChild(b); have.push(b); }
    have.forEach((b, k) => box(b, extra[k] || null));
    const el = (editing ? null : hov) || sel, r = el && el.isConnected ? (rh || el.getBoundingClientRect()) : null;
    if (!r) { l.style.display = "none"; return; }
    const c = clsOf(el).split(" ").filter(Boolean).slice(0, 2).map(x => "." + x).join("");
    l.textContent = `${el.tagName.toLowerCase()}${el.id ? "#" + el.id : ""}${c}  ${Math.round(r.width)} × ${Math.round(r.height)}`;
    l.style.display = "block";
    const below = r.top < 26, y = below ? Math.min(innerHeight - 22, r.bottom + 4) : r.top - 22;
    l.style.left = Math.max(2, Math.min(innerWidth - l.offsetWidth - 2, r.left)) + "px"; l.style.top = y + "px";
  }
  const later = () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; place(); }); };
  addEventListener("scroll", later, true); addEventListener("resize", later);

  /* ---------- an edit shown in the page, and typing an element's text in place ---------- */
  function setVar(name, value) {
    for (const r of rules()) {
      if (!/(^|,)\s*(:root|html)\s*(,|$)/i.test(r.selectorText) || !r.style.getPropertyValue(name) || (r.parentRule && r.parentRule.media)) continue;
      r.style.setProperty(name, value); return;
    }
    document.documentElement.style.setProperty(name, value);
  }
  function live(ops) {
    for (const o of ops || []) {
      if (o.var) { setVar(o.var, o.value); continue; }
      const el = byId(o.i); if (!el) continue;
      if (o.style) for (const [p, v] of Object.entries(o.style)) { if (v) el.style.setProperty(p, v); else el.style.removeProperty(p); }
      if (typeof o.text === "string" && !el.children.length) el.textContent = o.text;
    }
    later();
  }
  function type(i) {
    const el = byId(i); if (!el || el.children.length || editing || LEAF_NO.test(el.localName)) return;
    ensure();
    const prev = el.getAttribute("contenteditable"), was = el.textContent;
    el.setAttribute("contenteditable", "plaintext-only"); if (el.contentEditable !== "plaintext-only") el.setAttribute("contenteditable", "true");
    editing = { el, i, was, prev }; const c = catcher(); if (c) c.style.display = "none";
    el.focus({ preventScroll: true });
    try { const rg = document.createRange(); rg.selectNodeContents(el); const s = getSelection(); s.removeAllRanges(); s.addRange(rg); } catch (e) { /* no selection API */ }
    const key = e => { if ((e.key === "Enter" && !e.shiftKey) || e.key === "Escape") { e.preventDefault(); e.stopPropagation(); finish(); } };
    el.addEventListener("keydown", key); el.addEventListener("blur", finish);
    editing.off = () => { el.removeEventListener("keydown", key); el.removeEventListener("blur", finish); };
    place();
  }
  function finish() {
    const e = editing; if (!e) return; editing = null; e.off();
    if (e.prev === null) e.el.removeAttribute("contenteditable"); else e.el.setAttribute("contenteditable", e.prev);
    try { getSelection().removeAllRanges(); } catch (x) { /* none */ }
    const c = catcher(); if (c) c.style.display = inspecting ? "block" : "none";
    place(); send({ text: { i: e.i, was: e.was, text: e.el.textContent } });
  }
  // while typing, a press outside the element ends it and never reaches the page (these listeners are the page's first)
  ["pointerdown", "mousedown", "click"].forEach(t => addEventListener(t, e => {
    if (!editing || editing.el.contains(e.target)) return;
    e.preventDefault(); e.stopPropagation(); if (t === "pointerdown") finish();
  }, true));

  // the page changed (a script added rows, a class flipped): the tree again, at most once a second
  let mt = 0, last = 0;
  const changed = () => { clearTimeout(mt); mt = setTimeout(() => { last = Date.now(); send({ tree: tree() }); if (sel) { if (sel.isConnected && !editing) sendSel(); later(); } }, Math.max(300, 1000 - (Date.now() - last))); };
  new MutationObserver(ms => { if (ms.every(m => host && (m.target === host || host.contains(m.target) || [...m.addedNodes].every(n => n === host)))) return; epoch++; changed(); })
    .observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["id", "class"] });

  addEventListener("message", e => {
    const d = e.data; if (e.source !== UP || !d || d.hydev !== 2) return;
    if (d.a === "tree") send({ tree: tree() });
    else if (d.a === "hl") { ensure(); hov = d.i ? byId(d.i) : null; place(); }
    else if (d.a === "sel") {
      ensure(); sel = d.i ? byId(d.i) : null; hov = null;
      sels = [...new Set([sel, ...(d.all || []).map(byId)])].filter(Boolean);
      if (sel && d.scroll) { const r = sel.getBoundingClientRect(); if (r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth) sel.scrollIntoView({ block: "center", inline: "nearest" }); }
      place(); sendSel();
    }
    else if (d.a === "marks") { if (host) host.style.display = d.on ? "" : "none"; }
    else if (d.a === "zoom") zoomOwn = !!d.on;
    else if (d.a === "inspect") { ensure(); inspecting = !!d.on; catcher().style.display = inspecting && !editing ? "block" : "none"; if (!inspecting) { hov = null; place(); } }
    else if (d.a === "source" && typeof d.html === "string") {
      try { SRC = { doc: new DOMParser().parseFromString(d.html, "text/html"), rev: d.rev }; epoch++; } catch (x) { SRC = null; }
      if (sel) sendSel(); else send({ rev: d.rev, detail: null, more: [] });
    }
    else if (d.a === "live") live(d.ops);
    else if (d.a === "type") type(d.i);
    else if (d.a === "where") { WATCH = (d.keys || []).slice(0, 200).map(String); sendWhere(); }
    else if (d.a === "spot") { const el = byId(d.i); send({ spot: Object.assign({ i: d.i }, el && spot(el)) }); }
    else if (d.a === "unspot") unspot(d.n);
  });
  // keys the board takes while the page has the focus: Esc, ⌘Z and ⇧⌘Z, I, Enter to type a selected text; never while the page's own field has it
  addEventListener("keydown", e => {
    if (editing) return;
    const a = document.activeElement, field = a && (a.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName));
    if (e.key === "Escape") send({ key: "Escape" });
    else if (field) return;
    else if ((e.metaKey || e.ctrlKey) && !e.altKey && (e.key === "z" || e.key === "я" || e.key === "Z")) { e.preventDefault(); send({ key: "z", shift: e.shiftKey }); }
    else if (e.key === "Enter" && inspecting && sel) { e.preventDefault(); send({ key: "Enter" }); }
    // I turns the select tool on and off also while the page takes the clicks (it opens so, owner 2026-10-08), unless one of its fields is typed in
    else if (!e.metaKey && !e.ctrlKey && !e.altKey && /^[iIшШ]$/.test(e.key)) { e.preventDefault(); send({ key: "i" }); }
    else if (inspecting && !e.metaKey && !e.ctrlKey && !e.altKey && /^[cCсСpPзЗ]$/.test(e.key)) {   // C a comment on an element, P draw over the page
      e.preventDefault(); send({ key: /^[cCсС]$/.test(e.key) ? "c" : "p" }); }
  }, true);
  const ready = () => send({ ready: true, tree: tree(), title: document.title || "", vw: innerWidth, vh: innerHeight });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready, { once: true }); else ready();
  addEventListener("load", () => send({ tree: tree() }), { once: true });
})();
