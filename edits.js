// Dev mode's writes (0.2, owner 2026-10-07: «два раза нажать на них и поменять там цвет ... Дописать какой-то текст»): what the inspector
// and typing in place change goes into the page at once (agent.js "live") and into the file a moment later, through the plugin's server
// routes (server.py: source, edit, undo). One write at a time: after each one the page reads the file's new source, so the next edit
// names its elements by their new offsets. Each write is one step of Dev mode's own undo (⌘Z, ⇧⌘Z while Dev mode is open); a step is
// kept by the server while it runs and taken back only when the file is still as that step left it.
//
// ctx: {D() the open Dev mode or null, toPage(msg), t(key, vars), toast(text, kind), plugin, changed()}; D carries src (the library
// path), sid (the session), rev, vars, detail (the primary element, agent.js detail()), more (the other selected ones, brief), gen (the
// frame's load), past and future (the steps).
//
// Edit mode (treeedit.js, owner 2026-10-09: «режим редактирования HTML ... как в браузере в инспекторе») adds attrs (attributes set,
// added, removed), rename (the tag) and remove (the element): the page shows each at once and the file follows, as for the inspector's
// controls. A step carries its label for History (panel.js: what, the element, the value) and the time it was made; the elements a
// write touched get a dot on their tree row (D.touched). Undoing a removal puts the element back where it stood in the page (agent.js
// keeps it), a renamed one gets its old tag back the same way.
export function makeEdits(ctx) {
  const { t } = ctx;
  let chain = Promise.resolve(), revWait = null, busy = 0;
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

  const queue = fn => {   // one write at a time; busy counts the ones waiting or on their way (the LED blinks, panel.js)
    busy++; if (ctx.busy) ctx.busy();
    return (chain = chain.then(fn).catch(e => { console.error("dev edit", e); ctx.toast(String(e.message || e), "error"); })
      .finally(() => { busy--; if (ctx.busy) ctx.busy(); }));
  };
  // an element's short name for History: its tag and its id, else its first class
  const named = x => !x ? "" : x.t + (x.d ? "#" + x.d : x.c && x.c.length ? "." + x.c[0] : "");
  // the elements an edit goes to: the selected ones the file has, in the page's revision
  function targets(D) {
    const all = [D.detail, ...(D.more || [])].filter(Boolean);
    return { ok: all.filter(x => x.src && x.src.at !== undefined && x.src.rev === D.rev), off: all.filter(x => !(x.src && x.src.at !== undefined)) };
  }
  // a refusal in words (P4 S-39: «Not saved: 500»): the server's reason, else what happened, never a bare status
  const whyNot = r => r.j.error || (r.status ? t("the server did not write it") : t("no connection to Hyimg"));
  async function write(D, build, retry = true) {
    const b = build(D); if (!b || !b.ops.length) return null;
    const r = await api("edit", { p: D.src, rev: D.rev, session: D.sid, ops: b.ops });
    if (ctx.D() !== D) return null;
    if (r.status === 409 && retry) {   // the file changed outside: read it again, and the edit once more on the new offsets
      const s = await api("source", { p: D.src }); if (s.ok) await takeSource(D, s.j);
      const j = await write(D, build, false);
      // the edit went in beside the change made outside, which the page does not show yet (P4 S-40: it was merged without a word)
      if (j) ctx.toast(t("The file had changed outside: your edit is in it, Reload shows the rest"), "info", { key: "dvoutside", actions: [{ label: t("Reload"), fn: () => ctx.reload() }] });
      return j;
    }
    if (!r.ok && !retry && r.status === 422) {   // the file changed under the edit (P4 S-05): it stays, the page shows it, nothing of yours is written
      ctx.toast(t("The file changed meanwhile: your edit was not saved, the page shows the file now"), "error"); ctx.reload(); return null;
    }
    if (!r.ok) {   // the page back as the file is, the LED red until a write goes through (S-39)
      D.saveErr = whyNot(r); ctx.toPage({ a: "live", ops: b.undo }); ctx.toast(t("Not saved: {why}", { why: D.saveErr }), "error", { key: "dvnotsaved" }); ctx.changed(); return null;
    }
    D.saveErr = "";
    if (r.j.step) {
      D.past.push({ step: r.j.step, undo: b.undo, redo: b.redo, gen: D.gen, label: b.label, at: Date.now() }); D.future = [];
      for (const o of b.redo || []) if (o.i) (D.touched || (D.touched = new Set())).add(o.i);
    }
    await takeSource(D, r.j); ctx.changed(true);
    return r.j;
  }

  // a style property of the selected elements, or the custom property behind it (scope "all"); live now, written when it settles, or
  // with o.hold only when a later call commits it (a number dragged by its label: one write, one step of ⌘Z), or never if cancel() drops it
  const keyOf = (prop, o) => o.scope === "all" && o.v ? "var:" + o.v : "style:" + prop;
  function style(prop, value, o = {}) {
    const D = ctx.D(); if (!D || !D.detail) return;
    const key = keyOf(prop, o);
    let p = pending.get(key);
    if (!p) {
      const { ok } = targets(D);
      const before = o.scope === "all" && o.v ? { var: o.v, value: ((D.vars || []).find(v => v.name === o.v) || {}).value || "" }
        : ok.map(x => ({ i: x.i, style: Object.fromEntries([prop, ...(o.also ? Object.keys(o.also) : [])].map(k => [k, (x.inl && x.inl[k]) || (x.ed && x.ed.p[k] && x.ed.p[k].inl) || ""])) }));
      p = { before, ids: ok.map(x => x.i), el: ok.length > 1 ? t("{n} elements", { n: ok.length }) : named(ok[0] || D.detail) }; pending.set(key, p);
    }
    p.value = value; p.also = o.also; p.prop = prop; p.o = o;
    const liveOps = o.scope === "all" && o.v ? [{ var: o.v, value }] : p.ids.map(i => ({ i, style: { [prop]: value, ...(o.also || {}) } }));
    ctx.toPage({ a: "live", ops: liveOps });
    clearTimeout(p.timer);
    const go = () => { clearTimeout(p.timer); if (pending.get(key) === p) { pending.delete(key); flush(key, prop, p, o); } };
    p.go = go;
    if (o.commit) go(); else if (!o.hold) p.timer = setTimeout(go, 450);
  }
  // a change not written yet taken back (Esc): the page as it was before it, nothing goes to the file
  function cancel(prop, o = {}) {
    const key = keyOf(prop, o), p = pending.get(key); if (!p) return;
    clearTimeout(p.timer); pending.delete(key);
    ctx.toPage({ a: "live", ops: Array.isArray(p.before) ? p.before : [p.before] });
  }
  function flush(key, prop, p, o) {
    queue(async () => {
      const D = ctx.D(); if (!D) return;
      await write(D, D2 => {
        if (key.startsWith("var:")) {
          return { ops: [{ op: "var", name: o.v, value: p.value }], undo: [p.before], redo: [{ var: o.v, value: p.value }],
            label: { k: "var", what: o.v, el: t("everywhere"), v: p.value } };
        }
        const { ok, off } = targets(D2), mine = ok.filter(x => p.ids.includes(x.i));
        if (off.length) ctx.toast(t("Not saved: made by a script or the browser, {n}", { n: off.length }), "info");
        const set = { [prop]: p.value, ...(p.also || {}) };
        return { ops: mine.map(x => ({ op: "style", at: x.src.at, tag: x.src.tag, set })),
          undo: p.before.filter(b => p.ids.includes(b.i)), redo: mine.map(x => ({ i: x.i, style: set })), label: { k: "style", what: prop, el: p.el, v: p.value } };
      });
    });
  }
  // the text typed in place: the element's text in the file, if the file has that element and its text
  function text(i, was, now) {
    // the text the file had when this typing started (typeText), else what the page showed: a change made outside meanwhile is refused (S-05)
    const D0 = ctx.D(), base = D0 && D0.typed && D0.typed.i === i && typeof D0.typed.file === "string" ? D0.typed.file : was; if (D0) D0.typed = null;
    if (was === now) return;
    queue(async () => {
      const D = ctx.D(); if (!D) return;
      await write(D, D2 => {
        const x = [D2.detail, ...(D2.more || [])].find(e => e && e.i === i);
        if (!x || !x.src || x.src.at === undefined || typeof x.src.text !== "string") {
          ctx.toPage({ a: "live", ops: [{ i, text: was }] }); ctx.toast(t("This text can't be saved: it is not in the file"), "error"); return null;
        }
        return { ops: [{ op: "text", at: x.src.at, tag: x.src.tag, was: base, text: now }], undo: [{ i, text: was }], redo: [{ i, text: now }],
          label: { k: "text", what: t("Text"), el: named(x.t ? x : D2.detail), v: now.replace(/\s+/g, " ").trim().slice(0, 60) } };
      });
    });
  }
  // the element i among the selected ones, where the file has it in the page's revision
  const inFile = (D2, i) => { const x = [D2.detail, ...(D2.more || [])].find(e => e && e.i === i); return x && x.src && x.src.at !== undefined && x.src.rev === D2.rev ? x : null; };
  const refuse = (i, live) => { if (live) ctx.toPage({ a: "live", ops: live }); ctx.toast(t("Not saved: it is not in the file"), "error"); return null; };
  // Edit mode: attributes of element i set, added or removed ({name: value | null}); before: the page's values, for ⌘Z; el: its detail
  function attrs(i, set, before, el) {
    ctx.toPage({ a: "live", ops: [{ i, attr: set }] });
    const undo = [{ i, attr: before }], names = Object.keys(set);
    queue(async () => {
      const D = ctx.D(); if (!D) return;
      await write(D, D2 => {
        const x = inFile(D2, i) || (el && el.src && el.src.rev === D2.rev ? el : null); if (!x) return refuse(i, undo);
        // the attributes as the file had them when the edit was made (el), not as read again after a change outside (P4 S-05)
        const src = Object.fromEntries((el && el.src && el.src.attrs) || x.src.attrs || []), was = Object.fromEntries(names.map(n => [n, n in src ? src[n] : null]));
        const gone = names.filter(n => set[n] === null), v = names.filter(n => set[n] !== null).map(n => `${n}="${set[n]}"`).join(" ");
        const what = names.length === 1 ? (gone.length ? t("Removed {a}", { a: names[0] }) : names[0]) : gone.length === 1 && names.length === 2 ? t("Renamed {a}", { a: gone[0] }) : t("Attributes");
        return { ops: [{ op: "attrs", at: x.src.at, tag: x.src.tag, set, was }], undo, redo: [{ i, attr: set }],
          label: { k: "attrs", what, el: named(el || x), v: gone.length && names.length === 1 ? "" : (names.length === 1 ? set[names[0]] : v).slice(0, 60) } };
      });
    });
  }
  // Edit mode: the element's tag renamed, in its start tag and its end tag
  function rename(i, name, el) {
    const old = el && el.t;
    ctx.toPage({ a: "live", ops: [{ i, tag: name }] });
    queue(async () => {
      const D = ctx.D(); if (!D) return;
      await write(D, D2 => {
        const x = (el && el.src && el.src.rev === D2.rev ? el : null) || inFile(D2, i); if (!x) return refuse(i, old ? [{ i, tag: old }] : null);
        return { ops: [{ op: "tag", at: x.src.at, tag: x.src.tag, name, inner: x.src.inner }], undo: [{ i, tag: x.src.tag }], redo: [{ i, tag: name }],
          label: { k: "tag", what: t("Tag"), el: named(el || x), v: `${x.src.tag} → ${name}` } };
      });
    });
  }
  // Edit mode: the elements taken out of the page and the file (⌫); ⌘Z puts them back where they stood
  function remove(list) {
    const ids = list.map(x => x.i);
    ctx.toPage({ a: "live", ops: ids.map(i => ({ i, remove: true })) }); if (ctx.picked) ctx.picked([]);   // nothing removed stays chosen (P4 S-51)
    queue(async () => {
      const D = ctx.D(); if (!D) return;
      await write(D, D2 => {
        const xs = list.map(x => x.src && x.src.at !== undefined && x.src.rev === D2.rev ? x : null);
        if (xs.some(x => !x)) return refuse(null, ids.map(i => ({ i, restore: true })));
        return { ops: xs.map(x => ({ op: "remove", at: x.src.at, tag: x.src.tag, inner: x.src.inner })), undo: ids.map(i => ({ i, restore: true })),
          redo: ids.map(i => ({ i, remove: true })), label: { k: "remove", what: t("Deleted"), el: xs.length > 1 ? t("{n} elements", { n: xs.length }) : named(xs[0]) } };
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
      if (!r.ok) {   // the step stays where it was, to try again (P4 S-24: a failed undo lost it, a failed redo said «Can't undo»)
        from.push(s); ctx.toast(t(back ? "Can't undo: {why}" : "Can't redo: {why}", { why: whyNot(r) }), "error"); ctx.changed(); return;
      }
      to.push(s);
      const ops = back ? s.undo : s.redo, put = ops.filter(o => o.restore).map(o => o.i);
      if (s.gen === D.gen) { ctx.toPage({ a: "live", ops }); if (ctx.picked && (put.length || ops.some(o => o.remove))) ctx.picked(put); } else ctx.reload();   // S-51
      await takeSource(D, r.j); ctx.changed(true);
    });
  }
  // every change still settling written now; resolves when the writes are done (Done, Reload, Board: P4 S-17, they were lost)
  function flushAll() { for (const p of [...pending.values()]) p.go(); return chain.catch(() => {}); }
  return { load, seen, style, cancel, text, attrs, rename, remove, undo: () => step(true), redo: () => step(false), api, busy: () => busy > 0, flush: flushAll };
}
