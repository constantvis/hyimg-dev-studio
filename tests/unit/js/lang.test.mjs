// lang.js: the plugin's Russian words, how they reach the board's T, and the English a board without T shows
import test from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { REPO, read } from "./load.mjs";

let n = 0;
const fresh = () => import(pathToFileURL(path.join(REPO, "lang.js")).href + "?fresh=" + ++n);   // its «strings handed over» flag starts unset
const holes = s => [...String(s).matchAll(/\{(\w+)\}/g)].map(m => m[1]).sort().join(",");

test("every Russian word has exactly the placeholders of its English key, in every form", async () => {
  const { RU } = await fresh(), bad = [];
  for (const [k, v] of Object.entries(RU)) for (const form of [].concat(v)) if (holes(form) !== holes(k)) bad.push(`«${k}» → «${form}»`);
  assert.deepEqual(bad, []);
});

test("every English plural has two forms and a Russian one of three", async () => {
  const { RU, EN } = await fresh();
  for (const [k, v] of Object.entries(EN)) { assert.equal(v.length, 2, k); assert.ok(Array.isArray(RU[k]) && RU[k].length === 3, k); }
});

test("every key the card, Dev mode, its inspector and its edits ask for has its Russian", async () => {
  const { RU } = await fresh(), missing = [];
  for (const m of ["canvas.js", "inspect.js", "edits.js"].map(read).join("\n").matchAll(/\bt\(\s*"((?:[^"\\]|\\.)*)"/g)) { const k = JSON.parse('"' + m[1] + '"'); if (!(k in RU)) missing.push(k); }
  assert.deepEqual(missing, []);
});

test("short labels have no full stop at the end, in either language", async () => {
  const { RU } = await fresh(), bad = [];
  for (const [k, v] of Object.entries(RU)) for (const s of [k, ...[].concat(v)]) if (s.length <= 40 && /[^.]\.$/.test(s)) bad.push(s);
  assert.deepEqual(bad, []);
});

test("a board with T gets the words once, every key under the plugin's prefix", async () => {
  const L = await fresh(), handed = [];
  const t = L.translator({ t: k => `T(${k})`, strings: d => handed.push(d) });
  assert.equal(handed.length, 1);
  assert.ok(Object.keys(handed[0].ru).every(k => k.startsWith("dev::")));
  assert.deepEqual(Object.keys(handed[0].en), ["dev::{n} elements"]);
  assert.equal(t("HTML page"), "T(dev::HTML page)");
});

test("a board without T shows the English, plurals by the number", async () => {
  const { translator } = await fresh(), t = translator({});
  assert.equal(t("HTML page"), "HTML page");
  assert.equal(t("{n} elements", { n: 1 }), "1 element");
  assert.equal(t("{n} elements", { n: 12 }), "12 elements");
});
