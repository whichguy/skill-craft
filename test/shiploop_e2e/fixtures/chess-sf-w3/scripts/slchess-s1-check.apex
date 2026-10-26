String start = SLChessEngine.startFen();
System.assertEquals('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1', start);
List<String> startMoves = SLChessEngine.legalMoves(start);
System.assertEquals(20, startMoves.size());
System.assertEquals('a2a3', startMoves[0]);
System.assertEquals('h2h4', startMoves[startMoves.size() - 1]);
List<String> sortedStart = startMoves.clone();
sortedStart.sort();
System.assertEquals(String.join(sortedStart, ','), String.join(startMoves, ','));
System.assertEquals('ongoing', SLChessEngine.status(start));
Boolean illegal = false;
try {
    SLChessEngine.applyMove(start, 'e2e5');
} catch (SLChessEngine.IllegalMoveException ex) {
    illegal = true;
}
System.assert(illegal, 'e2e5 must throw IllegalMoveException');
System.assertEquals('stalemate', SLChessEngine.status('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1'));
System.assertEquals(0, SLChessEngine.legalMoves('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1').size());
System.assertEquals('checkmate', SLChessEngine.status('rnb1kbnr/pppp1ppp/4p3/8/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3'));
System.assertEquals('check', SLChessEngine.status('4k3/8/8/8/8/8/4q3/4K3 w - - 0 1'));
System.assert(SLChessEngine.legalMoves('4k3/8/8/8/8/8/4q3/4K3 w - - 0 1').contains('e1e2'));

List<String> kiwi = SLChessEngine.legalMoves('r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1');
System.assertEquals(48, kiwi.size());
System.assert(kiwi.contains('e1g1'));
System.assert(kiwi.contains('e1c1'));
System.assertEquals(14, SLChessEngine.legalMoves('8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1').size());
System.assertEquals(6, SLChessEngine.legalMoves('r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1').size());
String pos6 = 'r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10';
Integer p6Start = Limits.getCpuTime();
List<String> p6Moves = SLChessEngine.legalMoves(pos6);
Integer p6Cpu = Limits.getCpuTime() - p6Start;
System.debug(LoggingLevel.ERROR, 'P6_CPU=' + p6Cpu);
System.assertEquals(46, p6Moves.size());
System.assert(p6Cpu < 10000, 'position 6 cpu ' + p6Cpu);

System.assert(!SLChessEngine.legalMoves('4r1k1/8/8/8/8/8/8/R3K2R w KQ - 0 1').contains('e1g1'));
System.assert(!SLChessEngine.legalMoves('5rk1/8/8/8/8/8/8/R3K2R w KQ - 0 1').contains('e1g1'));
System.assert(!SLChessEngine.legalMoves('6r1/8/8/8/8/8/8/R3K2R w KQ - 0 1').contains('e1g1'));
System.assert(!SLChessEngine.legalMoves('r3k2r/8/8/8/8/8/8/R3K2R w Qkq - 0 1').contains('e1g1'));
System.assert(!SLChessEngine.legalMoves('r3k2r/8/8/8/8/8/8/R3K2R w Kkq - 0 1').contains('e1c1'));
System.assert(!SLChessEngine.legalMoves('8/8/8/8/8/4k3/8/4K3 w - - 0 1').contains('e1e2'));
for (String pinMove : SLChessEngine.legalMoves('4k3/4b3/8/8/8/8/8/4R2K b - - 0 1')) {
    System.assert(!pinMove.startsWith('e7'), pinMove);
}
List<String> promo = SLChessEngine.legalMoves('k7/4P3/8/8/8/8/8/4K3 w - - 0 1');
System.assert(promo.contains('e7e8q'));
System.assert(promo.contains('e7e8r'));
System.assert(promo.contains('e7e8b'));
System.assert(promo.contains('e7e8n'));
System.assert(!promo.contains('e7e8'));

