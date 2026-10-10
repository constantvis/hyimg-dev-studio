// Dev mode's inspector controls (0.2, owner 2026-10-07: «Выделить объекты и поменять им цвет»): Layout (width and height when the page
// sets them, padding, gap of a flex or grid box), Appearance (opacity, corners), Fill, Text (colour, size, weight) and Stroke (colour,
// width) of the selected elements, from the app's primitives: hy-swatch with the native colour picker over it (as Settings › Paper
// colour), hy-segmented, the app's slider (ui/slider.js), a number field. A value that comes from a custom property shows it, and the
// choice «This element» or «Everywhere · N» (the property's declaration in the file). An element the file has not got (made by a script,
// implied by the parser) shows the reason and its controls are grey.
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const WEIGHTS = [["300", "Light"], ["400", "Regular"], ["500", "Medium"], ["600", "Semibold"], ["700", "Bold"], ["800", "Extra bold"]];
// round 15 (r15/r15-dev.html, owner 2026-10-09: «Да, неплохо, делай»): a field is a well with its label inside (W auto, Padding 0 0 18 px),
// a colour a well with its swatch and value, the weight a menu («Semibold 600»), Blur beside Corners; the choice «This element | Everywhere»
// Hyimg's micro segments (<hy-segmented variant=micro>, r15-micro #3, owner 2026-10-09: «Все топ, все делай»). A number field drags by its
// label as in Figma (Hyimg's scrub(), ui/hy/scrub.js; owner 2026-10-10 on r16-scrub.html, version A: «отлично, беру»): ⇧ ten times
// faster, ⌥ ten times finer, a click types the number, Esc puts it back; the page follows the drag, the file takes it once, as it ends.

export function hexOf(c) {
  const m = /rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)/.exec(c || "");
  if (m) return "#" + [m[1], m[2], m[3]].map(v => Math.max(0, Math.min(255, Math.round(+v))).toString(16).padStart(2, "0")).join("");
  const h = /^#([\da-f]{3}|[\da-f]{6})$/i.exec((c || "").trim());
  return h ? "#" + (h[1].length === 3 ? [...h[1]].map(x => x + x).join("") : h[1]).toLowerCase() : null;
}
const alphaOf = c => { const m = /rgba\([^)]*[,/]\s*([\d.]+)\s*\)/.exec(c || ""); return m ? +m[1] : 1; };
const num = v => { const m = /^(-?[\d.]+)px$/.exec((v || "").trim()); return m ? String(Math.round(+m[1] * 100) / 100) : (v || "").trim(); };
// a value typed into a field: a bare number is px; what CSS can't take for that property is refused
export function typed(prop, s) {
  s = String(s || "").trim(); if (!s) return prop === "width" || prop === "height" ? "" : null;   // W or H emptied: back to the page's own
  if (prop === "filter") { const n = /^(-?[\d.]+)(px)?$/.exec(s); return n ? (+n[1] ? `blur(${n[1]}px)` : "") : null; }
  if (/^-?[\d.]+$/.test(s) && prop !== "opacity" && prop !== "font-weight") s += "px";
  if (prop === "padding") s = s.split(/\s+/).map(x => /^-?[\d.]+$/.test(x) ? x + "px" : x).join(" ");
  return typeof CSS !== "undefined" && CSS.supports && !CSS.supports(prop, s) ? null : s;
}

// the numbers a field's label drags, or null when the field holds something else (1em, a filter other than one blur()): W and H «auto»
// start from the page's own size, Blur from its radius
const NUMS = /^-?[\d.]+(px)?$/;
export function numsOf(s) { const a = String(s || "").trim().split(/\s+/).filter(Boolean); return a.length && a.every(x => NUMS.test(x)) ? a.map(parseFloat) : null; }
function start(inp, prop) {
  const v = inp.value.trim();
  if (!v && (prop === "width" || prop === "height")) { const n = numsOf(inp.dataset.used); return n && [Math.round(n[0])]; }
  return numsOf(v);
}

// the reason an element can't be saved, or "" when it can
export function why(D, t, d) {
  if (D.srcErr) return t("<b>Can't save</b> this file: {why}", { why: esc(D.srcErr) });
  const s = d && d.src;
  if (!s || s.why === "wait") return t("<b>Reading</b> the file…");
  if (s.why === "script") return t("<b>Made by a script</b>, can't be saved: the file has no such element");
  if (s.why === "implied") return t("<b>Added by the browser</b>, can't be saved: the file has no such tag");
  if (s.why) return t("<b>Can't save</b> this element: {why}", { why: esc(s.msg || s.why) });
  return "";
}

