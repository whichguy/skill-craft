import test from "node:test";
import assert from "node:assert/strict";
import { createBoardState, selectSquare, resetBoard } from "../src/board-state.mjs";

test("selecting a square updates the local selection status", () => {
  assert.deepEqual(selectSquare(createBoardState(), "a1"), {
    selected: "a1",
    status: "Selected: a1"
  });
});

test("reset clears the selected square and restores the prompt", () => {
  assert.deepEqual(resetBoard(), { selected: null, status: "Choose a square" });
});

test("selection rejects coordinates outside the 8 by 8 board", () => {
  assert.throws(() => selectSquare(createBoardState(), "i9"), RangeError);
});
