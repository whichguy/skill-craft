/**
 * The rules of SLChessEngine. Expected counts are the published perft numbers of the standard test positions
 * (chessprogramming.org "Perft Results"); expected FENs were derived with an independent move generator.
 */
@IsTest
private class SLChessEngineTest {
    private static final String START = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
    private static final String KIWIPETE = 'r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1';
    private static final String POSITION_3 = '8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1';
    private static final String POSITION_4 = 'r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1';
    private static final String POSITION_5 = 'rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8';
    private static final String CASTLING = 'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1';

    // The number of legal replies to every legal move of fen: perft depth 2.
    private static Integer perft2(String fen) {
        Integer total = 0;
        for (String move : SLChessEngine.legalMoves(fen)) {
            total += SLChessEngine.legalMoves(SLChessEngine.applyMove(fen, move)).size();
        }
        return total;
    }

    private static String play(String fen, String moves) {
        String current = fen;
        for (String move : moves.split(' ')) {
            current = SLChessEngine.applyMove(current, move);
        }
        return current;
    }

    private static Boolean has(String fen, String move) {
        return SLChessEngine.legalMoves(fen).indexOf(move) >= 0;
    }

    private static Boolean refused(String fen, String move) {
        try {
            SLChessEngine.applyMove(fen, move);
        } catch (SLChessEngine.IllegalMoveException e) {
            return true;
        }
        return false;
    }

    @IsTest
    static void startPosition() {
        System.assertEquals(START, SLChessEngine.startFen());
        System.assertEquals('a2a3,a2a4,b1a3,b1c3,b2b3,b2b4,c2c3,c2c4,d2d3,d2d4,e2e3,e2e4,f2f3,f2f4,g1f3,g1h3,g2g3,g2g4,h2h3,h2h4',
            String.join(SLChessEngine.legalMoves(START), ','));
        System.assertEquals('ongoing', SLChessEngine.status(START));
        System.assertEquals('rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1', SLChessEngine.applyMove(START, 'e2e4'));
    }

    @IsTest
    static void perftStartPosition() {
        System.assertEquals(20, SLChessEngine.legalMoves(START).size());
        System.assertEquals(400, perft2(START));
    }

    @IsTest
    static void perftKiwipete() {
        System.assertEquals(48, SLChessEngine.legalMoves(KIWIPETE).size());
        System.assertEquals(2039, perft2(KIWIPETE));
        System.debug('CPU ' + Limits.getCpuTime());
    }

    @IsTest
    static void perftPosition3() {
        System.assertEquals(14, SLChessEngine.legalMoves(POSITION_3).size());
        System.assertEquals(191, perft2(POSITION_3));
    }

    @IsTest
    static void perftPosition4() {
        System.assertEquals(6, SLChessEngine.legalMoves(POSITION_4).size());
        System.assertEquals(264, perft2(POSITION_4));
    }

    @IsTest
    static void perftPosition5() {
        System.assertEquals(44, SLChessEngine.legalMoves(POSITION_5).size());
        System.assertEquals(1486, perft2(POSITION_5));
        System.debug('CPU ' + Limits.getCpuTime());
    }

    @IsTest
    static void perftCastlingPosition() {
        System.assertEquals(26, SLChessEngine.legalMoves(CASTLING).size());
    }

    @IsTest
    static void foolsMate() {
        String fen = play(START, 'f2f3 e7e5 g2g4');
        System.assertEquals('ongoing', SLChessEngine.status(fen));
        fen = SLChessEngine.applyMove(fen, 'd8h4');
        System.assertEquals('rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3', fen);
        System.assertEquals('checkmate', SLChessEngine.status(fen));
        System.assertEquals(0, SLChessEngine.legalMoves(fen).size());
    }

    @IsTest
    static void scholarsMate() {
        String fen = play(START, 'e2e4 e7e5 d1h5 b8c6 f1c4 g8f6');
        System.assertEquals('ongoing', SLChessEngine.status(fen));
        fen = SLChessEngine.applyMove(fen, 'h5f7');
        System.assertEquals('r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4', fen);
        System.assertEquals('checkmate', SLChessEngine.status(fen));
        System.assertEquals(0, SLChessEngine.legalMoves(fen).size());
    }

