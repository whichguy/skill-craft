/**
 * Org checks for SLChessController. Each game is one transaction.
 * blankFen covers a blank fen. TC_15 through TC_18 are the graded games.
 */
@IsTest
private class SLChessControllerTest {
    @IsTest
    static void blankFen() {
        assertBlankLegal('');
        assertBlankLegal(null);
        Boolean blankApply = false;
        try {
            SLChessController.applyMove('   ', 'e2e4');
        } catch (AuraHandledException ex) {
            blankApply = true;
        }
        System.assert(blankApply, 'blank fen applyMove');
        Boolean blankStatus = false;
        try {
            SLChessController.status('');
        } catch (AuraHandledException ex) {
            blankStatus = true;
        }
        System.assert(blankStatus, 'blank fen status');
    }

    @IsTest
    static void TC_15() {
        String fen = play(new List<String>{ 'f2f3', 'e7e6', 'g2g4', 'd8h4' });
        System.assertEquals(
            'rnb1kbnr/pppp1ppp/4p3/8/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3',
            fen
        );
        System.assertEquals('checkmate', SLChessController.status(fen));
    }

    @IsTest
    static void TC_16() {
        String fen = play(
            new List<String>{ 'e2e4', 'e7e5', 'f1c4', 'b8c6', 'd1h5', 'g8f6', 'h5f7' }
        );
        System.assertEquals(
            'r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4',
            fen
        );
        System.assertEquals('checkmate', SLChessController.status(fen));
    }

    @IsTest
    static void TC_17() {
        List<String> opera = new List<String>{
            'e2e4', 'e7e5', 'g1f3', 'd7d6', 'd2d4', 'c8g4', 'd4e5', 'g4f3', 'd1f3', 'd6e5', 'f1c4',
            'g8f6', 'f3b3', 'd8e7', 'b1c3', 'c7c6', 'c1g5', 'b7b5', 'c3b5', 'c6b5', 'c4b5', 'b8d7',
            'e1c1', 'a8d8', 'd1d7', 'd8d7', 'h1d1', 'e7e6', 'b5d7', 'f6d7', 'b3b8', 'd7b8', 'd1d8'
        };
        System.assertEquals(33, opera.size());
        Integer cpuStart = Limits.getCpuTime();
        String fen = play(opera);
        Integer cpu = Limits.getCpuTime() - cpuStart;
        System.debug(LoggingLevel.ERROR, 'TC_17_CPU=' + cpu);
        System.assertEquals('checkmate', SLChessController.status(fen));
        System.assert(cpu < 10000, 'opera cpu ' + cpu);
    }

    @IsTest
    static void TC_18() {
        String start = SLChessEngine.startFen();
        System.assertEquals(SLChessEngine.legalMoves(start), SLChessController.legalMoves(start));
        System.assertEquals('ongoing', SLChessController.status(start));
    }

    private static String play(List<String> moves) {
        String fen = SLChessEngine.startFen();
        for (String move : moves) {
            System.assert(SLChessController.legalMoves(fen).contains(move), move);
            fen = SLChessController.applyMove(fen, move);
            SLChessController.status(fen);
        }
        return fen;
    }

    private static void assertBlankLegal(String fen) {
        Boolean thrown = false;
        try {
            SLChessController.legalMoves(fen);
        } catch (AuraHandledException ex) {
            thrown = true;
        }
        System.assert(thrown, 'blank fen legalMoves');
    }
}
