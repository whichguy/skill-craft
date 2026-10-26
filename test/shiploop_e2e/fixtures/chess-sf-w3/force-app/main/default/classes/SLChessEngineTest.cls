@IsTest
private class SLChessEngineTest {
    @IsTest
    static void TC_1() {
        String start = SLChessEngine.startFen();
        System.assertEquals(
            'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
            start
        );
        List<String> moves = SLChessEngine.legalMoves(start);
        List<String> expected = new List<String>{
            'a2a3', 'a2a4', 'b1a3', 'b1c3', 'b2b3', 'b2b4', 'c2c3', 'c2c4',
            'd2d3', 'd2d4', 'e2e3', 'e2e4', 'f2f3', 'f2f4', 'g1f3', 'g1h3',
            'g2g3', 'g2g4', 'h2h3', 'h2h4'
        };
        System.assertEquals(20, moves.size());
        System.assertEquals(expected, moves);
        System.assertEquals('a2a3', moves[0]);
        System.assertEquals('h2h4', moves[moves.size() - 1]);
        System.assertEquals('ongoing', SLChessEngine.status(start));
    }

    @IsTest
    static void TC_2() {
        String start = SLChessEngine.startFen();
        String held = start;
        Boolean threw = false;
        try {
            SLChessEngine.applyMove(start, 'e2e5');
        } catch (SLChessEngine.IllegalMoveException ex) {
            threw = true;
        }
        System.assert(threw, 'e2e5 must throw IllegalMoveException');
        System.assertEquals(held, start);
    }

    @IsTest
    static void TC_3() {
        String fen = '7k/5Q2/6K1/8/8/8/8/8 b - - 0 1';
        System.assertEquals('stalemate', SLChessEngine.status(fen));
        System.assertEquals(0, SLChessEngine.legalMoves(fen).size());
    }

    @IsTest
    static void TC_4() {
        String fen = '4k3/8/8/8/8/8/4q3/4K3 w - - 0 1';
        System.assertEquals('check', SLChessEngine.status(fen));
        System.assert(SLChessEngine.legalMoves(fen).contains('e1e2'));
    }

    @IsTest
    static void TC_5() {
        String fen = play(SLChessEngine.startFen(), new List<String>{ 'f2f3', 'e7e6', 'g2g4', 'd8h4' });
        System.assertEquals(
            'rnb1kbnr/pppp1ppp/4p3/8/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3',
            fen
        );
        System.assertEquals('checkmate', SLChessEngine.status(fen));
        System.assertEquals(0, SLChessEngine.legalMoves(fen).size());
    }

    @IsTest
    static void TC_6() {
        String fen = play(
            SLChessEngine.startFen(),
            new List<String>{ 'e2e4', 'e7e5', 'f1c4', 'b8c6', 'd1h5', 'g8f6', 'h5f7' }
        );
        System.assertEquals(
            'r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4',
            fen
        );
        System.assertEquals('checkmate', SLChessEngine.status(fen));
    }

    @IsTest
    static void TC_7() {
        String fen = play(SLChessEngine.startFen(), new List<String>{ 'f2f3', 'e7e6', 'g2g4' });
        System.assertEquals('ongoing', SLChessEngine.status(fen));
        System.assert(SLChessEngine.legalMoves(fen).contains('d8h4'));
    }

    @IsTest
    static void TC_8() {
        String white = 'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1';
        System.assertEquals(
            'r3k2r/8/8/8/8/8/8/R4RK1 b kq - 1 1',
            SLChessEngine.applyMove(white, 'e1g1')
        );
        System.assertEquals(
            'r3k2r/8/8/8/8/8/8/2KR3R b kq - 1 1',
            SLChessEngine.applyMove(white, 'e1c1')
        );
        String black = 'r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1';
        System.assertEquals(
            'r4rk1/8/8/8/8/8/8/R3K2R w KQ - 1 2',
            SLChessEngine.applyMove(black, 'e8g8')
        );
        System.assertEquals(
            '2kr3r/8/8/8/8/8/8/R3K2R w KQ - 1 2',
            SLChessEngine.applyMove(black, 'e8c8')
        );
    }