export function drawEdit(D, t, icon) {
  const d = D.detail, e = d && d.ed; if (!e) return "";
  const P = e.p, off = why(D, t, d);
  const scope = k => (D.scope && D.scope[k]) || "el";
  const colorRow = (prop, label) => {
    const o = P[prop], v = o.var, dv = v && (D.vars || []).find(x => x.name === v), hx = hexOf(o.v) || "#000000";
    const shown = v && scope(prop) === "all" && dv ? dv.value : alphaOf(o.v) < 1 ? o.v : hx;
    let row = `<div class="dcr" data-p="${prop}"><span class="dsw2"><hy-swatch color="${esc(o.v)}" label="${esc(label)}" tabindex="-1"></hy-swatch>`
      + `<input type="color" value="${hx}" aria-label="${esc(label)}" data-k="${prop}"></span><input class="dfi" data-c="${prop}" value="${esc(shown)}" spellcheck="false" aria-label="${esc(label)}">`;
    if (v) row += `<span class="dvar" title="${esc(o.from ? t("From {tag}", { tag: o.from }) : v)}">${esc(v)}</span>`;
    row += `</div>`;
    if (v) {
      const can = dv && dv.where === "root", tip = !dv ? t("{v} is declared outside this file", { v }) : dv.where !== "root" ? t("{v} is declared inside a rule Dev Studio doesn't write", { v }) : "";
      row += `<div class="dsc"><hy-segmented class="dvms" variant="micro" full value="${scope(prop)}" data-s="${prop}" label="${esc(v)}">`
        + `<button value="el">${esc(t("This element"))}</button><button value="all"${can ? "" : ` disabled data-tip="${esc(tip)}" title="${esc(tip)}"`}>`
        + `${esc(t("Everywhere · {n}", { n: dv ? dv.uses : 0 }))}</button></hy-segmented></div>`;
    }
    return row;
  };
  const field = (prop, label, val, o = {}) => `<label class="dnf" data-p="${prop}"${o.tip ? ` title="${esc(o.tip)}"` : ""}><span class="dnl" aria-hidden="true">${esc(label)}</span>`
    + `<input class="dfi" data-n="${prop}" value="${esc(val)}" spellcheck="false" aria-label="${esc(label)}"${o.ph ? ` placeholder="${esc(o.ph)}"` : ""}${o.off ? " disabled" : ""}`
    + `${o.used ? ` data-used="${esc(o.used)}"` : ""}>`
    + `${o.u ? `<span class="du">${o.u}</span>` : ""}</label>`;
  const set = p => P[p].set && !/^(auto|initial|inherit|unset|normal)$/.test(P[p].set);
  const px = v => /^-?[\d.]+px$/.test((v || "").trim()) ? "px" : "";
  // W and H: the page's value when it sets one, else «auto» (typing a number sets it); Gap only in a flex or grid box
  const layout = [field("width", "W", set("width") ? num(P.width.v) : "", { ph: "auto", used: P.width.v }),
    field("height", "H", set("height") ? num(P.height.v) : "", { ph: "auto", used: P.height.v }),
    field("padding", t("Padding"), P.padding.v.split(" ").map(num).join(" "), { u: px(P.padding.v.split(" ")[0]) }),
    field("gap", t("Gap"), e.flex ? num(P.gap.v.split(" ")[0]) : "", { ph: "—", off: !e.flex, tip: e.flex ? "" : t("Only in a flex or grid box") })].join("");
  // Blur: the page's filter when it is one blur(), else the filter shows and the field is off (it would replace the filter)
  const fv = (P.filter && P.filter.v) || "none", bm = /^blur\(([-\d.]+)px\)$/.exec(fv.trim()), bOK = fv === "none" || !!bm;
  const blur = field("filter", t("Blur"), bm ? num(bm[1] + "px") : bOK ? "0" : fv, { u: bOK ? "px" : "", off: !bOK, tip: bOK ? "" : t("The page's filter: {v}", { v: fv }) });
  const D_ = D;   // the sections fold by their head's chevron, per session (D.fold)
  const sec = (title, body, cls = "") => { const k = cls || title, shut = D_.fold && D_.fold.has(k);
    return `<div class="dsec ded ${cls}${shut ? " shut" : ""}"${off ? " inert" : ""} data-sec="${esc(k)}"><div class="dsh hy-sh">`
      + `<button class="hy-sh-cv dcv" tabindex="-1" aria-hidden="true">${icon("chevron", 11)}</button>${esc(title)}</div><div class="dsb">${body}</div></div>`; };
  const fw = P["font-weight"].v, weights = WEIGHTS.some(([w]) => w === fw) ? WEIGHTS : [...WEIGHTS, [fw, ""]];
  const leaf = d.src && typeof d.src.text === "string";
  return (off ? `<p class="hy-hint dhint doff">${icon("lock", 13)} ${off}</p>` : leaf ? `<p class="hy-hint dhint">${t("<b>Double-click</b> the text or <b>Enter</b> to type it")}</p>` : "")
    + sec(t("Layout"), `<div class="dgrid">${layout}</div>`)
    + sec(t("Appearance"), `<div class="dop" data-p="opacity"></div><div class="dgrid">${field("border-radius", t("Corners"), num(P["border-radius"].v), { u: "px" })}${blur}</div>`)
    + sec(t("Fill"), colorRow("background-color", t("Fill")))
    + sec(t("Text"), colorRow("color", t("Colour")) + `<div class="dgrid">${field("font-size", t("Size"), num(P["font-size"].v), { u: "px" })}`
      + `<label class="dwt"><select class="dsel" data-w="1" aria-label="${esc(t("Weight"))}">`
      + weights.map(([w, n]) => `<option value="${esc(w)}"${w === fw ? " selected" : ""}>${esc(n ? t(n) + " " + w : w)}</option>`).join("")
      + `</select></label></div>`)
    + sec(t("Stroke"), colorRow("border-color", t("Stroke")) + `<div class="dgrid">${field("border-width", t("Width"), P["border-width"].v.split(" ").map(num).join(" "), { u: "px" })}</div>`);
}

