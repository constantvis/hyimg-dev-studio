// The HTML card at rest: its still and, big on screen, its live page (owner 2026-10-08: «не всегда рендерится в высоком разрешении,
// справа мазня, не видно что там»: two cards side by side at 153 % on a Retina screen, the left one live, the right one a 640 px still
// blown up to 2200 device px).
//
// Live pages. At most LIVE_MAX at a time. Each pass of the board's view (its view hook) ends in one pass here over every HTML card it saw:
// the cards on screen and big (from BIG px wide, a live one keeps its page down to SMALL) get the pages, the selected card first, then the
// nearest the centre of the view. A card outside the screen never holds a page a card on screen wants: the board's view pass reaches half
// a screen around it, and before 2026-10-08 the cards first in the board's order took the four pages there, off screen, so the cards in
// view got none. While the board moves (a pan, a zoom, a drag) no page starts and an off-screen one is kept, so a pan back costs no reload;
// the pass runs again 220 ms after the last move, and at rest the pages are given out anew: off-screen ones go, a card that lost its page
// gets it back as soon as one frees.
//
// Stills. The server draws the page at the card's own viewport (vw × vh css px, the live page's) at twice its css size (render.py: a
// 1440 × 900 card is drawn 2880 × 1800) and /thumb hands it out 640, 1280 or 2560 px wide. A
// card asks for the step its width on screen needs in device pixels (width × zoom × devicePixelRatio): a sharper one fades in over the one
// shown once decoded, so nothing flickers; mid-gesture a card keeps the one it has; zoomed out it steps back down (a 2560 still is 16 MB
// decoded), and a card off screen asks for nothing.
export const TYPE = "html";
export const BIG = 360, SMALL = 280, LIVE_MAX = 4, STEPS = [640, 1280, 2560], AGAIN_MS = 220, FADE_MS = 240;
const enc = encodeURIComponent;

// the still for a card that is `dev` device pixels wide on screen: the smallest step at most 10 % short of it
export const stepFor = dev => STEPS.find(s => dev <= s * 1.1) || STEPS[STEPS.length - 1];
// the step a card showing `cur` moves to: up as soon as it needs more, down only once it needs clearly less (no swaps back and forth
// at a boundary while the zoom wavers)
export function nextStep(cur, dev) {
  const need = stepFor(dev);
  if (!cur || need > cur) return need;
  return stepFor(dev * 1.25) < cur ? stepFor(dev * 1.25) : cur;
}

// which cards start a page and which stop one, from [{id, live, vis, px, d, sel, gone}]: live has (or is getting) a page, vis is on
// screen, px its width on screen in css px, d its squared distance from the view's centre in board units, sel selected, gone hidden by
// the board (outside its view pass) or no more an HTML card
export function plan(cards, { moving = false, max = LIVE_MAX, big = BIG, small = SMALL } = {}) {
  const rank = (a, b) => (b.sel - a.sel) || (a.d - b.d) || (b.px - a.px);
  const want = cards.filter(c => !c.gone && c.vis && (c.px >= big || (c.live && c.px >= small))).sort(rank).slice(0, max);
  const keep = new Set(want.map(c => c.id)), stop = [];
  const live = cards.filter(c => c.live);
  // a page goes when its card got small or left the board's view pass, and at rest when it is off screen
  for (const c of live) if (!keep.has(c.id) && (c.gone || c.px < small || (!moving && !c.vis))) stop.push(c.id);
  const start = moving ? [] : want.filter(c => !c.live).map(c => c.id);
  // cards on screen that lost to nearer ones give up their pages, the farthest first, as many as start
  let room = max - live.length + stop.length;
  const rest = live.filter(c => !keep.has(c.id) && !stop.includes(c.id)).sort((a, b) => b.d - a.d);
  while (room < start.length && rest.length) { stop.push(rest.shift().id); room++; }
  return { start: start.slice(0, Math.max(0, room)), stop };
}

