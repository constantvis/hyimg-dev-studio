// agent.js: the inspector inside a library page talks to the board only by postMessage: the page's tree, an element's detail, the
// pick in inspect mode, the tree again when the page changes. Run on the fake DOM with a fake parent window that records messages.
import test from "node:test";
import assert from "node:assert/strict";
import { page, plain } from "./load.mjs";

const PAGE = `<main id="app" class=" card   wide "><h1>  Hello
  world </h1><ul><li>One</li><li>Two</li></ul><script src="/~hyp/dev/agent.js"></script><script>var x = 1</script><style>p{}</style><svg><text>t</text></svg></main>`;

function agent(markup = PAGE) {
  const p = page();
  const RealDate = Date, clock = p.clock;
  p.window.Date = class extends RealDate { static now() { return clock.now; } };
  const sent = [], parent = { postMessage: (m, origin) => sent.push(plain({ m, origin })) };
  p.window.parent = parent;
  p.document.title = "Demo";
  p.html(markup);
  p.load("agent.js");
  const msgs = key => sent.map(s => s.m).filter(m => key in m);
  const ask = (a, extra = {}) => p.fire(p.window, "message", { data: { hydev: 2, a, ...extra }, source: parent }, { bubbles: false });
  const byTag = (node, t, out = []) => { if (node.t === t) out.push(node); (node.k || []).forEach(k => byTag(k, t, out)); return out; };
  return { p, sent, parent, msgs, ask, byTag };
}

test("the page says it is ready with its tree, title and viewport, to any origin (the board's frame is opaque)", () => {
  const { sent } = agent();
  const first = sent[0];
  assert.equal(first.origin, "*");
  assert.equal(first.m.hydev, 1);
  assert.equal(first.m.ready, true);
  assert.equal(first.m.title, "Demo");
  assert.deepEqual([first.m.vw, first.m.vh], [1280, 800]);
  assert.equal(first.m.tree.root.t, "html");
  assert.equal(first.m.tree.cut, false);
});

test("a tree node has its tag, id, classes tidied and a leaf's text squeezed", () => {
  const { msgs, byTag } = agent();
  const root = msgs("tree")[0].tree.root;
  const main = byTag(root, "main")[0], h1 = byTag(root, "h1")[0];
  assert.equal(main.d, "app");
  assert.equal(main.c, "card wide");
  assert.equal(h1.x, "Hello world");
  assert.deepEqual(byTag(root, "li").map(n => n.x), ["One", "Two"]);
});

test("the inspector's own script is left out of the tree, the page's scripts, styles and svg stay without their text", () => {
  const { msgs, byTag } = agent();
  const root = msgs("tree")[0].tree.root;
  const scripts = byTag(root, "script");
  assert.equal(scripts.length, 1, "only the page's own script");
  assert.equal(scripts[0].x, undefined);
  assert.equal(byTag(root, "style")[0].x, undefined);
  assert.equal(byTag(root, "svg")[0].k[0].t, "text");
});

test("asked again, the tree keeps every element's id", () => {
  const { msgs, ask } = agent();
  ask("tree");
  const [a, b] = msgs("tree").map(m => JSON.stringify(m.tree));
  assert.equal(a, b);
});

test("a page of more than 15000 elements is cut at 15000 and says so", () => {
  const { msgs } = agent(`<div>${"<i></i>".repeat(15050)}</div>`);
  const t = msgs("tree")[0].tree;
  assert.equal(t.n, 15000);
  assert.equal(t.cut, true);
});

test("a long id, class list and text are cut to their limits", () => {
  const { msgs, byTag } = agent(`<p id="${"i".repeat(200)}" class="${"c".repeat(300)}">${"word ".repeat(40)}</p>`);
  const p = byTag(msgs("tree")[0].tree.root, "p")[0];
  assert.equal(p.d.length, 120); assert.equal(p.c.length, 200); assert.equal(p.x.length, 80);
});

// the selection: the detail of one element
function selected(computed, markup = `<div id="box" class="a b" data-x="1" style="color: red">x</div>`) {
  const t = agent(markup);
  const box = t.p.document.getElementById("box");
  box._rect = { left: 10, top: 20, width: 100.04, height: 50.06 }; box._computed = computed;
  t.p.window.scrollX = 5; t.p.window.scrollY = 300;
  const id = (function find(n) { if (n.d === "box") return n.i; for (const k of n.k || []) { const r = find(k); if (r) return r; } })(t.msgs("tree")[0].tree.root);
  t.ask("sel", { i: id });
  return { ...t, id, detail: t.msgs("detail").at(-1).detail };
}

test("a selected element's detail has its box in page coordinates, its attributes and its path of ids from the html down", () => {
  const { detail, id } = selected({});
  assert.deepEqual(detail.box, { x: 15, y: 320, w: 100, h: 50.1 });
  assert.equal(detail.t, "div");
  assert.deepEqual(detail.c, ["a", "b"]);
  assert.deepEqual(detail.attrs.map(a => a[0]), ["id", "class", "data-x", "style"]);
  assert.equal(detail.path.at(-1), id);
  assert.equal(detail.path.length, 3, "html, body, the div");
});

