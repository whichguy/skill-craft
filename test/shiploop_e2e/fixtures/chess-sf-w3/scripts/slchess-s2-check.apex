String start = SLChessEngine.startFen();
System.assertEquals(SLChessEngine.legalMoves(start), SLChessController.legalMoves(start));
System.assertEquals('ongoing', SLChessController.status(start));

String fen = start;
List<String> fools = new List<String>{'f2f3', 'e7e6', 'g2g4', 'd8h4'};
for (Integer i = 0; i < fools.size(); i++) {
    System.assert(SLChessController.legalMoves(fen).contains(fools[i]), fools[i]);
    fen = SLChessController.applyMove(fen, fools[i]);
}
System.assertEquals('rnb1kbnr/pppp1ppp/4p3/8/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3', fen);
System.assertEquals('checkmate', SLChessController.status(fen));

fen = start;
for (String scholar : new List<String>{'e2e4', 'e7e5', 'f1c4', 'b8c6', 'd1h5', 'g8f6', 'h5f7'}) {
    System.assert(SLChessController.legalMoves(fen).contains(scholar), scholar);
    fen = SLChessController.applyMove(fen, scholar);
}
System.assertEquals('r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4', fen);
System.assertEquals('checkmate', SLChessController.status(fen));

List<String> opera = new List<String>{
    'e2e4', 'e7e5', 'g1f3', 'd7d6', 'd2d4', 'c8g4', 'd4e5', 'g4f3', 'd1f3', 'd6e5', 'f1c4',
    'g8f6', 'f3b3', 'd8e7', 'b1c3', 'c7c6', 'c1g5', 'b7b5', 'c3b5', 'c6b5', 'c4b5', 'b8d7',
    'e1c1', 'a8d8', 'd1d7', 'd8d7', 'h1d1', 'e7e6', 'b5d7', 'f6d7', 'b3b8', 'd7b8', 'd1d8'
};
System.assertEquals(33, opera.size());
Integer cpuStart = Limits.getCpuTime();
fen = start;
for (String ply : opera) {
    System.assert(SLChessController.legalMoves(fen).contains(ply), ply);
    fen = SLChessController.applyMove(fen, ply);
    SLChessController.status(fen);
}
Integer cpu = Limits.getCpuTime() - cpuStart;
System.debug(LoggingLevel.ERROR, 'OPERA_CPU=' + cpu);
System.assertEquals('checkmate', SLChessController.status(fen));
System.assert(cpu < 10000, 'opera cpu ' + cpu);
System.debug(LoggingLevel.ERROR, 'S2_OK');
