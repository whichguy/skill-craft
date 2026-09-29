const fleet = [
  { name: 'Harbor', cells: ['0,0', '0,1'] },
  { name: 'Buoy', cells: ['1,0'] },
];

function createGame(id) {
  return {
    id,
    ships: fleet.map((ship) => ({ name: ship.name, cells: new Set(ship.cells), hits: new Set() })),
    shots: 0,
    hits: 0,
  };
}

function fire(game, row, col) {
  game.shots += 1;
  const coordinate = `${row},${col}`;
  const ship = game.ships.find((item) => item.cells.has(coordinate));
  let result = 'miss';
  let sunkShip;
  if (ship) {
    ship.hits.add(coordinate);
    game.hits += 1;
    result = ship.hits.size === ship.cells.size ? 'sunk' : 'hit';
    if (result === 'sunk') sunkShip = ship.name;
  }
  const gameOver = game.ships.every((item) => item.hits.size === item.cells.size);
  return {
    result,
    gameOver,
    shots: game.shots,
    hits: game.hits,
    ...(sunkShip ? { ship: sunkShip } : {}),
  };
}

module.exports = { createGame, fire };