    @IsTest
    static void castlingOnBothSides() {
        System.assertEquals(true, has(CASTLING, 'e1g1'));
        System.assertEquals(true, has(CASTLING, 'e1c1'));
        System.assertEquals('r3k2r/8/8/8/8/8/8/R4RK1 b kq - 1 1', SLChessEngine.applyMove(CASTLING, 'e1g1'));
        System.assertEquals('r3k2r/8/8/8/8/8/8/2KR3R b kq - 1 1', SLChessEngine.applyMove(CASTLING, 'e1c1'));
        System.assertEquals('r4rk1/8/8/8/8/8/4K3/R6R w - - 2 2', play(CASTLING, 'e1e2 e8g8'));
        System.assertEquals('2kr3r/8/8/8/8/8/8/R4RK1 w - - 2 2', play(CASTLING, 'e1g1 e8c8'));
    }

    @IsTest
    static void castlingIsRefusedOutOfThroughAndIntoCheck() {
        // A rook on the e-file checks the king: no castling at all.
        String inCheck = '4r1k1/8/8/8/8/8/8/R3K2R w KQ - 0 1';
        System.assertEquals('check', SLChessEngine.status(inCheck));
        System.assertEquals(false, has(inCheck, 'e1g1'));
        System.assertEquals(false, has(inCheck, 'e1c1'));
        // A rook on the f-file attacks f1, which the king would cross.
        String through = 'r4rk1/8/8/8/8/8/8/R3K2R w KQ - 0 1';
        System.assertEquals(false, has(through, 'e1g1'));
        System.assertEquals(true, has(through, 'e1c1'));
        System.assertEquals(true, refused(through, 'e1g1'));
        // A rook on the g-file attacks g1, where the king would land.
        String landing = '6rk/8/8/8/8/8/8/R3K2R w KQ - 0 1';
        System.assertEquals(false, has(landing, 'e1g1'));
        System.assertEquals(true, has(landing, 'e1c1'));
        // Only the rook crosses b1, so an attack on b1 does not stop the long castle.
        String rookCrosses = '1r4k1/8/8/8/8/8/8/R3K2R w KQ - 0 1';
        System.assertEquals(true, has(rookCrosses, 'e1c1'));
        System.assertEquals(true, has(rookCrosses, 'e1g1'));
        // Pieces between king and rook.
        String blocked = 'r3k2r/8/8/8/8/8/8/RN2K1NR w KQkq - 0 1';
        System.assertEquals(false, has(blocked, 'e1g1'));
        System.assertEquals(false, has(blocked, 'e1c1'));
    }

    @IsTest
    static void castlingRightsAreLostCorrectly() {
        // The a1 rook leaves and returns: only the long right is gone.
        String afterRook = play(CASTLING, 'a1b1 e8e7 b1a1 e7e8');
        System.assertEquals('r3k2r/8/8/8/8/8/8/R3K2R w K - 4 3', afterRook);
        System.assertEquals(true, has(afterRook, 'e1g1'));
        System.assertEquals(false, has(afterRook, 'e1c1'));
        // The king leaves and returns: both rights are gone, for each side.
        String afterKing = play(CASTLING, 'e1e2 e8e7 e2e1 e7e8');
        System.assertEquals('r3k2r/8/8/8/8/8/8/R3K2R w - - 4 3', afterKing);
        System.assertEquals(false, has(afterKing, 'e1g1'));
        System.assertEquals(false, has(afterKing, 'e1c1'));
        // A captured rook takes its right with it: the bishop takes the rook on h1.
        String afterCapture = SLChessEngine.applyMove('r3k2r/8/8/8/8/8/6b1/R3K2R b KQkq - 0 1', 'g2h1');
        System.assertEquals('r3k2r/8/8/8/8/8/8/R3K2b w Qkq - 0 2', afterCapture);
        System.assertEquals(false, has(afterCapture, 'e1g1'));
        System.assertEquals(true, has(afterCapture, 'e1c1'));
        // A rook takes a rook in each corner: the mover loses the right of the rook that left, the victim's side the right of the captured one.
        System.assertEquals('4k2r/8/8/8/8/8/8/r3K2R w Kk - 0 2', SLChessEngine.applyMove('r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1', 'a8a1'));
        System.assertEquals('R3k2r/8/8/8/8/8/8/4K2R b Kk - 0 1', SLChessEngine.applyMove(CASTLING, 'a1a8'));
        System.assertEquals('r3k2R/8/8/8/8/8/8/R3K3 b Qq - 0 1', SLChessEngine.applyMove(CASTLING, 'h1h8'));
        System.assertEquals('r3k3/8/8/8/8/8/8/R3K2r w Qq - 0 2', SLChessEngine.applyMove('r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1', 'h8h1'));
    }

