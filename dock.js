// Dev Studio's dock on Hyimg's one dock (hyimg review/ui/dock.js, ui/palette.js; owner 2026-10-10 on round 18, r18-dock.html, ★ yes):
//   Select, Annotation | Undo, Redo | the view % | Actions | the switch of Studios
// Undo and Redo name their step on a plate over them under the pointer and for 2 s after ⌘Z or ⇧⌘Z (hyDock.steps, History's words:
// panel.js stepName). The view % is the board's zoom of the card, a click puts the card back between the panels (Hyimg's boarddock.js).
// Actions (⌘K, Hyimg's palette as in Image Studio) lists what the dock, the keys and the session actions top right do.
//   const K = studioDock({ D, t, svg, EDITS, PN, pick, comment, edit, reload, done, del })   K.done(dir)   K.toggle()   K.destroy()
export function studioDock(o) {
  const H = window.hyDock, d = o.D(), t = o.t; if (!H || !d || !d.bar) return null;
  const q = s => d.bar.querySelector(s), ic = n => o.svg(n, 16);
  const name = dir => { const x = o.D(); if (!x) return ""; const s = dir === "undo" ? x.past[x.past.length - 1] : x.future[x.future.length - 1]; return s ? o.PN.stepName(s) : ""; };
  const S = H.steps({ undo: q("[data-a=undo]"), redo: q("[data-a=redo]"), name });
  const open = () => { const b = document.querySelector(".dvui hy-studio-actions [data-a=open] .oi-go, .dvui hy-studio-actions [data-a=open]"); if (b) b.click(); };
  const items = () => {
    const x = o.D() || { past: [], future: [] }, g = { tools: t("Tools"), edit: t("Edit"), view: t("View"), studio: "Dev Studio" };
    return [
      { label: t("Select"), group: g.tools, icon: ic("select"), keys: ["V"], fn: o.pick },
      { label: t("Annotation"), group: g.tools, icon: ic("comment"), keys: ["C"], fn: o.comment },
      { label: t("Edit HTML"), group: g.tools, icon: ic("code"), keys: ["E"], fn: o.edit },
      { label: t("Undo"), group: g.edit, icon: ic("undo"), keys: ["⌘", "Z"], hint: name("undo"), dis: !x.past.length, fn: () => o.EDITS.undo() },
      { label: t("Redo"), group: g.edit, icon: ic("redo"), keys: ["⇧", "⌘", "Z"], hint: name("redo"), dis: !x.future.length, fn: () => o.EDITS.redo() },
      { label: t("Delete the element"), group: g.edit, icon: ic("trash"), keys: ["⌫"], dis: !(x.edit && x.sel), fn: o.del },
      { label: t("Fit the card between the panels"), group: g.view, icon: ic("fit"), fn: () => { const f = document.getElementById("bfit"); if (f) f.click(); } },
      { label: t("Reload the page"), group: g.view, icon: ic("sync"), keys: ["⌥", "R"], fn: o.reload },
      { label: t("Open in browser"), group: g.view, icon: ic("open"), fn: open },
      { label: t("Done"), group: g.studio, icon: ic("check"), keys: ["⌘", "↵"], fn: o.done },
    ];
  };
  const P = window.hyPalette ? window.hyPalette({ id: "dev", items, primary: o.done, anchor: () => { const k = document.getElementById("dock"); return k && k.getBoundingClientRect(); } }) : null;
  const slot = q("[data-dk=acts]"); if (slot && P) slot.replaceWith(H.acts(() => P.toggle()));
  return { done: dir => S.done(dir), toggle: () => P && P.toggle(), destroy() { if (P) P.destroy(); } };
}
