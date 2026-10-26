@IsTest
private class SLChessBudgetTest {
    @IsTest
    static void TC_19() {
        String fen = 'r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10';
        Integer before = Limits.getCpuTime();
        List<String> moves = SLChessEngine.legalMoves(fen);
        Integer cpu = Limits.getCpuTime() - before;
        System.debug(LoggingLevel.ERROR, 'TC_19_CPU=' + cpu);
        System.assertEquals(46, moves.size());
        System.assert(cpu < 10000, 'TC_19_CPU=' + cpu);
    }

    @IsTest
    static void TC_20() {
        String start = SLChessEngine.startFen();
        Integer before = Limits.getCpuTime();
        Integer nodes = 0;
        for (String move : SLChessEngine.legalMoves(start)) {
            nodes += SLChessEngine.legalMoves(SLChessEngine.applyMove(start, move)).size();
        }
        Integer cpu = Limits.getCpuTime() - before;
        System.debug(LoggingLevel.ERROR, 'TC_20_CPU=' + cpu);
        System.assertEquals(400, nodes);
        System.assert(cpu < 10000, 'TC_20_CPU=' + cpu);
    }
}