export function makeCards(HY, { mark, pathUrl, vwOf, vhOf, devId }) {
  let BASE = null, pass = false, again = 0, MOVING = false, SW = 0, SH = 0;
  const LIVE = new Set();   // cards that show their page at rest
  const BUST = new Map();   // library path -> the file's revision after Dev mode wrote it: the card's picture is drawn again
  const ELS = new Map();    // card id -> its element, every HTML card the view pass reported
  // where sandboxed library pages are served (Hyimg's server, /api/sandbox): one key per server start, asked once at a time (it may wait
  // behind the browser's six connections, all of them busy with stills being drawn); a failed ask is asked again a second later
  let asking = null;
  function base() {
    if (BASE) return Promise.resolve(BASE);
    return asking || (asking = fetch("/api/sandbox").then(r => r.ok ? r.json() : null).then(j => { BASE = (j && j.base) || null; }, () => {})
      .then(() => { asking = null; if (!BASE) setTimeout(schedule, 1000); return BASE; }));
  }
  // the stage's size, kept by an observer: read in the pass it would force a layout right after the view pass restyled the cards
  const box = () => { const r = HY.stage.getBoundingClientRect(); SW = r.width; SH = r.height; };
  box(); new ResizeObserver(box).observe(HY.stage);

  // the page drawn at the card's own viewport (vw × vh css px, as its live page lays out: a 1440 card drawn at 1280 jumped when the page
  // faded in, owner 2026-10-08); 1280 × 800 is the library's picture, asked for plainly
  function stillUrl(it, s) {
    const vw = vwOf(it), vh = vhOf(it), view = vw === 1280 && vh === 800 ? "" : `&vw=${vw}&vh=${vh}`;
    return `/thumb?p=${enc(it.src)}&s=${s}${view}${BUST.has(it.src) ? "&v=" + BUST.get(it.src) : ""}`;
  }
  const shown = el => el.querySelector(":scope > img.dvi:not(.dvo)");
  // the still u in the card: at once when nothing shows yet, else decoded first and faded in over the one shown, which then goes
  function swap(el, u) {
    const img = shown(el); if (!img || el._next === u) return;
    if (img._u === u) { el._next = null; return; }   // the one shown is wanted again: a sharper one on its way is not put over it
    if (!img._u || !img.complete || !img.naturalWidth) { el._next = null; img._u = u; img.src = u; return; }
    el._next = u;
    const nu = new Image(); nu.className = "dvi"; nu.alt = ""; nu.draggable = false; nu.decoding = "async"; nu.src = u;
    nu.decode().then(() => {
      if (el._next !== u || !img.isConnected) return;
      el._next = null; nu._u = u; img.classList.add("dvo"); img.after(nu);
      const a = nu.animate([{ opacity: 0 }, { opacity: 1 }], { duration: FADE_MS, easing: "cubic-bezier(.32,.72,0,1)" });
      a.onfinish = a.oncancel = () => img.remove();
    }, () => { if (el._next === u) el._next = null; });
  }
  // the card drawn by the board (its render hook): the still at the step it has (640 until the view pass says more), the page's size
  function card(el, it) {
    if (!shown(el)) {
      el.insertAdjacentHTML("afterbegin", `<img class="dvi" alt="" decoding="async" draggable="false">${mark()}`);
      shown(el).addEventListener("load", () => el.classList.add("lo"), { once: true });
    }
    swap(el, stillUrl(it, el._s || STEPS[0]));
    if (el._pv) sizeTo(el._pv, it);
  }
  function sizeTo(f, it) { const vw = vwOf(it); Object.assign(f.style, { width: vw + "px", height: vhOf(it) + "px", transform: `scale(${it.w / vw})` }); }

  function preview(id, el, it) {
    if (el._pv) return;
    if (!BASE) { base().then(b => { if (b) schedule(); }); return; }
    const f = document.createElement("iframe"); f.className = "dvpg"; f.setAttribute("sandbox", "allow-scripts"); f.tabIndex = -1; f.setAttribute("aria-hidden", "true");
    f.addEventListener("load", () => el.classList.add("pv"), { once: true });
    sizeTo(f, it); f.src = BASE + pathUrl(it.src); el.appendChild(f); el._pv = f; LIVE.add(id);
  }
  function unpreview(id, el) { LIVE.delete(id); if (!el || !el._pv) return; el._pv.remove(); el._pv = null; el.classList.remove("pv"); }

  // the board's view hook: the card's width on screen (0 outside the view pass), whether the board moves
  function view(id, el, px, moving) {
    if (devId() === id) return;
    const it = HY.board.items[id]; if (!it) return;
    ELS.set(id, el); MOVING = !!moving; schedule();
  }
  // the still a card on screen needs now
  function sharpen(c) {
    const s = nextStep(c.el._s, c.px * (devicePixelRatio || 1));
    if (s !== c.el._s) { c.el._s = s; swap(c.el, stillUrl(c.it, s)); }
  }
  function schedule() { if (!pass) { pass = true; queueMicrotask(() => { pass = false; give(); }); } }
  // the pass over all the cards: who gets a page
  function give() {
    clearTimeout(again);
    const moving = MOVING || HY.dragging, z = HY.cam.z, ins = parseFloat(document.documentElement.style.getPropertyValue("--inset")) || 0;
    const x0 = HY.cam.x + ins / z, y0 = HY.cam.y, x1 = HY.cam.x + SW / z, y1 = HY.cam.y + SH / z, cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    const cards = [];
    for (const [id, el] of ELS) {
      const it = HY.board.items[id];
      if (!it || it.type !== TYPE || !el.isConnected) { unpreview(id, el); ELS.delete(id); continue; }
      if (devId() === id) continue;
      const dx = Math.max(it.x - cx, 0, cx - it.x - it.w), dy = Math.max(it.y - cy, 0, cy - it.y - it.h);
      cards.push({ id, el, it, live: !!el._pv, vis: it.x < x1 && it.x + it.w > x0 && it.y < y1 && it.y + it.h > y0, px: it.w * z, d: dx * dx + dy * dy,
        sel: HY.sel && HY.sel.has(id) ? 1 : 0, gone: el.hidden });
    }
    if (!moving) cards.forEach(c => { if (c.vis && !c.gone) sharpen(c); });
    const p = plan(cards, { moving }), by = new Map(cards.map(c => [c.id, c]));
    p.stop.forEach(id => unpreview(id, by.get(id).el));
    p.start.forEach(id => { const c = by.get(id); preview(id, c.el, c.it); });
    if (moving) again = setTimeout(give, AGAIN_MS);   // the board may stop without another view pass (a drag let go)
  }

  base();
  return { card, view, sizeTo, unpreview, base, LIVE, BUST, stillUrl, give, get dbg() { return { MOVING, dragging: HY.dragging, BASE, n: ELS.size, again, SW, SH }; } };
}
