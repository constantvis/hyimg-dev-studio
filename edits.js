// Dev mode's writes (0.2, owner 2026-10-07: «два раза нажать на них и поменять там цвет ... Дописать какой-то текст»): what the inspector
// and typing in place change goes into the page at once (agent.js "live") and into the file a moment later, through the plugin's server
// routes (server.py: source, edit, undo). One write at a time: after each one the page reads the file's new source, so the next edit
// names its elements by their new offsets. Each write is one step of Dev mode's own undo (⌘Z, ⇧⌘Z while Dev mode is open); a step is
// kept by the server while it runs and taken back only when the file is still as that step left it.
//
// ctx: {D() the open Dev mode or null, toPage(msg), t(key, vars), toast(text, kind), plugin, changed()}; D carries src (the library
// path), sid (the session), rev, vars, detail (the primary element, agent.js detail()), more (the other selected ones, brief), gen (the
// frame's load), past and future (the steps).
export function makeEdits(ctx) {
  const { t } = ctx;
  let chain = Promise.resolve(), revWait = null;
  const pending = new Map();   // key -> {timer, value, before, build}: a change being dragged, written when it settles

  async function api(route, body) {
    try {
      const r = await fetch(`/api/plugin/${ctx.plugin}/${route}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      let j = {}; try { j = await r.json(); } catch (e) { /* no body */ }
      return { ok: r.ok, status: r.status, j };
    } catch (e) { return { ok: false, status: 0, j: { error: String(e.message || e) } }; }
  }
  // the page reads the file's source; resolves when it sent its selection again for that revision
  function takeSource(D, j) {
    D.rev = j.rev; D.vars = j.vars || []; D.srcErr = "";
    const wait = new Promise(res => { revWait = { rev: j.rev, res }; setTimeout(res, 3000); });
    ctx.toPage({ a: "source", html: j.html, rev: j.rev });
    return wait;
  }
  async function load() {
    const D = ctx.D(); if (!D) return;
    const r = await api("source", { p: D.src });
    if (ctx.D() !== D) return;
    if (!r.ok) { D.srcErr = r.j.error || t("The file can't be read"); ctx.changed(); return; }
    await takeSource(D, r.j); ctx.changed();
  }
  // the page sent its selection: a write waiting for this revision goes on
  function seen(rev) { if (revWait && rev === revWait.rev) { const w = revWait; revWait = null; w.res(); } }

  const queue = fn => (chain = chain.then(fn).catch(e => { console.error("dev edit", e); ctx.toast(String(e.message || e), "error"); }));
  // the elements an edit goes to: the selected ones the file has, in the page's revision
  function targets(D) {
    const all = [D.detail, ...(D.more || [])].filter(Boolean);
    return { ok: all.filter(x => x.src && x.src.at !== undefined && x.src.rev === D.rev), off: all.filter(x => !(x.src && x.src.at !== undefined)) };
  }
  async function write(D, build, retry = true) {
    const b = build(D); if (!b || !b.ops.length) return null;
    const r = await api("edit", { p: D.src, rev: D.rev, session: D.sid, ops: b.ops });
    if (ctx.D() !== D) return null;
    if (r.status === 409 && retry) {   // the file changed outside: read it again, and the edit once more on the new offsets
      const s = await api("source", { p: D.src }); if (s.ok) await takeSource(D, s.j);
      return write(D, build, false);
    }
    if (!r.ok) { ctx.toPage({ a: "live", ops: b.undo }); ctx.toast(t("Not saved: {why}", { why: r.j.error || r.status }), "error"); return null; }
    if (r.j.step) { D.past.push({ step: r.j.step, undo: b.undo, redo: b.redo, gen: D.gen }); D.future = []; }
    await takeSource(D, r.j); ctx.changed(true);
    return r.j;
  }

  // a style property of the selected elements, or the custom property behind it (scope "all"); live now, written when it settles
  function style(prop, value, o = {}) {
    const D = ctx.D(); if (!D || !D.detail) return;
    const key = o.scope === "all" && o.v ? "var:" + o.v : "style:" + prop;
    let p = pending.get(key);
    if (!p) {
      const { ok } = targets(D);
      const before = o.scope === "all" && o.v ? { var: o.v, value: ((D.vars || []).find(v => v.name === o.v) || {}).value || "" }
        : ok.map(x => ({ i: x.i, style: Object.fromEntries([prop, ...(o.also ? Object.keys(o.also) : [])].map(k => [k, (x.inl && x.inl[k]) || (x.ed && x.ed.p[k] && x.ed.p[k].inl) || ""])) }));
      p = { before, ids: ok.map(x => x.i) }; pending.set(key, p);
    }
    p.value = value; p.also = o.also; p.prop = prop; p.o = o;
    const liveOps = o.scope === "all" && o.v ? [{ var: o.v, value }] : p.ids.map(i => ({ i, style: { [prop]: value, ...(o.also || {}) } }));
    ctx.toPage({ a: "live", ops: liveOps });
    clearTimeout(p.timer);
    const go = () => { clearTimeout(p.timer); if (pending.get(key) === p) { pending.delete(key); flush(key, prop, p, o); } };
    p.go = go;
    if (o.commit) go(); else p.timer = setTimeout(go, 450);
  }
  function flush(key, prop, p, o) {
    queue(async () => {
      const D = ctx.D(); if (!D) return;
      await write(D, D2 => {
        if (key.startsWith("var:")) {
          return { ops: [{ op: "var", name: o.v, value: p.value }], undo: [p.before], redo: [{ var: o.v, value: p.value }] };
        }
        const { ok, off } = targets(D2), mine = ok.filter(x => p.ids.includes(x.i));
        if (off.length) ctx.toast(t("Not saved: made by a script or the browser, {n}", { n: off.length }), "info");
        const set = { [prop]: p.value, ...(p.also || {}) };
        return { ops: mine.map(x => ({ op: "style", at: x.src.at, tag: x.src.tag, set })),
          undo: p.before.filter(b => p.ids.includes(b.i)), redo: mine.map(x => ({ i: x.i, style: set })) };
      });
    });
  }
  // the text typed in place: the element's text in the file, if the file has that element and its text
  function text(i, was, now) {
    if (was === now) return;
    queue(async () => {
      const D = ctx.D(); if (!D) return;
      await write(D, D2 => {
        const x = [D2.detail, ...(D2.more || [])].find(e => e && e.i === i);
        if (!x || !x.src || x.src.at === undefined || typeof x.src.text !== "string") {
          ctx.toPage({ a: "live", ops: [{ i, text: was }] }); ctx.toast(t("This text can't be saved: it is not in the file"), "error"); return null;
        }
        return { ops: [{ op: "text", at: x.src.at, tag: x.src.tag, was: x.src.text, text: now }], undo: [{ i, text: was }], redo: [{ i, text: now }] };
      });
    });
  }
  // ⌘Z and ⇧⌘Z: the file back as it was before the step (or after it), the page follows
  function step(back) {
    for (const p of [...pending.values()]) p.go();   // a change still settling is written first, so ⌘Z takes back that change
    queue(async () => {
      const D = ctx.D(); if (!D) return;
      const from = back ? D.past : D.future, to = back ? D.future : D.past, s = from.pop();
      if (!s) return;
      const r = await api("undo", { p: D.src, step: s.step, dir: back ? "undo" : "redo" });
      if (ctx.D() !== D) return;
      if (!r.ok) { ctx.toast(t("Can't undo: {why}", { why: r.j.error || r.status }), "error"); ctx.changed(); return; }
      to.push(s);
      if (s.gen === D.gen) ctx.toPage({ a: "live", ops: back ? s.undo : s.redo }); else ctx.reload();
      await takeSource(D, r.j); ctx.changed(true);
    });
  }
  return { load, seen, style, text, undo: () => step(true), redo: () => step(false), api };
}
