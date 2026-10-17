/**
 * Whole games played ply by ply, the way a person plays them in the board component: every move must be in the legal move list,
 * every position gets the right status, and a move that is not legal is refused in the middle of the game. Each game is played
 * through the engine and again through SLChessController, the API the component calls.
 */
@IsTest
private class SLChessGameTest {
    // Morphy against the Duke of Brunswick and Count Isouard, Paris 1858: captures, a queenside castle, three checks, a mate.
    private static final String OPERA_GAME = 'e2e4 e7e5 g1f3 d7d6 d2d4 c8g4 d4e5 g4f3 d1f3 d6e5 f1c4 g8f6 f3b3 d8e7 b1c3 c7c6 c1g5 b7b5 '
        + 'c3b5 c6b5 c4b5 b8d7 e1c1 a8d8 d1d7 d8d7 h1d1 e7e6 b5d7 f6d7 b3b8 d7b8 d1d8';
    // An en passant capture (ply 5), a pawn promoting with capture (ply 13) and the mate it gives.
    private static final String PROMOTION_GAME = 'e2e4 a7a6 e4e5 d7d5 e5d6 a6a5 d6e7 a5a4 d2d3 a4a3 c1g5 a3b2 e7d8q';
    // Sam Loyd's stalemate in ten moves: a queen sacrifice tour, then Black has no legal move and is not in check.
    private static final String STALEMATE_GAME = 'e2e3 a7a5 d1h5 a8a6 h5a5 h7h5 a5c7 a6h6 h2h4 f7f6 c7d7 e8f7 d7b7 d8d3 b7b8 d3h7 b8c8 f7g6 c8e6';

    private static List<String> legalOf(String fen, Boolean viaController) {
        return viaController ? SLChessController.legalMoves(fen) : SLChessEngine.legalMoves(fen);
    }

    private static String applyTo(String fen, String move, Boolean viaController) {
        return viaController ? SLChessController.applyMove(fen, move) : SLChessEngine.applyMove(fen, move);
    }

    private static String statusOf(String fen, Boolean viaController) {
        return viaController ? SLChessController.status(fen) : SLChessEngine.status(fen);
    }

    private static Boolean refusedByEngine(String fen, String move) {
        try {
            SLChessEngine.applyMove(fen, move);
        } catch (SLChessEngine.IllegalMoveException e) {
            return true;
        }
        return false;
    }

    private static Boolean refusedByController(String fen, String move) {
        try {
            SLChessController.applyMove(fen, move);
        } catch (AuraHandledException e) {
            return true;
        }
        return false;
    }

    // Plays uci (space separated) from the start position. checkPlies lists, as ',21,29,', the plies after which the side to move is
    // in check; the last ply must give finalStatus and every other ply ongoing. After probePly plies, probeMove must be refused: it is
    // a king move of the side that is not to move (e8e7 with White to move after an even number of plies, e1e2 after an odd one).
    private static void playGame(String uci, String checkPlies, String finalStatus, Integer probePly, String probeMove, Boolean viaController) {
        List<String> moves = uci.split(' ');
        String fen = SLChessEngine.startFen();
        for (Integer i = 0; i < moves.size(); i++) {
            Integer ply = i + 1;
            String move = moves.get(i);
            System.assert(legalOf(fen, viaController).indexOf(move) >= 0, 'ply ' + ply + ': ' + move + ' is not legal in ' + fen);
            if (i == probePly) {
                Boolean refused = viaController ? refusedByController(fen, probeMove) : refusedByEngine(fen, probeMove);
                System.assert(refused, 'ply ' + ply + ': ' + probeMove + ' should be refused in ' + fen);
            }
            fen = applyTo(fen, move, viaController);
            String expected = ply == moves.size() ? finalStatus : (checkPlies.indexOf(',' + ply + ',') >= 0 ? 'check' : 'ongoing');
            System.assertEquals(expected, statusOf(fen, viaController), 'status after ply ' + ply + ' (' + move + ')');
        }
        if (finalStatus == 'checkmate' || finalStatus == 'stalemate') {
            System.assertEquals(0, legalOf(fen, viaController).size(), 'no legal move after the last ply');
        }
    }

    @IsTest
    static void operaGameThroughTheEngine() {
        playGame(OPERA_GAME, ',21,29,31,', 'checkmate', 11, 'e1e2', false);
    }

    @IsTest
    static void operaGameThroughTheController() {
        playGame(OPERA_GAME, ',21,29,31,', 'checkmate', 11, 'e1e2', true);
    }

    @IsTest
    static void enPassantPromotionAndMate() {
        playGame(PROMOTION_GAME, ',', 'checkmate', 4, 'e8e7', false);
        playGame(PROMOTION_GAME, ',', 'checkmate', 4, 'e8e7', true);
        String finalFen = 'rnbQkbnr/1pp2ppp/8/6B1/8/3P4/PpP2PPP/RN1QKBNR b KQkq - 0 7';
        String fen = SLChessEngine.startFen();
        for (String move : PROMOTION_GAME.split(' ')) {
            fen = SLChessEngine.applyMove(fen, move);
        }
        System.assertEquals(finalFen, fen);
    }

    @IsTest
    static void stalemateGame() {
        playGame(STALEMATE_GAME, ',11,', 'stalemate', 6, 'e8e7', false);
        playGame(STALEMATE_GAME, ',11,', 'stalemate', 6, 'e8e7', true);
    }
}
