// treecomments.js: a row path finds its node, the rows' counts and dots come from the open threads of this card, a count's clicks walk
// its threads (owner 2026-10-08: a comment from Dev Studio's tree)
import test, { afterEach } from "node:test";
import assert from "node:assert/strict";
import { nodeAt, makeTreeComments } from "../../../treecomments.js";

const TREE = { i: 1, t: "html", k: [{ i: 2, t: "head" }, { i: 3, t: "body", k: [{ i: 4, t: "header", k: [{ i: 5, t: "h1" }] }, { i: 6, t: "main" }] }] };

test("a row path finds its node and the rows above it, a stale path finds nothing", () => {
  assert.deepEqual(nodeAt(TREE, "html>body:1>header:0>h1:0"), { n: TREE.k[1].k[0].k[0], path: [1, 3, 4] });
  assert.deepEqual(nodeAt(TREE, "html"), { n: TREE, path: [] });
  assert.equal(nodeAt(TREE, "html>body:1>main:0"), null);   // the first child of body is a header
  assert.equal(nodeAt(TREE, "html>body:1>header:0>h1:3"), null);
  assert.equal(nodeAt(TREE, "svg>g:0"), null);
  assert.equal(nodeAt(null, "html"), null);
});

afterEach(() => { delete globalThis.window; });   // the fake board of setup() stays in this file

function setup(threads) {
  const opened = [];
  globalThis.window = { hyComments: { threads: () => threads, state: { open: null }, open: id => { opened.push(id); window.hyComments.state.open = id; },
    close: () => { opened.push("closed"); window.hyComments.state.open = null; } } };
  const D = { id: "h1", tree: { root: TREE } };
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const tc = makeTreeComments({ D: () => D, HY: {}, t: (k, v) => k.replace("{n}", v ? v.n : ""), esc, toPage() {}, select() {}, comment() {}, drawTree() {} });
  tc.count();
  return { tc, opened };
}
const th = (id, key, more = {}) => ({ id, anchor: { obj: "h1" }, element: { key }, updated: "2026-10-08T10:0" + id.slice(1) + ":00", ...more });

test("a row with open threads shows their count, a folded row with threads further in a dot, others nothing", () => {
  const { tc } = setup([th("c1", "html>body:1>header:0>h1:0"), th("c2", "html>body:1>header:0>h1:0"), th("c3", "html>body:1>main:1", { resolved: { by: {} } }),
    th("c4", "html>body:1>main:1", { anchor: { obj: "other" } })]);
  assert.match(tc.mark("html>body:1>header:0>h1:0", false), /class="dvcn"[^>]*>2<\/hy-button>/);
  assert.match(tc.mark("html>body:1>header:0", true), /<hy-badge class="dvcd" dot/);
  assert.equal(tc.mark("html>body:1>header:0", false), "");   // unfolded: the row itself shows the count
  assert.equal(tc.mark("html>body:1>main:1", false), "");   // resolved, or another card's
  assert.equal(tc.mark("html>body:1>head:0", true), "");
});

test("a click on the count opens the newest thread, then the next; one thread open closes again", () => {
  const { tc, opened } = setup([th("c1", "html>body:1>header:0>h1:0"), th("c2", "html>body:1>header:0>h1:0"), th("c5", "html>body:1>main:1")]);
  const row = key => ({ target: { closest: s => s === ".row" ? { dataset: { p: key, i: "5" } } : s === ".dvcn" ? {} : null } });
  tc.click(row("html>body:1>header:0>h1:0")); tc.click(row("html>body:1>header:0>h1:0")); tc.click(row("html>body:1>header:0>h1:0"));
  assert.deepEqual(opened, ["c2", "c1", "c2"]);
  tc.click(row("html>body:1>main:1")); tc.click(row("html>body:1>main:1"));
  assert.deepEqual(opened.slice(3), ["c5", "closed"]);
});
