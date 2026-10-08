// cards.js: which still an HTML card asks for and which cards get the four live pages (owner 2026-10-08: «справа мазня»)
import test from "node:test";
import assert from "node:assert/strict";
import { stepFor, nextStep, plan, LIVE_MAX } from "../../../cards.js";

test("the still matches the card's width on screen in device pixels", () => {
  assert.equal(stepFor(288), 640);    // 720 board units at 20 % on a Retina screen
  assert.equal(stepFor(700), 640);    // up to 10 % short of a step is fine
  assert.equal(stepFor(864), 1280);   // at 60 %
  assert.equal(stepFor(2203), 2560);  // at 153 %: the owner's two cards
  assert.equal(stepFor(9000), 2560);  // there is nothing bigger
});

test("up at once, down only once clearly smaller, no swaps back and forth at a step", () => {
  assert.equal(nextStep(undefined, 300), 640);
  assert.equal(nextStep(640, 2203), 2560);
  assert.equal(nextStep(2560, 1300), 2560);   // just under the 1280 step: kept
  assert.equal(nextStep(2560, 1000), 1280);
  assert.equal(nextStep(2560, 288), 640);
  assert.equal(nextStep(1280, 760), 1280);
});

const card = (id, o) => ({ id, live: false, vis: true, px: 1100, d: 0, sel: 0, gone: false, ...o });

test("cards off screen never take a page from cards on it (the owner's board: the row above lay in the view pass first)", () => {
  const cards = [card("c2", { vis: false, d: 9 }), card("c3", { vis: false, d: 8 }), card("c6", { vis: false, d: 7 }),
    card("c4", { d: 0 }), card("c4b", { d: 1 })];
  assert.deepEqual(plan(cards), { start: ["c4", "c4b"], stop: [] });
  // they held pages already: at rest they go, the two on screen start
  const held = cards.map(c => ({ ...c, live: !c.vis }));
  assert.deepEqual(plan(held), { start: ["c4", "c4b"], stop: ["c2", "c3", "c6"] });
});

test("the nearest the centre first, the selected card before all; the farthest live one gives way", () => {
  const cards = ["a", "b", "c", "d", "e"].map((id, k) => card(id, { d: k, live: k > 0 }));
  assert.deepEqual(plan(cards), { start: ["a"], stop: ["e"] });
  const sel = cards.map(c => ({ ...c, live: false, sel: c.id === "e" ? 1 : 0 }));
  assert.deepEqual(plan(sel).start, ["e", "a", "b", "c"]);
});

test("small cards get none, a live one keeps its page down to 280 px", () => {
  assert.deepEqual(plan([card("a", { px: 300 })]), { start: [], stop: [] });
  assert.deepEqual(plan([card("a", { px: 300, live: true })]), { start: [], stop: [] });
  assert.deepEqual(plan([card("a", { px: 270, live: true })]), { start: [], stop: ["a"] });
});

test("while the board moves nothing starts and a page off screen stays; one outside the view pass goes", () => {
  const cards = [card("a"), card("b", { vis: false, live: true }), card("c", { gone: true, live: true })];
  assert.deepEqual(plan(cards, { moving: true }), { start: [], stop: ["c"] });
});

test("never more than four", () => {
  const cards = Array.from({ length: 9 }, (_, k) => card("c" + k, { d: k }));
  assert.equal(plan(cards).start.length, LIVE_MAX);
});
