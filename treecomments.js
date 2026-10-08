// Comments from Dev Studio's element tree (owner 2026-10-08: «в дереве слева я могу выбрать именно нужный элемент ... но я не могу нажать
// на него и сделать комментарий ... А что если в дереве я точно так же смогу нажать и оставить комментарий? Оно у меня покажется уже на
// канвасе»). Any row starts a thread on its element: the comment button on the row under the pointer or the selected one, «Comment» in the
// row's right-click menu, C while the tree has the focus and a row is selected. The row is selected, the page brings the element into sight
// and says where its pin goes (agent.js «spot»), and the board's own composer opens there (Hyimg ui/comments.js newAt) with the anchor a
// click on that element with the Comment tool makes: the pin stands on the card as if the element had been clicked, the thread lists in
// hy.py comments with its element, @mentions and the bell work as for any comment. An element too small or covered to hit takes its box
// all the same; one that draws no box (display: contents) its contents', one not drawn at all (display: none) its nearest ancestor's, one
// a clipping box hides the nearest point in sight; the thread's element says so (pin: kids, parent, edge).
// A row with open threads shows their count (a click opens the newest, again the next one) and, under the pointer or selected, a «+» for
// another thread; a folded row with threads inside, a dot. A comment cancelled gives back the scroll the page took to show its element.
// The row under the pointer lights its pins on the board, and a pin opened on the board selects its row.

// the node of a row path «html>body:1>main:0» in the page's tree (canvas.js drawTree keys the rows so), with the ids of the rows above it
export function nodeAt(root, key) {
  const parts = String(key || "").split(">"), path = []; let n = root;
  if (!n || parts[0] !== n.t) return null;
  for (const s of parts.slice(1)) {
    const [tag, j] = s.split(":"); path.push(n.i); n = (n.k || [])[+j];
    if (!n || n.t !== tag) return null;
  }
  return { n, path };
}

export function makeTreeComments({ D, HY, t, esc, toPage, select, comment, drawTree }) {
  const CM = () => window.hyComments;
  let MAP = new Map(), sig = "";
  // the open threads on this card's elements by row path, newest first, of the authors the board shows (Annotate's filter)
  function count() {
    const d = D(), m = new Map(), c = CM(); MAP = m; sig = "";
    if (!d || !c || !c.threads) return;
    const seen = window.hyAnnot && hyAnnot.visible ? b => hyAnnot.visible(b) : () => true;
    for (const th of c.threads()) {
      const k = th.element && th.element.key;
      if (th.resolved || !k || !th.anchor || th.anchor.obj !== d.id || !seen(th.by)) continue;
      if (!m.has(k)) m.set(k, []); m.get(k).push(th);
    }
    for (const l of m.values()) l.sort((a, b) => String(b.updated || "").localeCompare(String(a.updated || "")));
    sig = [...m].map(([k, l]) => k + "=" + l.map(x => x.id).join(",")).join("|");
  }
  // a row's mark, drawn with it: its threads' count, a click opens them; a folded row with threads further in, a dot
  function mark(key, folded) {
    const l = MAP.get(key);
    if (l) return `<hy-button class="dvcn" size="s" variant="ghost" icon="comment" data-cm-keep title="${esc(t("{n} comments: open", { n: l.length }))}">${l.length}</hy-button>`;
    if (folded && MAP.size) for (const k of MAP.keys()) if (k.startsWith(key + ">")) return `<hy-badge class="dvcd" dot title="${esc(t("Comments inside"))}"></hy-badge>`;
    return "";
  }
  // the comment button: one for the tree, it stands on the row under the pointer, else on the selected one; on a row with threads it is a
  // «+» before their count, a new thread on the same element (the count opens the ones there are)
  function place(row) {
    const d = D(); if (!d) return;
    if (!d.cmb) { const b = d.cmb = document.createElement("hy-icon-button"); b.className = "dvcb"; b.setAttribute("size", "s"); }
    const box = d.ui.tree, r = row || box.querySelector(".row.hov") || (d.sel ? box.querySelector(`.row[data-i="${d.sel}"]`) : null);
    if (!r) { d.cmb.remove(); return; }
    const n = r.querySelector(".dvcn"), set = (k, v) => { if (d.cmb.getAttribute(k) !== v) d.cmb.setAttribute(k, v); };
    set("icon", n ? "plus" : "comment"); set("label", n ? t("New comment on this element · C") : t("Comment on this element · C"));
    if (d.cmb.parentNode !== r || d.cmb.nextSibling !== n) r.insertBefore(d.cmb, n);
  }
  // the row under the pointer (null: none): its pins lit on the board, the button on it
  function hover(row) {
    const c = CM(), l = row && MAP.get(row.dataset.p);
    if (c && c.light) c.light(l ? l.map(x => x.id) : []);
    place(row);
  }
  // a new thread on row i's element: the row selected, the page asked where the element is (the answer comes to spot)
  function start(i) {
    const d = D(); if (!d || !d.tree || !i) return;
    if (!(d.sels.size === 1 && d.sel === i)) select(i, true);
    d.spot = i; clearTimeout(d.spotT); toPage({ a: "spot", i });
    d.spotT = setTimeout(() => { const e = D(); if (e && e.spot === i) { e.spot = null; HY.toast(t("The page did not say where this element is"), "info"); } }, 2500);
  }
  function spot(s) {
    const d = D(); if (!d || !s) return;
    if (d.spot !== s.i) { if (s.n) toPage({ a: "unspot", n: s.n }); return; }   // too late, no comment: the page's scroll back
    d.spot = null; clearTimeout(d.spotT);
    if (!s.el) return HY.toast(t("This element is gone from the page"), "info");
    comment({ el: s.el, pt: s.pt, vp: s.vp, pin: s.pin, n: s.n });   // n: cancelled, the page gives back the scroll it took (agent.js unspot)
  }
  // a click on a row's count: the newest thread, then the next one; the only one open closes again
  function open(key) {
    const c = CM(), l = MAP.get(key); if (!c || !l) return;
    const at = l.findIndex(x => x.id === (c.state || {}).open);
    if (at >= 0 && l.length === 1) return c.close();
    c.open(l[(at + 1) % l.length].id);
  }
  // a press in the tree: true when it was on a row's button or count
  function click(e) {
    const r = e.target.closest(".row"); if (!r) return false;
    if (e.target.closest(".dvcb")) { start(+r.dataset.i); return true; }
    if (e.target.closest(".dvcn")) { open(r.dataset.p); return true; }
    return false;
  }
  // a thread opened on the board (its pin, the list, the bell): the row of its element selected, unfolded down to it, scrolled to; not the
  // one just written (made), which leaves the tree as it was
  function opened(e) {
    const d = D(), th = e && e.detail && !e.detail.made && e.detail.thread;
    if (!d || !d.tree || !th || !th.element || !th.anchor || th.anchor.obj !== d.id) return;
    const at = nodeAt(d.tree.root, th.element.key); if (!at) return;
    at.path.forEach(i => d.open.add(i));
    select(at.n.i, true);
  }
  // threads added, answered, resolved or gone: the rows' marks again when they changed
  function refresh() { const d = D(); if (!d || !d.tree) return; const was = sig; count(); if (sig !== was) drawTree(); }
  const item = () => window.hyMenuItem ? hyMenuItem('data-act="comment"', "comment", esc(t("Comment")), ["C"]) : "";
  return { count, mark, place, hover, start, spot, click, opened, refresh, item };
}