// the controls' events: each change goes to edits.style (live now, written when it settles)
export function wire(root, D, edits, t) {
  const d = D.detail; if (!d || !d.ed) return;
  const P = d.ed.p, sc = k => (D.scope && D.scope[k]) || "el";
  const scopeOf = prop => { const v = P[prop] && P[prop].var; return { scope: v && sc(prop) === "all" ? "all" : "el", v }; };
  // hold: live in the page only, written when a later send commits (a drag of the label is one write, one step of ⌘Z)
  const send = (prop, value, commit, hold) => {
    const also = prop === "border-width" && /none|hidden/.test(P["border-style"].v) && value && !/^0(px)?$/.test(value) ? { "border-style": "solid" } : null;
    edits.style(prop, value, { ...scopeOf(prop), commit, also, hold });
  };
  // a field's keys by Hyimg's one helper (ui/typing.js): a value, so Esc puts it back (owner decision 2026-10-10), ↵ and Tab write it, ⌘↵
  // writes it and is Done (P4 S-28); without the helper, the same by hand
  const H = window.hyTyping && window.hyTyping.keys ? window.hyTyping : null;
  const keys = (inp, apply, cancel, key) => H ? H.keys(inp, { esc: "cancel", enter: "line", tab: "own", apply, cancel, key, primary: () => D.done && D.done() })
    : inp.addEventListener("keydown", e => {
      e.stopPropagation(); if (e.key === "Enter") { e.preventDefault(); apply(); } else if (e.key === "Escape") { e.preventDefault(); cancel(); } else if (key) key(e);
    });
  // the colour picker: the page follows the pointer, the file takes the colour once it is picked, one step (P4 S-38)
  root.querySelectorAll("input[type=color]").forEach(inp => {
    const prop = inp.dataset.k, sw = inp.previousElementSibling, txt = root.querySelector(`[data-c="${prop}"]`);
    inp.addEventListener("input", () => { sw.setAttribute("color", inp.value); txt.value = inp.value; send(prop, inp.value, false, true); });
    inp.addEventListener("change", () => send(prop, inp.value, true));
  });
  // a value goes to the file once: ↵ and the blur after it were two writes and two notes (P4 S-39)
  const once = (inp, v, prop) => { if (inp._sent === v) return; inp._sent = v; send(prop, v, true); };
  root.querySelectorAll("input[data-c]").forEach(inp => {
    const prop = inp.dataset.c;
    const go = () => { const v = typed("color", inp.value); if (!v) { inp.classList.add("bad"); return; } inp.classList.remove("bad"); if (inp.value !== inp.defaultValue) once(inp, v, prop); };
    keys(inp, () => { go(); inp.blur(); }, () => { inp.classList.remove("bad"); inp.value = inp.defaultValue; inp.blur(); });   // Esc cancels (P4 S-18)
    inp.addEventListener("change", go);
  });
  // a number: ↑ ↓ show in the page at once and wait for ↵, Tab or the blur, which write them once, one step for the whole run of presses
  // (P4 S-38); Esc puts it back whenever it comes, the page too (S-59: it worked only in the 450 ms before the write)
  root.querySelectorAll("input[data-n]").forEach(inp => {
    const prop = inp.dataset.n;
    const go = () => { const v = typed(prop, inp.value); if (v === null) { inp.classList.add("bad"); return; } inp.classList.remove("bad"); if (inp.value !== inp.defaultValue) once(inp, v, prop); };
    keys(inp, () => { go(); inp.blur(); }, () => {   // the number as it was, in the field and the page; nothing is written
      inp.classList.remove("bad"); if (inp.value !== inp.defaultValue) { inp.value = inp.defaultValue; edits.cancel(prop, scopeOf(prop)); } inp._held = false; inp.blur();
    }, e => {
      if ((e.key !== "ArrowUp" && e.key !== "ArrowDown") || !/^-?[\d.]+$/.test(inp.value.trim())) return;
      e.preventDefault(); const n = +inp.value + (e.key === "ArrowUp" ? 1 : -1) * (e.shiftKey ? 10 : 1);
      inp.value = String(Math.max(/^(padding|border-width|font-size|filter)$/.test(prop) ? 0 : -1e4, Math.round(n * 100) / 100));
      inp._held = true; send(prop, prop === "filter" ? typed("filter", inp.value) : inp.value + "px", false, true);
    });
    inp.addEventListener("change", go);
    inp.addEventListener("blur", () => { if (inp._held) { inp._held = false; go(); } });
    scrubField(inp, prop);
  });
  root.querySelectorAll("hy-segmented[data-s]").forEach(s => s.addEventListener("hy-change", e => { D.scope = Object.assign({}, D.scope, { [s.dataset.s]: e.detail.value }); D.redraw(); }));
  // the label drags the number (Hyimg ui/hy/scrub.js): the numbers it starts from (W or H «auto»: the page's own size now; Padding, Stroke
  // width: every side moves by the same amount, none under 0), the page follows each step, the file takes the last one once at the end
  function scrubField(inp, prop) {
    const h = inp.previousElementSibling;
    if (!window.hyScrub || inp.disabled || !h || !h.classList.contains("dnl") || !start(inp, prop)) return;
    let base = null, last = "";
    const settle = () => { D.scrubbing = false; if (D.dirty) D.redraw(); };
    window.hyScrub(h, {
      can: () => !inp.disabled && !!start(inp, prop),
      get: () => { base = start(inp, prop); last = ""; return base[0]; },
      begin: () => { D.scrubbing = true; inp.classList.remove("bad"); },
      set: v => {
        const n = base.map(x => Math.max(0, Math.round((x + v - base[0]) * 10) / 10));
        inp.value = n.join(" "); last = prop === "filter" ? typed("filter", String(n[0])) : n.map(x => x + "px").join(" ");
        send(prop, last, false, true);
      },
      end: changed => { if (changed) send(prop, last, true); else edits.cancel(prop, scopeOf(prop)); settle(); },
      cancel: () => { inp.value = inp.defaultValue; edits.cancel(prop, scopeOf(prop)); settle(); },
      click: () => { inp.focus(); inp.select(); },
    });
  }
  const w = root.querySelector("select[data-w]");
  if (w) {   // a letter never picks a weight (P4 S-19: the Studio's keys typed with it focused wrote font-weight); chosen, it lets the keys go
    w.addEventListener("keydown", e => { if (e.key.length === 1 && !e.metaKey && !e.ctrlKey && !e.altKey) e.preventDefault(); });
    w.addEventListener("change", () => { send("font-weight", w.value, true); w.blur(); });
  }
  root.querySelectorAll(".ded .dcv").forEach(b => b.closest(".dsh").addEventListener("click", () => {   // a section folds by its head
    const sec = b.closest(".dsec"), k = sec.dataset.sec; D.fold = D.fold || new Set();
    if (D.fold.has(k)) D.fold.delete(k); else D.fold.add(k); sec.classList.toggle("shut", D.fold.has(k));
  }));
  const op = root.querySelector(".dop");
  if (op && window.hySlider) {
    const s = window.hySlider.create({ label: t("Opacity"), min: 0, max: 100, step: 1, unit: "%", value: Math.round(parseFloat(P.opacity.v || "1") * 100),
      onInput: v => send("opacity", String(Math.round(v) / 100), false, true), onChange: v => send("opacity", String(Math.round(v) / 100), true) });   // one step a drag (S-38)
    op.appendChild(s.el);
  }
}