test("box sides are written short as CSS does: one value, a pair, or four", () => {
  const side = (pre, v, post = "") => Object.fromEntries(["top", "right", "bottom", "left"].map((s, i) => [`${pre}-${s}${post}`, v[i]]));
  const style = (d, k) => Object.fromEntries(d.styles)[k];
  const a = selected({ display: "block", ...side("margin", ["0px", "0px", "0px", "0px"]), ...side("padding", ["8px", "16px", "8px", "16px"]), ...side("border", ["1px", "2px", "3px", "4px"], "-width") }).detail;
  assert.equal(style(a, "margin"), "0px");
  assert.equal(style(a, "padding"), "8px 16px");
  assert.equal(style(a, "border-width"), "1px 2px 3px 4px");
});

test("flex and gap show only for a flex or grid box", () => {
  const keys = d => d.styles.map(s => s[0]);
  assert.equal(keys(selected({ display: "block" }).detail).includes("gap"), false);
  assert.equal(keys(selected({ display: "inline-flex" }).detail).includes("flex-direction"), true);
  assert.equal(keys(selected({ display: "grid" }).detail).includes("gap"), true);
});

test("a selection of an element that is gone sends no detail", () => {
  const { ask, msgs } = agent();
  ask("sel", { i: 99999 });
  assert.equal(msgs("detail").at(-1).detail, null);
});

test("a message from anyone but the board, or not of the protocol, is ignored", () => {
  const { p, sent } = agent();
  const n = sent.length;
  p.fire(p.window, "message", { data: { hydev: 2, a: "tree" }, source: {} }, { bubbles: false });
  p.fire(p.window, "message", { data: { hydev: 1, a: "tree" }, source: p.window.parent }, { bubbles: false });
  assert.equal(sent.length, n);
});

test("Escape in the page is sent to the board", () => {
  const { p, msgs } = agent();
  p.fire(p.window, "keydown", { key: "Escape" });
  assert.deepEqual(msgs("key").map(m => m.key), ["Escape"]);
});

test("in inspect mode a press picks the element under the pointer instead of reaching the page", () => {
  const { p, ask, msgs } = agent();
  const li = p.document.querySelectorAll("li")[1];
  p.document.elementFromPoint = () => li;
  ask("inspect", { on: true });
  const catcher = p.document.querySelector("hy-dev-marks").shadowRoot.querySelector(".c");
  assert.equal(catcher.style.display, "block");
  const e = p.fire(catcher, "pointerdown", { clientX: 30, clientY: 40 });
  assert.equal(e.defaultPrevented, true);
  const pick = msgs("pick").at(-1);
  assert.equal(pick.detail.t, "li");
  assert.equal(pick.path.at(-1), pick.pick);
  assert.equal(pick.path.length, 5, "html, body, main, ul, li");
  ask("inspect", { on: false });
  assert.equal(catcher.style.display, "none");
});

test("the page changing sends the tree again, at most once a second", () => {
  const { p, msgs } = agent();
  const ul = p.document.querySelector("ul");
  ul.appendChild(p.document.createElement("li")); ul.appendChild(p.document.createElement("li"));
  return p.flush().then(async () => {
    p.tick(300); assert.equal(msgs("tree").length, 2, "one tree for both changes, 300 ms after them");
    ul.appendChild(p.document.createElement("li")); await p.flush();
    p.tick(500); assert.equal(msgs("tree").length, 2, "not within a second of the last");
    p.tick(500); assert.equal(msgs("tree").length, 3);
    assert.equal(msgs("tree").at(-1).tree.root.k[1].k[0].k[1].k.length, 5);
  });
});

test("the inspector's own marks are never taken for a change of the page", async () => {
  const { p, ask, msgs } = agent();
  ask("hl", { i: 1 }); await p.flush(); p.tick(2000);
  assert.equal(msgs("tree").length, 1);
  assert.ok(p.document.querySelector("hy-dev-marks"));
});

test("⌘. hides the marks with the board's interface and brings them back", () => {
  const { p, ask } = agent();
  ask("hl", { i: 1 });
  const host = p.document.querySelector("hy-dev-marks");
  ask("marks", { on: false }); assert.equal(host.style.display, "none");
  ask("marks", { on: true }); assert.equal(host.style.display, "");
});

test("the hover mark is labelled with the tag, id, two classes and the size", () => {
  const { p, ask, msgs } = agent();
  const main = p.document.getElementById("app"); main._rect = { left: 0, top: 100, width: 640.4, height: 80 };
  const id = msgs("tree")[0].tree.root.k[1].k[0].i;
  ask("hl", { i: id });
  const label = p.document.querySelector("hy-dev-marks").shadowRoot.querySelector(".l");
  assert.equal(label.textContent, "main#app.card.wide  640 × 80");
  assert.equal(label.style.top, "78px", "above the element");
});

test("the inspector stays out of a page that is not in a frame", () => {
  const p = page(); p.load("agent.js");
  assert.equal(p.window.__hyDevAgent, undefined);
});
