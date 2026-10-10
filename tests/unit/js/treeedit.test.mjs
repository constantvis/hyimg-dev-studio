// treeedit.js and panel.js: what Edit mode reads from a field (name="value" as after a tag) and how History steps to a write
import test from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { REPO } from "./load.mjs";

const mod = f => import(pathToFileURL(path.join(REPO, f)).href);

test("attributes are typed as after a tag: quoted, unquoted, bare; anything else is no attribute", async () => {
  const { parseAttrs } = await mod("treeedit.js");
  assert.deepEqual(parseAttrs(`title="Hi there" data-k=1 hidden lang='en'`), { title: "Hi there", "data-k": "1", hidden: "", lang: "en" });
  assert.deepEqual(parseAttrs(`  Class="a b"  `), { class: "a b" });
  assert.equal(parseAttrs(""), null);
  assert.equal(parseAttrs(`="x"`), null);
  assert.equal(parseAttrs(`a="unclosed`), null);
});

test("History: the writes made then the undone ones in the order they were made; a click is that many undos or redos", async () => {
  const { timeline, stepsTo } = await mod("panel.js");
  const D = { past: [{ n: 1 }, { n: 2 }], future: [{ n: 4 }, { n: 3 }] };   // the top of future is the next redo
  assert.deepEqual(timeline(D).map(x => [x.s.n, x.on]), [[1, true], [2, true], [3, false], [4, false]]);
  assert.equal(stepsTo(D, -1), -2, "«Opened»: every write undone");
  assert.equal(stepsTo(D, 1), 0);
  assert.equal(stepsTo(D, 3), 2);
});
