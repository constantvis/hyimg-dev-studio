// Dev Studio's Edit mode (owner 2026-10-09 on round 15's «Inspector · History»: «я бы еще добавил режим редактирования HTML. Чтобы мы
// могли, как в браузере в инспекторе можно редактировать, так же и тут ... Может быть, переключать туда-сюда»). The mini toggle in the
// right block's header or E turns it on and off; Inspect is the studio as it was. In Edit mode, as in a browser's Elements panel:
//
// - the tree: a double click on a row's tag renames the element, on its #id or .classes edits that attribute, on a leaf's text edits the
//   text, all in place; Enter applies, leaving the field applies; Esc puts a name or a value back and keeps a text (Hyimg's one rule, owner
//   decision 2026-10-10, P4 S-25: what is written on the canvas keeps it, the same text typed in the page does too); ⌘↵ applies and is Done. Under the pointer a row shows + (add attributes, typed as
//   name="value") and a bin (delete the element); ⌫ or Delete deletes the selected ones
// - the inspector's Attributes: every attribute's name and value is a field; the page follows as you type, Enter or leaving the field
//   writes it, Esc puts it back; × removes one, + adds name="value"
// - the page: a double click on a text types it in place, with Select on or off (agent.js «edit»)
//
// Each change shows in the page at once and is written into the file by edits.js: only that attribute, that tag's name (and its end tag's),
// that text or that element's bytes change in the file (htmledit.py), one step of ⌘Z a change, listed in History.
import { why } from "./inspect.js";