    @IsTest
    static void TC_9() {
        System.assert(
            !SLChessEngine.legalMoves('4r1k1/8/8/8/8/8/8/R3K2R w KQ - 0 1').contains('e1g1')
        );
        System.assert(
            !SLChessEngine.legalMoves('5rk1/8/8/8/8/8/8/R3K2R w KQ - 0 1').contains('e1g1')
        );
        System.assert(
            !SLChessEngine.legalMoves('6r1/8/8/8/8/8/8/R3K2R w KQ - 0 1').contains('e1g1')
        );
        System.assert(
            !SLChessEngine.legalMoves('r3k2r/8/8/8/8/8/8/R3K2R w Qkq - 0 1').contains('e1g1')
        );
        System.assert(
            !SLChessEngine.legalMoves('r3k2r/8/8/8/8/8/8/R3K2R w Kkq - 0 1').contains('e1c1')
        );
    }

    @IsTest
    static void TC_10() {
        String start = SLChessEngine.startFen();
        String e4 = SLChessEngine.applyMove(start, 'e2e4');
        System.assertEquals(
            'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
            e4
        );
        System.assertEquals(
            'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2',
            SLChessEngine.applyMove(e4, 'e7e5')
        );
        System.assertEquals(
            'rnbqkb1r/pppppppp/5n2/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 2',
            SLChessEngine.applyMove(e4, 'g8f6')
        );
        String ep = SLChessEngine.applyMove('4k3/8/8/8/3p4/8/4P3/4K3 w - - 0 1', 'e2e4');
        System.assertEquals('4k3/8/8/8/3pP3/8/8/4K3 b - e3 0 1', ep);
        System.assertEquals(
            '4k3/8/8/8/8/4p3/8/4K3 w - - 0 2',
            SLChessEngine.applyMove(ep, 'd4e3')
        );
    }

    @IsTest
    static void TC_11() {
        String fen = 'k7/4P3/8/8/8/8/8/4K3 w - - 0 1';
        List<String> moves = SLChessEngine.legalMoves(fen);
        System.assert(moves.contains('e7e8q'));
        System.assert(moves.contains('e7e8r'));
        System.assert(moves.contains('e7e8b'));
        System.assert(moves.contains('e7e8n'));
        System.assert(!moves.contains('e7e8'));
        System.assertEquals(
            'k3Q3/8/8/8/8/8/8/4K3 b - - 0 1',
            SLChessEngine.applyMove(fen, 'e7e8q')
        );
        System.assertEquals(
            'k3R3/8/8/8/8/8/8/4K3 b - - 0 1',
            SLChessEngine.applyMove(fen, 'e7e8r')
        );
        System.assertEquals(
            'k3B3/8/8/8/8/8/8/4K3 b - - 0 1',
            SLChessEngine.applyMove(fen, 'e7e8b')
        );
        System.assertEquals(
            'k3N3/8/8/8/8/8/8/4K3 b - - 0 1',
            SLChessEngine.applyMove(fen, 'e7e8n')
        );
    }

    @IsTest
    static void TC_12() {
        List<String> kiwi = SLChessEngine.legalMoves(
            'r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1'
        );
        System.assertEquals(48, kiwi.size());
        System.assert(kiwi.contains('e1g1'));
        System.assert(kiwi.contains('e1c1'));
        System.assertEquals(
            14,
            SLChessEngine.legalMoves('8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1').size()
        );
        System.assertEquals(
            6,
            SLChessEngine.legalMoves(
                'r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1'
            ).size()
        );
    }

    @IsTest
    static void TC_13() {
        System.assert(
            !SLChessEngine.legalMoves('8/8/8/8/8/4k3/8/4K3 w - - 0 1').contains('e1e2')
        );
        for (String move : SLChessEngine.legalMoves('4k3/4b3/8/8/8/8/8/4R2K b - - 0 1')) {
            System.assert(!move.startsWith('e7'), move);
        }
    }

    @IsTest
    static void TC_14() {
        String castle = 'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1';
        System.assertEquals(
            'r3k2r/8/8/8/8/8/8/R3K1R1 b Qkq - 1 1',
            SLChessEngine.applyMove(castle, 'h1g1')
        );
        System.assertEquals(
            'r3k2r/8/8/8/8/8/4K3/R6R b kq - 1 1',
            SLChessEngine.applyMove(castle, 'e1e2')
        );
        System.assertEquals(
            'Q3k2r/8/8/8/8/8/8/R3K2R b KQk - 0 1',
            SLChessEngine.applyMove('r3k2r/Q7/8/8/8/8/8/R3K2R w KQkq - 0 1', 'a7a8')
        );
    }

    private static String play(String fen, List<String> moves) {
        for (String move : moves) {
            System.assert(SLChessEngine.legalMoves(fen).contains(move), move);
            fen = SLChessEngine.applyMove(fen, move);
        }
        return fen;
    }
}
