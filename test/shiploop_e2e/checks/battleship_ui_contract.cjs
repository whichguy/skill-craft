'use strict';

const CELL_NAME_SOURCE = '^Battle cell row ([0-9]) column ([0-9]): (unfired|hit|miss|sunk)$';

function cellNamePattern(state) {
  const source = state ? `^Battle cell row ([0-9]) column ([0-9]): ${state}$` : CELL_NAME_SOURCE;
  return new RegExp(source, 'i');
}

function cellName(row, column, state) {
  return `Battle cell row ${row} column ${column}: ${state}`;
}

module.exports = { CELL_NAME_SOURCE, cellNamePattern, cellName };
