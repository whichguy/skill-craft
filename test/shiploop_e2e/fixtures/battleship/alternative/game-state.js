const positions = new Map([
  ['9,10', 'Pioneer'],
  ['10,9', 'Pioneer'],
  ['10,10', 'Cutter'],
]);

function start() {
  return { targets: positions, fired: new Set(), sunk: new Set(), shots: 0, hits: 0 };
}

function shoot(state, row, col) {
  const point = `${row},${col}`;
  state.fired.add(point);
  state.shots += 1;
  const ship = state.targets.get(point);
  let result = 'miss';
  if (ship) {
    state.hits += 1;
    const total = [...state.targets.values()].filter((name) => name === ship).length;
    const hitCount = [...state.fired].filter((target) => state.targets.get(target) === ship).length;
    result = hitCount === total ? 'sunk' : 'hit';
    if (result === 'sunk') state.sunk.add(ship);
  }
  const allShips = new Set(state.targets.values());
  return {
    result,
    gameOver: [...allShips].every((name) => state.sunk.has(name)),
    shots: state.shots,
    hits: state.hits,
    ...(result === 'sunk' ? { ship } : {}),
  };
}

module.exports = { start, shoot };
