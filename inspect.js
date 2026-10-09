// Dev mode's inspector controls (0.2, owner 2026-10-07: «Выделить объекты и поменять им цвет»): Layout (width and height when the page
// sets them, padding, gap of a flex or grid box), Appearance (opacity, corners), Fill, Text (colour, size, weight) and Stroke (colour,
// width) of the selected elements, from the app's primitives: hy-swatch with the native colour picker over it (as Settings › Paper
// colour), hy-segmented, the app's slider (ui/slider.js), a number field. A value that comes from a custom property shows it, and the
// choice «This element» or «Everywhere · N» (the property's declaration in the file). An element the file has not got (made by a script,
// implied by the parser) shows the reason and its controls are grey.
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const WEIGHTS = ["300", "400", "500", "600", "700", "800"];

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
  s = String(s || "").trim(); if (!s) return null;
  if (/^-?[\d.]+$/.test(s) && prop !== "opacity" && prop !== "font-weight") s += "px";
  if (prop === "padding") s = s.split(/\s+/).map(x => /^-?[\d.]+$/.test(x) ? x + "px" : x).join(" ");
  return typeof CSS !== "undefined" && CSS.supports && !CSS.supports(prop, s) ? null : s;
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
    let row = `<div class="dcr" data-p="${prop}"><span class="dcl">${esc(label)}</span><span class="dsw2"><hy-swatch color="${esc(o.v)}" label="${esc(label)}" tabindex="-1"></hy-swatch>`
      + `<input type="color" value="${hx}" aria-label="${esc(label)}" data-k="${prop}"></span><input class="dfi" data-c="${prop}" value="${esc(shown)}" spellcheck="false" aria-label="${esc(label)}">`;
    if (v) row += `<span class="dvar" title="${esc(o.from ? t("From {tag}", { tag: o.from }) : v)}">${esc(v)}</span>`;
    row += `</div>`;
    if (v) {
      const can = dv && dv.where === "root", tip = !dv ? t("{v} is declared outside this file", { v }) : dv.where !== "root" ? t("{v} is declared inside a rule Dev Studio doesn't write", { v }) : "";
      row += `<div class="dsc"><hy-segmented variant="well" value="${scope(prop)}" data-s="${prop}" label="${esc(v)}">`
        + `<button value="el">${esc(t("This element"))}</button><button value="all"${can ? "" : ` disabled data-tip="${esc(tip)}" title="${esc(tip)}"`}>`
        + `${esc(t("Everywhere · {n}", { n: dv ? dv.uses : 0 }))}</button></hy-segmented></div>`;
    }
    return row;
  };
  const field = (prop, label, val) => `<label class="dnf" data-p="${prop}"><span>${esc(label)}</span>`
    + `<input class="dfi" data-n="${prop}" value="${esc(val)}" spellcheck="false" aria-label="${esc(label)}"></label>`;
  const set = p => P[p].set && !/^(auto|initial|inherit|unset|normal)$/.test(P[p].set);
  const layout = [set("width") ? field("width", "W", num(P.width.v)) : "", set("height") ? field("height", "H", num(P.height.v)) : "",
    field("padding", t("Padding"), P.padding.v.split(" ").map(num).join(" ")), e.flex ? field("gap", t("Gap"), num(P.gap.v.split(" ")[0])) : ""].join("");
  const sec = (title, body, cls = "") => `<div class="dsec ded ${cls}"${off ? " inert" : ""}><div class="dsh hy-sh">${esc(title)}</div>${body}</div>`;
  const leaf = d.src && typeof d.src.text === "string";
  return (off ? `<p class="hy-hint dhint doff">${icon("lock", 13)} ${off}</p>` : leaf ? `<p class="hy-hint dhint">${t("<b>Double-click</b> the text or <b>Enter</b> to type it")}</p>` : "")
    + sec(t("Layout"), `<div class="dgrid">${layout}</div>`)
    + sec(t("Appearance"), `<div class="dop" data-p="opacity"></div><div class="dgrid">${field("border-radius", t("Corners"), num(P["border-radius"].v))}</div>`)
    + sec(t("Fill"), colorRow("background-color", t("Fill")))
    + sec(t("Text"), colorRow("color", t("Colour")) + `<div class="dgrid">${field("font-size", t("Size"), num(P["font-size"].v))}</div>`
      + `<div class="dwt"><hy-segmented variant="well" value="${esc(P["font-weight"].v)}" data-w="1" label="${esc(t("Weight"))}">`
      + `${WEIGHTS.map(w => `<button value="${w}">${w}</button>`).join("")}</hy-segmented></div>`)
    + sec(t("Stroke"), colorRow("border-color", t("Stroke")) + `<div class="dgrid">${field("border-width", t("Width"), P["border-width"].v.split(" ").map(num).join(" "))}</div>`);
}