    @IsTest
    static void enPassant() {
        // The target square is recorded after every two-square push, whether or not a pawn could capture.
        System.assertEquals('rnbqkbnr/pppppppp/8/8/P7/8/1PPPPPPP/RNBQKBNR b KQkq a3 0 1', SLChessEngine.applyMove(START, 'a2a4'));
        System.assertEquals('rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq - 1 1', SLChessEngine.applyMove(START, 'g1f3'));
        // White takes en passant on the move after the push, and not later.
        String ready = play(START, 'e2e4 a7a6 e4e5 d7d5');
        System.assertEquals('rnbqkbnr/1pp1pppp/p7/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3', ready);
        System.assertEquals(true, has(ready, 'e5d6'));
        System.assertEquals('rnbqkbnr/1pp1pppp/p2P4/8/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 3', SLChessEngine.applyMove(ready, 'e5d6'));
        System.assertEquals(false, has(play(ready, 'h2h3 a6a5'), 'e5d6'));
        // Black takes en passant too.
        String black = SLChessEngine.applyMove('4k3/8/8/8/3p4/8/2P5/4K3 w - - 0 1', 'c2c4');
        System.assertEquals('4k3/8/8/8/2Pp4/8/8/4K3 b - c3 0 1', black);
        System.assertEquals(true, has(black, 'd4c3'));
        System.assertEquals('4k3/8/8/8/8/2p5/8/4K3 w - - 0 2', SLChessEngine.applyMove(black, 'd4c3'));
    }

    @IsTest
    static void enPassantIsRefusedWhenItExposesTheKingAlongTheRank() {
        // Taking b5xc6 removes both pawns from the fifth rank and opens the rook on h5 to the king on a5.
        String pinned = '7k/8/8/KPp4r/8/8/8/8 w - c6 0 1';
        System.assertEquals(false, has(pinned, 'b5c6'));
        System.assertEquals(true, refused(pinned, 'b5c6'));
        System.assertEquals('a5a4,a5a6,a5b6,b5b6', String.join(SLChessEngine.legalMoves(pinned), ','));
        // The same capture without the rook is fine.
        String free = '7k/8/8/KPp5/8/8/8/8 w - c6 0 1';
        System.assertEquals(true, has(free, 'b5c6'));
        System.assertEquals('7k/8/2P5/K7/8/8/8/8 b - - 0 1', SLChessEngine.applyMove(free, 'b5c6'));
    }

    @IsTest
    static void promotion() {
        String lone = '4k3/P7/8/8/8/8/8/4K3 w - - 0 1';
        System.assertEquals('a7a8b,a7a8n,a7a8q,a7a8r,e1d1,e1d2,e1e2,e1f1,e1f2', String.join(SLChessEngine.legalMoves(lone), ','));
        System.assertEquals('Q3k3/8/8/8/8/8/8/4K3 b - - 0 1', SLChessEngine.applyMove(lone, 'a7a8q'));
        System.assertEquals('R3k3/8/8/8/8/8/8/4K3 b - - 0 1', SLChessEngine.applyMove(lone, 'a7a8r'));
        System.assertEquals('B3k3/8/8/8/8/8/8/4K3 b - - 0 1', SLChessEngine.applyMove(lone, 'a7a8b'));
        System.assertEquals('N3k3/8/8/8/8/8/8/4K3 b - - 0 1', SLChessEngine.applyMove(lone, 'a7a8n'));
        // Promotion needs its piece letter, and only q, r, b and n are pieces.
        System.assertEquals(true, refused(lone, 'a7a8'));
        System.assertEquals(true, refused(lone, 'a7a8k'));
        System.assertEquals(true, refused(lone, 'a7a8p'));
        System.assertEquals(true, refused(lone, 'e1e2q'));
        // Promotion by capture, and by Black.
        String capture = '1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1';
        System.assertEquals(true, has(capture, 'a7b8n'));
        System.assertEquals('1Q2k3/8/8/8/8/8/8/4K3 b - - 0 1', SLChessEngine.applyMove(capture, 'a7b8q'));
        String black = '4k3/8/8/8/8/8/p7/4K3 b - - 0 1';
        System.assertEquals('4k3/8/8/8/8/8/8/q3K3 w - - 0 2', SLChessEngine.applyMove(black, 'a2a1q'));
        System.assertEquals('4k3/8/8/8/8/8/8/n3K3 w - - 0 2', SLChessEngine.applyMove(black, 'a2a1n'));
        // A promotion can give check.
        String giving = SLChessEngine.applyMove('7k/P7/8/8/8/8/8/4K3 w - - 0 1', 'a7a8q');
        System.assertEquals('Q6k/8/8/8/8/8/8/4K3 b - - 0 1', giving);
        System.assertEquals('check', SLChessEngine.status(giving));
    }

