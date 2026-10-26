"use strict";

// Shot rules for one process. server.js will require this file; it does not listen.

const crypto = require("node:crypto");

/** @type {Map<string, {ships: {name: string, cells: number[][]}[], fired: Set<string>, results: Map<string, string>}>} */
const games = new Map();

function fail(message) {
  return { error: message };
}

function isRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function key(row, col) {
  return row + "," + col;
}

const FLEET = [
  { name: "carrier", length: 5 },
  { name: "battleship", length: 4 },
  { name: "cruiser", length: 3 },
  { name: "submarine", length: 3 },
  { name: "destroyer", length: 2 },
];

function randomFrom(seed) {
  let state = seed >>> 0;
  return function () {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

function placeFleet(seed) {
  const random = randomFrom(seed);
  const occupied = new Set();
  const ships = [];
  for (const spec of FLEET) {
    let placed = null;
    for (let attempt = 0; attempt < 400 && !placed; attempt++) {
      const horizontal = random() < 0.5;
      const row = Math.floor(random() * 10);
      const col = Math.floor(random() * 10);
      const cells = [];
      let fits = true;
      for (let offset = 0; offset < spec.length; offset++) {
        const r = horizontal ? row : row + offset;
        const c = horizontal ? col + offset : col;
        if (r > 9 || c > 9 || occupied.has(key(r, c))) {
          fits = false;
          break;
        }
        cells.push([r, c]);
      }
      if (fits) placed = cells;
    }
    if (!placed) return null;
    for (const cell of placed) occupied.add(key(cell[0], cell[1]));
    ships.push({ name: spec.name, cells: placed });
  }
  return ships;
}

// Contract: createGame
/**
 * Store a caller-supplied placement, or place the five-ship fleet from a seed.
 * @param {object} options options.ships is an array of {name, cells}, or options.seed is an integer and ships is absent.
 * @returns {{game: string, ships: {name: string, cells: number[][]}[]} | {error: string}}
 * Each cell is an integer pair inside 0 through 9, and no two ships share a cell. Ships may touch.
 * Success stores the game in this process only. It does not throw. The same seed returns the same ships.
 * A rejected placement stores nothing.
 */
function createGame(options) {
  if (!isRecord(options)) {
    return fail("createGame requires an object with ships or seed, and received " + (options === undefined ? "nothing" : typeof options) + ".");
  }
  const hasShips = Object.prototype.hasOwnProperty.call(options, "ships");
  const hasSeed = Object.prototype.hasOwnProperty.call(options, "seed");
  if (hasShips && hasSeed) {
    return fail("createGame accepts ships or seed, and received both.");
  }
  let source;
  if (hasShips) {
    if (!Array.isArray(options.ships)) {
      return fail("createGame requires ships to be an array, and received " + typeof options.ships + ".");
    }
    source = options.ships;
  } else if (hasSeed) {
    if (!Number.isInteger(options.seed)) {
      return fail("createGame requires seed to be an integer, and received " + String(options.seed) + ".");
    }
    source = placeFleet(options.seed);
    if (!source) {
      return fail("createGame could not place the five-ship fleet for seed " + options.seed + ".");
    }
  } else {
    return fail("createGame requires ships or seed, and received neither.");
  }
  const ships = [];
  const occupied = new Set();
  for (const ship of source) {
    if (!isRecord(ship) || typeof ship.name !== "string" || ship.name.length === 0 || !Array.isArray(ship.cells)) {
      return fail("each ship requires a non-empty name and a cells array");
    }
    const cells = [];
    for (const cell of ship.cells) {
      if (!Array.isArray(cell) || cell.length !== 2 || !Number.isInteger(cell[0]) || !Number.isInteger(cell[1])) {
        return fail("each cell must be a pair of integers");
      }
      if (cell[0] < 0 || cell[0] > 9 || cell[1] < 0 || cell[1] > 9) {
        return fail("createGame requires each cell to be inside 0 through 9, and received row " + cell[0] + ", column " + cell[1] + ".");
      }
      const id = key(cell[0], cell[1]);
      if (occupied.has(id)) {
        return fail("createGame requires ships to share no cell, and received a repeated cell at row " + cell[0] + ", column " + cell[1] + ".");
      }
      occupied.add(id);
      cells.push([cell[0], cell[1]]);
    }
    ships.push({ name: ship.name, cells });
  }
  const game = crypto.randomUUID();
  games.set(game, { ships, fired: new Set(), results: new Map() });
  return {
    game,
    ships: ships.map((ship) => ({ name: ship.name, cells: ship.cells.map((cell) => [cell[0], cell[1]]) })),
  };
}

function shipAt(ships, row, col) {
  for (const ship of ships) {
    for (const cell of ship.cells) {
      if (cell[0] === row && cell[1] === col) return ship;
    }
  }
  return null;
}

function fleetSunk(state) {
  for (const ship of state.ships) {
    for (const cell of ship.cells) {
      if (!state.fired.has(key(cell[0], cell[1]))) return false;
    }
  }
  return true;
}

// Contract: fire
/**
 * Resolve one shot.
 * @param {string} game id from createGame
 * @param {number} row integer 0 through 9
 * @param {number} col integer 0 through 9
 * @returns {{result: "hit"|"miss"|"sunk", gameOver: boolean} | {error: string}}
 * A repeat returns the first result and the current gameOver, and does not mark the cell again.
 * An error does not throw and does not mark a cell.
 */
function fire(game, row, col) {
  if (arguments.length < 1 || typeof game !== "string") {
    return fail("fire requires game to be a string, and received " + (arguments.length < 1 ? "nothing" : typeof game) + ".");
  }
  if (arguments.length < 2 || !Number.isInteger(row)) {
    return fail("fire requires row to be an integer, and received " + (arguments.length < 2 ? "nothing" : String(row)) + ".");
  }
  if (arguments.length < 3 || !Number.isInteger(col)) {
    return fail("fire requires col to be an integer, and received " + (arguments.length < 3 ? "nothing" : String(col)) + ".");
  }
  if (row < 0 || row > 9) return fail("fire requires row to be an integer from 0 through 9, and received " + row + ".");
  if (col < 0 || col > 9) return fail("fire requires col to be an integer from 0 through 9, and received " + col + ".");
  const state = games.get(game);
  if (!state) return fail("fire requires a stored game, and received " + game + ".");
  const id = key(row, col);
  const prior = state.results.get(id);
  if (prior) return { result: prior, gameOver: fleetSunk(state) };
  const ship = shipAt(state.ships, row, col);
  state.fired.add(id);
  let result = "miss";
  if (ship) {
    const remaining = ship.cells.some((cell) => !state.fired.has(key(cell[0], cell[1])));
    result = remaining ? "hit" : "sunk";
  }
  state.results.set(id, result);
  return { result, gameOver: fleetSunk(state) };
}

/**
 * Occupied cells in placement order. In-process only.
 * @param {string} game id from createGame
 * @returns {number[][] | {error: string}}
 */
function occupiedCells(game) {
  const state = typeof game === "string" ? games.get(game) : undefined;
  if (!state) return fail("game is not a stored game");
  return state.ships.flatMap((ship) => ship.cells.map((cell) => [cell[0], cell[1]]));
}

module.exports = { createGame, fire, occupiedCells };