// the controls' events: each change goes to edits.style (live now, written when it settles)
export function wire(root, D, edits, t) {
  const d = D.detail; if (!d || !d.ed) return;
  const P = d.ed.p, sc = k => (D.scope && D.scope[k]) || "el";
  const send = (prop, value, commit) => {
    const v = P[prop] && P[prop].var, all = v && sc(prop) === "all";
    const also = prop === "border-width" && /none|hidden/.test(P["border-style"].v) && value && !/^0(px)?$/.test(value) ? { "border-style": "solid" } : null;
    edits.style(prop, value, { scope: all ? "all" : "el", v, commit, also });
  };
  root.querySelectorAll("input[type=color]").forEach(inp => {
    const prop = inp.dataset.k, sw = inp.previousElementSibling, txt = root.querySelector(`[data-c="${prop}"]`);
    inp.addEventListener("input", () => { sw.setAttribute("color", inp.value); txt.value = inp.value; send(prop, inp.value, false); });
    inp.addEventListener("change", () => send(prop, inp.value, true));
  });
  root.querySelectorAll("input[data-c]").forEach(inp => {
    const prop = inp.dataset.c;
    const go = () => { const v = typed("color", inp.value); if (!v) { inp.classList.add("bad"); return; } inp.classList.remove("bad"); send(prop, v, true); };
    inp.addEventListener("keydown", e => { e.stopPropagation(); if (e.key === "Enter") { e.preventDefault(); go(); inp.blur(); } if (e.key === "Escape") inp.blur(); });
    inp.addEventListener("change", go);
  });
  root.querySelectorAll("input[data-n]").forEach(inp => {
    const prop = inp.dataset.n;
    const go = () => { const v = typed(prop, inp.value); if (!v) { inp.classList.add("bad"); return; } inp.classList.remove("bad"); send(prop, v, true); };
    inp.addEventListener("keydown", e => {
      e.stopPropagation();
      if (e.key === "Enter") { e.preventDefault(); go(); inp.blur(); }
      else if (e.key === "Escape") inp.blur();
      else if ((e.key === "ArrowUp" || e.key === "ArrowDown") && /^-?[\d.]+$/.test(inp.value.trim())) {
        e.preventDefault(); const n = +inp.value + (e.key === "ArrowUp" ? 1 : -1) * (e.shiftKey ? 10 : 1);
        inp.value = String(Math.max(prop === "padding" || prop === "border-width" || prop === "font-size" ? 0 : -1e4, Math.round(n * 100) / 100)); send(prop, inp.value + "px", false);
      }
    });
    inp.addEventListener("change", go);
  });
  root.querySelectorAll("hy-segmented[data-s]").forEach(s => s.addEventListener("hy-change", e => { D.scope = Object.assign({}, D.scope, { [s.dataset.s]: e.detail.value }); D.redraw(); }));
  const w = root.querySelector("hy-segmented[data-w]");
  if (w) w.addEventListener("hy-change", e => send("font-weight", e.detail.value, true));
  const op = root.querySelector(".dop");
  if (op && window.hySlider) {
    const s = window.hySlider.create({ label: t("Opacity"), min: 0, max: 100, step: 1, unit: "%", value: Math.round(parseFloat(P.opacity.v || "1") * 100),
      onInput: v => send("opacity", String(Math.round(v) / 100), false), onChange: v => send("opacity", String(Math.round(v) / 100), true) });
    op.appendChild(s.el);
  }
}

export const CSS_EDIT = `
  .dvr .ded[inert] { opacity: .45; }
  .dvr .ded .dsh { padding-left: 6px; }
  .dvr .doff svg { vertical-align: -2px; margin-right: 2px; }
  .dvr .dcr { display: flex; align-items: center; gap: 8px; min-height: 32px; padding: 0 6px; }
  .dvr .dcr .dcl { flex: 0 0 52px; color: var(--sub); font-size: 12px; }
  .dvr .dsw2 { position: relative; display: inline-flex; flex: none; width: 22px; height: 22px; align-items: center; justify-content: center; }
  .dvr .dsw2 hy-swatch { pointer-events: none; }
  .dvr .dsw2 input[type=color] { position: absolute; inset: 0; width: 100%; height: 100%; margin: 0; padding: 0; opacity: 0; cursor: pointer; border: 0; }
  .dvr .dfi { min-width: 0; flex: 1; height: var(--hy-ctl-h, 24px); box-sizing: border-box; padding: 0 8px; border: 1px solid transparent; border-radius: var(--hy-row-r, 999px);
    background: var(--hy-well, transparent); color: var(--ink); font: 12px ui-monospace, "SF Mono", Menlo, monospace; outline: none;
    transition: border-color .2s cubic-bezier(.32,.72,0,1), background-color .2s cubic-bezier(.32,.72,0,1); }   /* a dark well (round 12) */
  .dvr .dfi:hover { background: var(--hy-well-hov, transparent); }
  .dvr .dfi:focus { border-color: var(--sel); } .dvr .dfi.bad { border-color: var(--hy-red); }
  .dvr .dvar { flex: none; max-width: 92px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font: 11px ui-monospace, "SF Mono", Menlo, monospace;
    color: var(--ink); padding: 3px 8px; border-radius: var(--hy-row-r, 999px); background: var(--raise); }
  .dvr .dsc { padding: 2px 6px 6px 66px; } .dvr .dsc hy-segmented { width: 100%; }
  .dvr .dgrid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--hy-gap-ctl, 4px); padding: 2px 6px 4px; }
  .dvr .dnf { display: flex; align-items: center; gap: 6px; min-width: 0; } .dvr .dnf > span { flex: none; color: var(--sub); font-size: 12px; min-width: 14px; }
  .dvr .dnf[data-p=padding] { grid-column: span 2; } .dvr .dnf[data-p=padding] > span { flex-basis: 52px; }
  .dvr .dop { padding: 2px 6px 4px; } .dvr .dwt { padding: 4px 6px 6px; } .dvr .dwt hy-segmented { width: 100%; }`;
