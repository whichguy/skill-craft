@IsTest
private class SLBattleGameTest {
    @IsTest
    static void aWholeGameThroughTheControllerSinksTheStandardFleet() {
        String game = SLBattleController.newGame(20261017);
        Integer hits = 0;
        List<Integer> sunkSizes = new List<Integer>();
        Integer overAt = null;
        for (Integer cell = 0; cell < 100; cell++) {
            game = SLBattleController.fire(game, cell / 10, Math.mod(cell, 10));
            Map<String, Object> state = (Map<String, Object>) JSON.deserializeUntyped(game);
            Map<String, Object> shot = (Map<String, Object>) state.get('lastShot');
            String outcome = (String) shot.get('result');
            if (outcome != 'miss') {
                hits++;
            }
            if (outcome == 'sunk') {
                sunkSizes.add((Integer) shot.get('size'));
                if (sunkSizes.size() == 5) {
                    overAt = cell;
                }
            }
            System.assertEquals(overAt != null, state.get('gameOver'));
            System.assertEquals(cell + 1, state.get('shots'));
        }
        sunkSizes.sort();
        System.assertEquals(17, hits);
        System.assertEquals(new List<Integer>{2, 3, 3, 4, 5}, sunkSizes);
    }

    @IsTest
    static void theControllerReportsAnInvalidShotAsAnAuraHandledException() {
        String game = SLBattleController.fire(SLBattleController.newGame(7), 0, 0);
        String message = null;
        try {
            SLBattleController.fire(game, 0, 0);
        } catch (AuraHandledException e) {
            message = e.getMessage();
        }
        System.assertEquals('The cell (0, 0) was already fired at.', message);
    }
}
