"use strict";

// In-process rules cases. HTTP status checks are a later item.

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");
const { createGame, fire, occupiedCells } = require("../game.js");

const LENGTHS = {
  carrier: 5,
  battleship: 4,
  cruiser: 3,
  submarine: 3,
  destroyer: 2,
};

function call(fn) {
  let outcome;
  assert.doesNotThrow(() => {
    outcome = fn();
  });
  return outcome;
}

function errorOnly(value) {
  assert.equal(typeof value.error, "string");
  assert.ok(value.error.length > 0);
  assert.equal(Object.hasOwn(value, "game"), false);
  assert.equal(Object.hasOwn(value, "result"), false);
}

function destroyer() {
  const created = call(() => createGame({
    ships: [{ name: "destroyer", cells: [[0, 0], [0, 1]] }],
  }));
  assert.equal(created.error, undefined);
  assert.equal(typeof created.game, "string");
  assert.ok(created.game.length > 0);
  return created;
}

function assertFleet(created) {
  assert.equal(created.error, undefined);
  assert.equal(typeof created.game, "string");
  assert.ok(created.game.length > 0);
  assert.equal(created.ships.length, 5);
  assert.deepEqual(
    created.ships.map((ship) => ship.name),
    ["carrier", "battleship", "cruiser", "submarine", "destroyer"],
  );
  const seen = new Set();
  for (const ship of created.ships) {
    assert.equal(ship.cells.length, LENGTHS[ship.name]);
    const rows = ship.cells.map((cell) => cell[0]);
    const cols = ship.cells.map((cell) => cell[1]);
    const sameRow = rows.every((row) => row === rows[0]);
    const sameCol = cols.every((col) => col === cols[0]);
    assert.notEqual(sameRow, sameCol);
    const vary = (sameRow ? cols : rows).slice().sort((left, right) => left - right);
    for (let index = 0; index < vary.length; index++) {
      assert.equal(vary[index], vary[0] + index);
    }
    for (const cell of ship.cells) {
      assert.ok(Number.isInteger(cell[0]) && cell[0] >= 0 && cell[0] <= 9);
      assert.ok(Number.isInteger(cell[1]) && cell[1] >= 0 && cell[1] <= 9);
      const id = cell[0] + "," + cell[1];
      assert.equal(seen.has(id), false);
      seen.add(id);
    }
  }
  assert.equal(seen.size, 17);
  const stored = occupiedCells(created.game).map((cell) => cell[0] + "," + cell[1]).sort();
  assert.deepEqual(stored, [...seen].sort());
}

test("TC-5 destroyer sequence", () => {
  const src = fs.readFileSync(path.join(__dirname, "..", "game.js"), "utf8");
  assert.ok(src.includes("// Contract: createGame"));
  assert.ok(src.includes("// Contract: fire"));
  errorOnly(call(() => createGame()));
  errorOnly(call(() => createGame({})));
  errorOnly(call(() => createGame({ ships: "no" })));
  errorOnly(call(() => fire()));
  errorOnly(call(() => fire("missing", 0, 0)));
  const created = destroyer();
  assert.deepEqual(fire(created.game, 0, 0), { result: "hit", gameOver: false });
  assert.deepEqual(fire(created.game, 0, 0), { result: "hit", gameOver: false });
  assert.deepEqual(fire(created.game, 1, 0), { result: "miss", gameOver: false });
  assert.deepEqual(fire(created.game, 0, 1), { result: "sunk", gameOver: true });
  assert.deepEqual(occupiedCells(created.game), [[0, 0], [0, 1]]);
});

test("TC-5 (a) repeat after the fleet is sunk", () => {
  const created = destroyer();
  assert.deepEqual(fire(created.game, 0, 0), { result: "hit", gameOver: false });
  assert.deepEqual(fire(created.game, 0, 1), { result: "sunk", gameOver: true });
  assert.deepEqual(fire(created.game, 0, 0), { result: "hit", gameOver: true });
  assert.deepEqual(occupiedCells(created.game), [[0, 0], [0, 1]]);
});

test("TC-7 illegal shots leave occupied cells", () => {
  const created = destroyer();
  assert.deepEqual(occupiedCells(created.game), [[0, 0], [0, 1]]);
  const shots = [
    () => fire(created.game, 1.5, 0),
    () => fire(created.game, -1, 0),
    () => fire(created.game, 10, 0),
    () => fire(created.game, 0, -1),
    () => fire(created.game, 0, 10),
    () => fire(created.game, 0),
    () => fire(created.game, undefined, 0),
  ];
  for (const shot of shots) {
    errorOnly(call(shot));
    assert.deepEqual(occupiedCells(created.game), [[0, 0], [0, 1]]);
  }
  assert.deepEqual(fire(created.game, 0, 0), { result: "hit", gameOver: false });
});

test("TC-8 seed 1 places the five-ship fleet", () => {
  const first = call(() => createGame({ seed: 1 }));
  assertFleet(first);
  const second = call(() => createGame({ seed: 1 }));
  assertFleet(second);
  assert.deepEqual(second.ships, first.ships);
});

test("TC-8 (a) another integer seed repeats its ships", () => {
  const first = call(() => createGame({ seed: 2 }));
  assertFleet(first);
  const second = call(() => createGame({ seed: 2 }));
  assert.deepEqual(second.ships, first.ships);
});

test("TC-9 overlapping carrier and battleship are rejected", () => {
  const created = call(() => createGame({
    ships: [
      { name: "carrier", cells: [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4]] },
      { name: "battleship", cells: [[0, 0], [1, 0], [2, 0], [3, 0]] },
    ],
  }));
  errorOnly(created);
});

test("TC-9 (a) another shared cell is rejected", () => {
  errorOnly(call(() => createGame({
    ships: [
      { name: "destroyer", cells: [[0, 1], [0, 2]] },
      { name: "destroyer", cells: [[0, 2], [1, 2]] },
    ],
  })));
  errorOnly(call(() => createGame({
    ships: [{ name: "destroyer", cells: [[0, 0], [0, 0]] }],
  })));
});

test("TC-10 touching ships and the column bounds", () => {
  const touching = call(() => createGame({
    ships: [
      { name: "destroyer", cells: [[0, 0], [0, 1]] },
      { name: "destroyer", cells: [[1, 0], [1, 1]] },
    ],
  }));
  assert.equal(touching.error, undefined);
  assert.deepEqual(touching.ships.map((ship) => ship.cells), [
    [[0, 0], [0, 1]],
    [[1, 0], [1, 1]],
  ]);
  assert.deepEqual(occupiedCells(touching.game), [[0, 0], [0, 1], [1, 0], [1, 1]]);
  const carrier = call(() => createGame({
    ships: [{ name: "carrier", cells: [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4]] }],
  }));
  assert.equal(carrier.error, undefined);
  assert.deepEqual(carrier.ships[0].cells, [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4]]);
  assert.deepEqual(occupiedCells(carrier.game), [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4]]);
  errorOnly(call(() => createGame({
    ships: [{ name: "carrier", cells: [[0, 6], [0, 7], [0, 8], [0, 9], [0, 10]] }],
  })));
});

test("TC-10 (a) a cell off the board other than column 10 is rejected", () => {
  errorOnly(call(() => createGame({
    ships: [{ name: "carrier", cells: [[6, 0], [7, 0], [8, 0], [9, 0], [10, 0]] }],
  })));
  errorOnly(call(() => createGame({
    ships: [{ name: "destroyer", cells: [[0, -1], [0, 0]] }],
  })));
});