const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const NAME = /^[^\s"'>/=\u0000-\u001f\u007f]{1,200}$/;
const TAG = /^[a-z][a-z0-9-]{0,60}$/;

// name="value" pairs as one types them after a tag in HTML: name, name=value, name="value", name='value'; null when there is anything else
export function parseAttrs(s) {
  const out = {}, re = /\s*([^\s"'>/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/y;
  let k = 0; s = String(s || "");
  while (k < s.length) {
    if (!s.slice(k).trim()) break;
    re.lastIndex = k; const m = re.exec(s); if (!m) return null;
    if (!NAME.test(m[1])) return null;
    out[m[1].toLowerCase()] = m[2] ?? m[3] ?? m[4] ?? ""; k = re.lastIndex;
  }
  return Object.keys(out).length ? out : null;
}

export function makeTreeEdit({ D, t, svg, EDITS, select, toast, toPage, drawTree, drawInspector, done }) {
  const H = () => (window.hyTyping && window.hyTyping.keys ? window.hyTyping : null);   // Hyimg's one helper for a field's keys (ui/typing.js)
  const live = det => det && det.attrs ? Object.fromEntries(det.attrs) : {};
  // the element of row i once its detail came for the file's revision (a row is selected first, the page answers)
  function whenDetail(i) {
    const d = D(); if (!d) return Promise.resolve(null);
    if (!(d.sels.size === 1 && d.sel === i && d.detail && d.detail.i === i)) select(i, true);
    const t0 = performance.now();
    return new Promise(res => {
      const tick = () => {
        const e = D(), x = e && e.detail; if (!e) return res(null);
        if (x && x.i === i && x.src && x.src.why !== "wait" && (x.src.why || x.src.rev === e.rev)) return res(x);
        if (performance.now() - t0 > 3000) return res(null);
        setTimeout(tick, 30);
      };
      tick();
    });
  }
  const can = det => { const d = D(), off = d && why(d, t, det); if (off) toast(off.replace(/<[^>]+>/g, ""), "info"); return !off; };
  function attrs(det, set) {
    const before = {}, now = live(det);
    for (const k of Object.keys(set)) before[k] = k in now ? now[k] : null;
    EDITS.attrs(det.i, set, before, det);
  }

  /* ---------- the tree: a field in place of a row's part ---------- */
  // part: tag | id | class | text | add
  async function open(i, part) {
    const det = await whenDetail(i), d = D(); if (!d || !det || !can(det)) return;
    let value = "";
    if (part === "tag") value = det.t;
    else if (part === "id") value = det.d || "";
    else if (part === "class") value = live(det).class || "";
    else if (part === "text") {
      if (typeof det.src.text !== "string") return toast(t("Only an element with nothing but text inside can be typed"), "info");
      value = det.src.text.replace(/\s+/g, " ").trim();
    }
    d.inline = null; drawTree();
    const row = d.ui.tree.querySelector(`.row[data-i="${i}"]`); if (!row) return;
    const at = { tag: ".dtg", id: ".dia", class: ".dic", text: ".dtx" }[part];
    let span = at && row.querySelector(at);
    if (!span) { span = document.createElement("span"); span.className = part === "add" ? "dtadd" : at.slice(1); row.querySelector(".nm").appendChild(span); }
    const inp = document.createElement("input");
    inp.className = "dvin"; inp.value = value; inp.spellcheck = false; inp.setAttribute("aria-label", part === "add" ? t("New attributes") : part);
    if (part === "add") inp.placeholder = 'name="value"';
    const fit = () => { inp.style.width = Math.max(4, Math.min(60, (inp.value || inp.placeholder).length + 1)) + "ch"; };
    fit(); inp.addEventListener("input", fit);
    span.replaceChildren(inp); row.classList.add("editing");
    const s = d.inline = { i, part, det, inp, was: value, done: false };
    if (H()) H().keys(inp, { esc: part === "text" ? "apply" : "cancel", enter: "line", apply: () => finish(s, true), cancel: () => finish(s, false), primary: done });
    else inp.addEventListener("keydown", e => {
      e.stopPropagation();
      if (e.key === "Enter") { e.preventDefault(); finish(s, true); }
      else if (e.key === "Escape") { e.preventDefault(); finish(s, false); }
    });
    inp.addEventListener("blur", () => finish(s, true));
    inp.focus(); inp.select();
  }
  function finish(s, apply) {
    const d = D(); if (!d || s.done) return; s.done = true;
    if (d.inline === s) d.inline = null;
    const v = s.inp.value, det = s.det;
    drawTree(); if (d.ui.tree.contains(document.activeElement) || !document.activeElement || document.activeElement === document.body) d.ui.tree.focus({ preventScroll: true });
    if (!apply || v === s.was) return;
    if (s.part === "tag") {
      const n = v.trim().toLowerCase();
      if (!TAG.test(n)) return toast(t("Not a tag name: {v}", { v: v.slice(0, 40) }), "error");
      if (n !== det.t) EDITS.rename(det.i, n, det);
    } else if (s.part === "id") attrs(det, { id: v.trim() || null });
    else if (s.part === "class") attrs(det, { class: v.replace(/\s+/g, " ").trim() || null });
    else if (s.part === "text") { toPage({ a: "live", ops: [{ i: det.i, text: v }] }); EDITS.text(det.i, s.was, v); }
    else if (s.part === "add") {
      const set = parseAttrs(v); if (!set) return toast(t("Type attributes as name=\"value\""), "error");
      attrs(det, set);
    }
  }
  // a double click on a row in Edit mode: its part in a field (a row's other places still fold and unfold it)
  function dbl(e) {
    const d = D(); if (!d || !d.edit) return false;
    const r = e.target.closest(".row"); if (!r || e.target.closest(".chev, .dvcb, .dvcn, .dvea, .dved, .dvin")) return false;
    const part = e.target.closest(".dtg") ? "tag" : e.target.closest(".dia") ? "id" : e.target.closest(".dic") ? "class" : e.target.closest(".dtx") ? "text" : null;
    if (!part) return false;
    open(+r.dataset.i, part); return true;
  }
  // under the pointer in Edit mode: + and the bin on the row, before its annotation button: Hyimg's icons on hover (a row is a .hy-hovrow,
  // its buttons .hy-ri, 20 px; r15-micro #8, owner 2026-10-09: «Все топ, все делай»)
  let btns = null;
  function hover(row) {
    const d = D(); if (!d) return;
    if (!btns) {
      const mk = (cls, icon, label) => {
        const b = document.createElement("button"); b.type = "button"; b.className = "hy-ri " + cls; b.tabIndex = -1;
        b.title = label; b.setAttribute("aria-label", label); b.innerHTML = svg(icon, 12);
        return b;
      };
      btns = [mk("dvea", "plus", t("Add attributes")), mk("dved", "trash", t("Delete the element · ⌫"))];
    }
    if (!row || !d.edit || row.classList.contains("editing")) { btns.forEach(b => b.remove()); return; }
    const before = row.querySelector(".dvcb, .dvcn, .dvcd");
    for (const b of btns) if (b.parentNode !== row || (before && b.compareDocumentPosition(before) & Node.DOCUMENT_POSITION_PRECEDING)) row.insertBefore(b, before);
  }
  function click(e) {
    const r = e.target.closest(".row"); if (!r) return false;
    if (e.target.closest(".dvea")) { open(+r.dataset.i, "add"); return true; }
    if (e.target.closest(".dved")) { whenDetail(+r.dataset.i).then(det => { if (det && can(det)) EDITS.remove([det]); }); return true; }
    return e.target.closest(".dvin") ? true : false;
  }
  // ⌫ or Delete: the selected elements the file has, not one inside another selected one
  function del() {
    const d = D(); if (!d || !d.edit || !d.detail) return false;
    const all = [d.detail, ...(d.more || [])].filter(Boolean), ids = new Set(all.map(x => x.i));
    const top = all.filter(x => !(x.path || []).slice(0, -1).some(i => ids.has(i)));
    if (!can(d.detail)) return true;
    EDITS.remove(top); return true;
  }

  /* ---------- the inspector's Attributes in Edit mode ---------- */
  function attrsHtml(det, off) {
    const rows = det.attrs || [];
    return `<div class="dsec ded dattr"${off ? " inert" : ""}><div class="dsh hy-sh">${esc(t("Attributes"))}<span class="hy-sh-n">${rows.length || ""}</span>`
      + `<button class="hy-sh-act" data-aadd title="${esc(t("Add attributes"))}" aria-label="${esc(t("Add attributes"))}">${svg("plus", 14)}</button></div>`
      + rows.map(([k, v]) => `<div class="dva" data-a="${esc(k)}"><input class="dva-n" value="${esc(k)}" spellcheck="false" aria-label="${esc(t("Attribute name"))}">`
        + `<input class="dva-v" value="${esc(v)}" spellcheck="false" aria-label="${esc(k)}">`
        + `<button class="dva-x" title="${esc(t("Remove {a}", { a: k }))}" aria-label="${esc(t("Remove {a}", { a: k }))}">${svg("close", 12)}</button></div>`).join("")
      + `</div>`;
  }
  function wireAttrs(root, det) {
    const sec = root.querySelector(".dattr"); if (!sec) return;
    // an attribute is a name or a value: ↵ and Tab write it, Esc puts it back (the field, the page; the blur after it writes nothing, no change
    // event), ⌘↵ writes it and is Done; Hyimg's one helper when there is one
    const back = inp => {
      const k = inp.closest(".dva") && inp.closest(".dva").dataset.a;
      if (inp.classList.contains("dva-v") && inp.value !== inp.defaultValue) toPage({ a: "live", ops: [{ i: det.i, attr: { [k]: inp.defaultValue } }] });
      inp.value = inp.defaultValue; if (inp.classList.contains("dva-w")) inp.closest(".dva").remove(); else inp.blur();
    };
    const keys = e => {
      e.stopPropagation();
      const inp = e.target;
      if (e.key === "Enter") { e.preventDefault(); inp.blur(); }
      else if (e.key === "Escape") { e.preventDefault(); back(inp); }
    };
    const on = inp => H() ? H().keys(inp, { esc: "cancel", enter: "line", tab: "own", apply: () => inp.blur(), cancel: () => back(inp), primary: done })
      : inp.addEventListener("keydown", keys);
    sec.querySelectorAll(".dva-v").forEach(inp => {
      const k = inp.closest(".dva").dataset.a;
      on(inp);
      inp.addEventListener("input", () => toPage({ a: "live", ops: [{ i: det.i, attr: { [k]: inp.value } }] }));   // the page follows as you type
      inp.addEventListener("change", () => { EDITS.attrs(det.i, { [k]: inp.value }, { [k]: inp.defaultValue }, det); inp.defaultValue = inp.value; });
    });
    sec.querySelectorAll(".dva-n").forEach(inp => {
      const k = inp.closest(".dva").dataset.a, val = inp.closest(".dva").querySelector(".dva-v");
      on(inp);
      inp.addEventListener("change", () => {
        const n = inp.value.trim().toLowerCase();
        if (!NAME.test(n)) { inp.value = inp.defaultValue; return toast(t("Not an attribute name: {v}", { v: inp.value.slice(0, 40) }), "error"); }
        if (n === k) return;
        attrs(det, { [k]: null, [n]: val.value });
      });
    });
    sec.querySelectorAll(".dva-x").forEach(b => b.addEventListener("click", () => { const k = b.closest(".dva").dataset.a; attrs(det, { [k]: null }); }));
    sec.querySelector("[data-aadd]").addEventListener("click", () => {
      if (sec.querySelector(".dva-w")) return sec.querySelector(".dva-w").focus();
      const row = document.createElement("div"); row.className = "dva dnew";
      row.innerHTML = `<input class="dva-w" placeholder='name="value"' spellcheck="false" aria-label="${esc(t("New attributes"))}">`;
      sec.appendChild(row); const inp = row.firstChild;
      on(inp);
      inp.addEventListener("change", () => {
        if (!inp.value.trim()) return row.remove();
        const set = parseAttrs(inp.value); if (!set) return toast(t("Type attributes as name=\"value\""), "error");
        attrs(det, set);
      });
      inp.focus();
    });
  }
  const busy = () => { const d = D(); return !!(d && d.inline && !d.inline.done); };
  return { open, dbl, hover, click, del, attrsHtml, wireAttrs, busy, whenDetail };
}

export const CSS_TREEEDIT = `
  .dvt .row .dvin, .dvr .dva input { box-sizing: border-box; height: 22px; padding: 0 6px; border: 0; border-radius: var(--hy-ctl-r, 6px); outline: none;
    background: var(--hy-well); color: var(--ink); font: 400 12px ui-monospace, "SF Mono", Menlo, monospace; box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--dev) 65%, transparent); }
  .dvt .row.editing { overflow: visible; } .dvt .row.editing .nm { overflow: visible; } .dvt .row .dtadd { margin-left: 8px; }
  .dvt .row .dvea { margin-left: auto; } .dvt .row .dvea ~ :is(.dvcb, .dvcn, .dvcd) { margin-left: 0; }
  .dvt .row .dvchd { margin-left: 6px; }   /* changed, written: Hyimg's change dot (.hy-dot, micro #7), in the Studio's green */
  .dvui.dvedit-on .dvt .row :is(.dtg, .dia, .dic, .dtx) { cursor: text; }
  .dvr .dattr .dsh .hy-sh-n { margin-left: auto; } .dvr .dattr .dsh .hy-sh-act { width: 24px; height: 24px; }
  .dvr .dva { display: flex; align-items: center; gap: 4px; padding: 1px 6px; }
  .dvr .dva input { height: var(--hy-ctl-h, 24px); box-shadow: none; border: 1px solid transparent; transition: border-color .2s cubic-bezier(.32,.72,0,1); }
  .dvr .dva input:focus { border-color: var(--sel); }
  .dvr .dva .dva-n { flex: 0 0 86px; width: 86px; min-width: 0; color: var(--sub); }
  .dvr .dva .dva-v, .dvr .dva .dva-w { flex: 1; min-width: 0; }
  .dvr .dva .dva-x { width: 24px; height: 24px; flex: none; display: grid; place-items: center; padding: 0; border: 0; border-radius: var(--hy-ctl-r, 6px); background: none;
    color: var(--muted); cursor: pointer; opacity: 0; transition: opacity .15s ease; }
  .dvr .dva:hover .dva-x, .dvr .dva .dva-x:focus-visible { opacity: 1; } .dvr .dva .dva-x:hover { color: var(--ink); background: var(--hy-hov); }`;