System.assertEquals('rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1', SLChessEngine.applyMove(start, 'e2e4'));
String e4 = SLChessEngine.applyMove(start, 'e2e4');
System.assertEquals('rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2', SLChessEngine.applyMove(e4, 'e7e5'));
System.assertEquals('rnbqkb1r/pppppppp/5n2/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 2', SLChessEngine.applyMove(e4, 'g8f6'));
String ep = SLChessEngine.applyMove('4k3/8/8/8/3p4/8/4P3/4K3 w - - 0 1', 'e2e4');
System.assertEquals('4k3/8/8/8/3pP3/8/8/4K3 b - e3 0 1', ep);
System.assertEquals('4k3/8/8/8/8/4p3/8/4K3 w - - 0 2', SLChessEngine.applyMove(ep, 'd4e3'));
String castle = 'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1';
System.assertEquals('r3k2r/8/8/8/8/8/8/R4RK1 b kq - 1 1', SLChessEngine.applyMove(castle, 'e1g1'));
System.assertEquals('r3k2r/8/8/8/8/8/8/2KR3R b kq - 1 1', SLChessEngine.applyMove(castle, 'e1c1'));
System.assertEquals('r3k2r/8/8/8/8/8/8/R3K1R1 b Qkq - 1 1', SLChessEngine.applyMove(castle, 'h1g1'));
System.assertEquals('r3k2r/8/8/8/8/8/4K3/R6R b kq - 1 1', SLChessEngine.applyMove(castle, 'e1e2'));
String blackCastle = 'r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1';
System.assertEquals('r4rk1/8/8/8/8/8/8/R3K2R w KQ - 1 2', SLChessEngine.applyMove(blackCastle, 'e8g8'));
System.assertEquals('2kr3r/8/8/8/8/8/8/R3K2R w KQ - 1 2', SLChessEngine.applyMove(blackCastle, 'e8c8'));
System.assertEquals('Q3k2r/8/8/8/8/8/8/R3K2R b KQk - 0 1', SLChessEngine.applyMove('r3k2r/Q7/8/8/8/8/8/R3K2R w KQkq - 0 1', 'a7a8'));
String promoFen = 'k7/4P3/8/8/8/8/8/4K3 w - - 0 1';
System.assertEquals('k3Q3/8/8/8/8/8/8/4K3 b - - 0 1', SLChessEngine.applyMove(promoFen, 'e7e8q'));
System.assertEquals('k3R3/8/8/8/8/8/8/4K3 b - - 0 1', SLChessEngine.applyMove(promoFen, 'e7e8r'));
System.assertEquals('k3B3/8/8/8/8/8/8/4K3 b - - 0 1', SLChessEngine.applyMove(promoFen, 'e7e8b'));
System.assertEquals('k3N3/8/8/8/8/8/8/4K3 b - - 0 1', SLChessEngine.applyMove(promoFen, 'e7e8n'));

String fen = start;
List<String> fools = new List<String>{'f2f3', 'e7e6', 'g2g4', 'd8h4'};
for (Integer i = 0; i < fools.size(); i++) {
    if (i == 3) {
        System.assertEquals('ongoing', SLChessEngine.status(fen));
        System.assert(SLChessEngine.legalMoves(fen).contains('d8h4'));
    }
    fen = SLChessEngine.applyMove(fen, fools[i]);
}
System.assertEquals('rnb1kbnr/pppp1ppp/4p3/8/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3', fen);
System.assertEquals('checkmate', SLChessEngine.status(fen));
System.assertEquals(0, SLChessEngine.legalMoves(fen).size());
fen = start;
for (String scholar : new List<String>{'e2e4', 'e7e5', 'f1c4', 'b8c6', 'd1h5', 'g8f6', 'h5f7'}) {
    fen = SLChessEngine.applyMove(fen, scholar);
}
System.assertEquals('r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4', fen);
System.assertEquals('checkmate', SLChessEngine.status(fen));

Integer d2Start = Limits.getCpuTime();
Integer nodes = 0;
for (String ply : SLChessEngine.legalMoves(start)) {
    nodes += SLChessEngine.legalMoves(SLChessEngine.applyMove(start, ply)).size();
}
Integer d2Cpu = Limits.getCpuTime() - d2Start;
System.debug(LoggingLevel.ERROR, 'D2_CPU=' + d2Cpu);
System.assertEquals(400, nodes);
System.assert(d2Cpu < 10000, 'depth 2 cpu ' + d2Cpu);
System.debug(LoggingLevel.ERROR, 'S1_OK');