    @IsTest
    static void stalemateCheckAndCheckmate() {
        String stalemate = '7k/5Q2/6K1/8/8/8/8/8 b - - 0 1';
        System.assertEquals('stalemate', SLChessEngine.status(stalemate));
        System.assertEquals(0, SLChessEngine.legalMoves(stalemate).size());
        // A move that stalemates.
        System.assertEquals('7k/5Q2/6K1/8/8/8/8/8 b - - 1 1', SLChessEngine.applyMove('7k/8/6K1/5Q2/8/8/8/8 w - - 0 1', 'f5f7'));
        // A back-rank mate.
        String mate = SLChessEngine.applyMove('6k1/5ppp/8/8/8/8/8/R3K3 w - - 0 1', 'a1a8');
        System.assertEquals('R5k1/5ppp/8/8/8/8/8/4K3 b - - 1 1', mate);
        System.assertEquals('checkmate', SLChessEngine.status(mate));
        System.assertEquals(0, SLChessEngine.legalMoves(mate).size());
        // Check, with the king's four ways out.
        String check = '4k3/8/8/8/8/8/8/4RK2 b - - 0 1';
        System.assertEquals('check', SLChessEngine.status(check));
        System.assertEquals('e8d7,e8d8,e8f7,e8f8', String.join(SLChessEngine.legalMoves(check), ','));
        System.assertEquals('ongoing', SLChessEngine.status(START));
    }

    @IsTest
    static void illegalMovesThrow() {
        System.assertEquals(true, refused(START, 'e2e5'));
        System.assertEquals(true, refused(START, 'e7e5'));
        System.assertEquals(true, refused(START, 'e3e4'));
        System.assertEquals(true, refused(START, 'a1a3'));
        System.assertEquals(true, refused(START, 'e1e2'));
        System.assertEquals(true, refused(START, 'e2'));
        System.assertEquals(true, refused(START, 'e2e4e5'));
        System.assertEquals(true, refused(START, 'zzzz'));
        System.assertEquals(true, refused(START, 'E2E4'));
        System.assertEquals(true, refused(START, ''));
        System.assertEquals(true, refused(START, null));
        // The king may not step into an attacked square, and a pinned piece may not leave the line of the pin.
        String rookOnFirstRank = '4k3/8/8/8/8/8/8/r3K3 w - - 0 1';
        System.assertEquals(true, refused(rookOnFirstRank, 'e1d1'));
        System.assertEquals(true, refused(rookOnFirstRank, 'e1f1'));
        System.assertEquals(false, refused(rookOnFirstRank, 'e1e2'));
        String pinned = '4r1k1/8/8/8/8/8/4B3/4K3 w - - 0 1';
        System.assertEquals(true, refused(pinned, 'e2d3'));
        System.assertEquals('e1d1,e1d2,e1f1,e1f2', String.join(SLChessEngine.legalMoves(pinned), ','));
        // The message names the move.
        try {
            SLChessEngine.applyMove(START, 'e2e5');
            System.assert(false, 'e2e5 must throw');
        } catch (SLChessEngine.IllegalMoveException e) {
            System.assert(e.getMessage().contains('e2e5'), e.getMessage());
        }
    }

    @IsTest
    static void clocks() {
        String fen = play(START, 'g1f3 g8f6');
        System.assertEquals('rnbqkb1r/pppppppp/5n2/8/8/5N2/PPPPPPPP/RNBQKB1R w KQkq - 2 2', fen);
        System.assertEquals('rnbqkb1r/pppppppp/5n2/8/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq e3 0 2', SLChessEngine.applyMove(fen, 'e2e4'));
        System.assertEquals('rnbqkb1r/pppppNpp/8/8/4n3/8/PPPPPPPP/RNBQKB1R b KQkq - 0 3', play(fen, 'f3e5 f6e4 e5f7'));
        System.assertEquals('r1bqkbnr/1ppp1ppp/p1B5/4p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 0 4', play(START, 'e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5c6'));
    }

    @IsTest
    static void invalidFenThrows() {
        List<String> invalid = new List<String>{
            '', 'garbage', '8/8/8/8/8/8/8/8 w - - 0 1', 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP w KQkq - 0 1',
            'rnbqkbnr/pppppppp/9/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1', 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR x KQkq - 0 1'
        };
        for (String fen : invalid) {
            Boolean rejected = false;
            try {
                SLChessEngine.legalMoves(fen);
            } catch (SLChessEngine.IllegalMoveException e) {
                rejected = true;
            }
            System.assert(rejected, 'FEN should be rejected: ' + fen);
        }
    }
}
