@IsTest
private class SLBattleEngineTest {
    private static Map<String, Object> parse(String game) {
        return (Map<String, Object>) JSON.deserializeUntyped(game);
    }

    private static Map<String, Object> lastShot(String game) {
        return (Map<String, Object>) parse(game).get('lastShot');
    }

    // The cells of every ship of a game, in fleet order (carrier first).
    private static List<List<Integer>> shipCells(String game) {
        List<List<Integer>> fleet = new List<List<Integer>>();
        for (Object item : (List<Object>) parse(game).get('ships')) {
            List<Integer> cells = new List<Integer>();
            for (Object cell : (List<Object>) ((Map<String, Object>) item).get('cells')) {
                cells.add((Integer) cell);
            }
            fleet.add(cells);
        }
        return fleet;
    }

    private static String fireAt(String game, Integer cell) {
        return SLBattleEngine.fire(game, cell / 10, Math.mod(cell, 10));
    }

    private static Integer waterCell(String game) {
        Set<Integer> ships = new Set<Integer>();
        for (List<Integer> cells : shipCells(game)) {
            ships.addAll(cells);
        }
        for (Integer cell = 0; cell < 100; cell++) {
            if (!ships.contains(cell)) {
                return cell;
            }
        }
        return null;
    }

    @IsTest
    static void aNewGameHasTheStandardFleetAndNoShotYet() {
        Map<String, Object> state = parse(SLBattleEngine.newGame(7));
        System.assertEquals(0, state.get('shots'));
        System.assertEquals(5, state.get('shipsLeft'));
        System.assertEquals(false, state.get('gameOver'));
        System.assertEquals(null, state.get('lastShot'));
        List<String> names = new List<String>();
        List<Integer> sizes = new List<Integer>();
        for (Object item : (List<Object>) state.get('ships')) {
            Map<String, Object> ship = (Map<String, Object>) item;
            names.add((String) ship.get('name'));
            sizes.add(((List<Object>) ship.get('cells')).size());
        }
        System.assertEquals(new List<String>{'carrier', 'battleship', 'cruiser', 'submarine', 'destroyer'}, names);
        System.assertEquals(new List<Integer>{5, 4, 3, 3, 2}, sizes);
    }

    @IsTest
    static void everyShipIsStraightInsideTheGridAndSharesNoCell() {
        for (Integer seed = 1; seed <= 25; seed++) {
            Set<Integer> seen = new Set<Integer>();
            for (List<Integer> cells : shipCells(SLBattleEngine.newGame(seed))) {
                Integer head = cells[0];
                Integer step = cells[1] - cells[0];
                System.assert(step == 1 || step == 10, 'a ship runs along a row or a column');
                for (Integer k = 0; k < cells.size(); k++) {
                    Integer cell = cells[k];
                    System.assertEquals(head + k * step, cell);
                    System.assert(cell >= 0 && cell < 100, 'inside the grid');
                    if (step == 1) {
                        System.assertEquals(head / 10, cell / 10, 'a ship along a row stays on it');
                    }
                    System.assert(seen.add(cell), 'no two ships share a cell');
                }
            }
        }
    }

    @IsTest
    static void theSameSeedGivesTheSameFleetAndAnotherSeedAnotherOne() {
        System.assertEquals(shipCells(SLBattleEngine.newGame(42)), shipCells(SLBattleEngine.newGame(42)));
        System.assertNotEquals(shipCells(SLBattleEngine.newGame(1)), shipCells(SLBattleEngine.newGame(2)));
    }

    @IsTest
    static void aShotAtWaterIsAMiss() {
        String game = SLBattleEngine.newGame(7);
        Integer cell = waterCell(game);
        game = fireAt(game, cell);
        Map<String, Object> shot = lastShot(game);
        System.assertEquals('miss', shot.get('result'));
        System.assertEquals(cell / 10, shot.get('row'));
        System.assertEquals(Math.mod(cell, 10), shot.get('col'));
        System.assertEquals(null, shot.get('ship'));
        System.assertEquals(null, shot.get('size'));
        System.assertEquals(1, parse(game).get('shots'));
        System.assertEquals(5, parse(game).get('shipsLeft'));
    }

    @IsTest
    static void aHitAndThenTheSinkingShotOfTheDestroyer() {
        String game = SLBattleEngine.newGame(7);
        List<Integer> destroyer = shipCells(game)[4];
        game = fireAt(game, destroyer[0]);
        System.assertEquals('hit', lastShot(game).get('result'));
        System.assertEquals(null, lastShot(game).get('ship'));
        System.assertEquals(5, parse(game).get('shipsLeft'));
        game = fireAt(game, destroyer[1]);
        System.assertEquals('sunk', lastShot(game).get('result'));
        System.assertEquals('destroyer', lastShot(game).get('ship'));
        System.assertEquals(2, lastShot(game).get('size'));
        System.assertEquals(4, parse(game).get('shipsLeft'));
        System.assertEquals(false, parse(game).get('gameOver'));
    }

    @IsTest
    static void theGameIsOverExactlyWhenTheLastShipSinks() {
        String game = SLBattleEngine.newGame(11);
        List<Integer> order = new List<Integer>();
        for (List<Integer> cells : shipCells(game)) {
            order.addAll(cells);
        }
        for (Integer k = 0; k < order.size(); k++) {
            game = fireAt(game, order[k]);
            System.assertEquals(k == order.size() - 1, parse(game).get('gameOver'));
        }
        System.assertEquals('sunk', lastShot(game).get('result'));
        System.assertEquals(0, parse(game).get('shipsLeft'));
        System.assertEquals(17, parse(game).get('shots'));
        game = fireAt(game, waterCell(game));
        System.assertEquals('miss', lastShot(game).get('result'));
        System.assertEquals(true, parse(game).get('gameOver'));
    }

    @IsTest
    static void aCellFiredAtTwiceIsRefused() {
        String game = SLBattleEngine.fire(SLBattleEngine.newGame(7), 3, 4);
        Boolean refused = false;
        try {
            SLBattleEngine.fire(game, 3, 4);
        } catch (SLBattleEngine.InvalidShotException e) {
            refused = true;
        }
        System.assert(refused, 'the second shot at (3, 4) is refused');
    }

    @IsTest
    static void aShotOutsideTheGridIsRefused() {
        String game = SLBattleEngine.newGame(7);
        List<List<Integer>> shots = new List<List<Integer>>{
            new List<Integer>{10, 0}, new List<Integer>{0, 10}, new List<Integer>{-1, 0}, new List<Integer>{0, -1},
            new List<Integer>{null, 0}
        };
        for (List<Integer> shot : shots) {
            Boolean refused = false;
            try {
                SLBattleEngine.fire(game, shot[0], shot[1]);
            } catch (SLBattleEngine.InvalidShotException e) {
                refused = true;
            }
            System.assert(refused, 'the shot ' + shot + ' is refused');
        }
    }
}