export const CSS_EDIT = `
  .dvr .ded[inert] { opacity: .45; }
  .dvr .ded .dsh { padding-left: 2px; cursor: default; }
  .dvr .ded .dsh .dcv { border: 0; padding: 0; background: none; cursor: pointer; } .dvr .ded .dsh .dcv svg { transition: transform .32s cubic-bezier(.32,.72,0,1); transform: rotate(90deg); }
  .dvr .ded.shut .dsh .dcv svg { transform: none; } .dvr .ded.shut .dsb { display: none; }
  .dvr .doff svg { vertical-align: -2px; margin-right: 2px; }
  /* a colour (r15 .cw): one well, the swatch and the value in it, the custom property after it */
  .dvr .dcr { display: flex; align-items: center; gap: 4px; padding: 2px 6px; }
  .dvr .dcr .dsw2 + .dfi { padding-left: 30px; margin-left: -28px; }
  .dvr .dsw2 { position: relative; z-index: 1; display: inline-flex; flex: none; width: 24px; height: 24px; align-items: center; justify-content: center; }
  .dvr .dsw2 hy-swatch { pointer-events: none; transform: scale(.8); }
  .dvr .dsw2 input[type=color] { position: absolute; inset: 0; width: 100%; height: 100%; margin: 0; padding: 0; opacity: 0; cursor: pointer; border: 0; }
  .dvr .dfi { min-width: 0; flex: 1; height: var(--hy-ctl-h, 24px); box-sizing: border-box; padding: 0 8px; border: 1px solid transparent; border-radius: var(--hy-ctl-r, 6px);
    background: var(--hy-well, transparent); color: var(--ink); font: 12px ui-monospace, "SF Mono", Menlo, monospace; outline: none;
    transition: border-color .2s cubic-bezier(.32,.72,0,1), background-color .2s cubic-bezier(.32,.72,0,1); }   /* a dark well (round 12) */
  .dvr .dfi:hover { background: var(--hy-well-hov, transparent); }
  .dvr .dfi:focus { border-color: var(--sel); } .dvr .dfi.bad { border-color: var(--hy-red); }
  .dvr .dvar { flex: none; max-width: 92px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font: 11px ui-monospace, "SF Mono", Menlo, monospace;
    color: var(--ink); padding: 3px 8px; border-radius: var(--hy-ctl-r, 6px); background: var(--raise); }
  .dvr .dsc { padding: 0 6px 4px; }
  .dvr .dgrid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--hy-gap-ctl, 4px); padding: 2px 6px 4px; }
  /* a field (r15 .fld): one well, its label inside before the value, its unit at the end */
  .dvr .dnf { position: relative; display: flex; align-items: center; min-width: 0; height: var(--hy-ctl-h, 24px); }
  /* its label is the scrub's handle (Hyimg .hy-scrub-h: ew-resize, the selection's tint under the pointer), the height of the well */
  .dvr .dnf > .dnl { position: absolute; left: 4px; top: 0; bottom: 0; z-index: 1; margin: 0; padding: 0 4px; font-size: 12px; }
  .dvr .dnf:not(.hy-scrubbing) > .dnl:not(:hover) { color: var(--muted); }
  .dvr .dnf .dfi { padding-left: calc(var(--lw, 14px) + 14px); padding-right: 22px; font-family: var(--sans, system-ui); }
  .dvr .dnf[data-p=padding] { --lw: 50px; } .dvr .dnf[data-p=gap] { --lw: 26px; } .dvr .dnf[data-p=border-radius] { --lw: 50px; }
  .dvr .dnf[data-p=filter] { --lw: 28px; } .dvr .dnf[data-p=font-size] { --lw: 26px; } .dvr .dnf[data-p=border-width] { --lw: 38px; }
  .dvr .dnf .du { position: absolute; right: 8px; color: var(--muted); font-size: 12px; pointer-events: none; }
  .dvr .dnf .dfi:disabled { color: var(--muted); }
  .dvr .dop { padding: 2px 6px 4px; }
  .dvr .dwt { position: relative; display: flex; min-width: 0; }
  .dvr .dsel { appearance: none; -webkit-appearance: none; width: 100%; min-width: 0; height: var(--hy-ctl-h, 24px); box-sizing: border-box; padding: 0 22px 0 9px; border: 0;
    border-radius: var(--hy-ctl-r, 6px); background: var(--hy-well); color: var(--ink); font: 500 12px var(--sans, system-ui); outline: none; cursor: pointer; }
  .dvr .dsel:hover { background: var(--hy-well-hov, var(--hy-well)); }
  .dvr .dwt::after { content: ""; position: absolute; right: 10px; top: 8px; width: 5px; height: 5px; border: solid var(--muted); border-width: 0 1.5px 1.5px 0;
    transform: rotate(45deg); pointer-events: none; }`;
