/**
 * SLChessController: the three calls the slChessBoard component makes, and how an illegal move or a bad FEN reaches the browser.
 */
@IsTest
private class SLChessControllerTest {
    private static final String START = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

    @IsTest
    static void controllerAnswersLikeTheEngine() {
        System.assertEquals(String.join(SLChessEngine.legalMoves(START), ','), String.join(SLChessController.legalMoves(START), ','));
        System.assertEquals(20, SLChessController.legalMoves(START).size());
        System.assertEquals('rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1', SLChessController.applyMove(START, 'e2e4'));
        System.assertEquals('ongoing', SLChessController.status(START));
        System.assertEquals('check', SLChessController.status('4k3/8/8/8/8/8/8/4RK2 b - - 0 1'));
        System.assertEquals('checkmate', SLChessController.status('R5k1/5ppp/8/8/8/8/8/4K3 b - - 1 1'));
        System.assertEquals('stalemate', SLChessController.status('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1'));
    }

    @IsTest
    static void anIllegalMoveReachesTheCallerAsAnAuraHandledException() {
        Boolean thrown = false;
        try {
            SLChessController.applyMove(START, 'e2e5');
        } catch (AuraHandledException e) {
            thrown = true;
            System.assert(e.getMessage().contains('e2e5'), 'the engine message must reach the caller: ' + e.getMessage());
        }
        System.assert(thrown, 'e2e5 must be refused');
    }

    @IsTest
    static void aBadFenReachesTheCallerAsAnAuraHandledException() {
        Boolean thrown = false;
        try {
            SLChessController.legalMoves('not a fen');
        } catch (AuraHandledException e) {
            thrown = true;
            System.assert(e.getMessage().contains('Invalid FEN'), e.getMessage());
        }
        System.assert(thrown, 'a bad FEN must be refused');
    }
}
