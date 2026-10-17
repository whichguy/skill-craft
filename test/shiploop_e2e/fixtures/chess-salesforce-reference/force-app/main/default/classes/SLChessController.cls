/**
 * The calls the slChessBoard component makes. Each delegates to SLChessEngine; a position the engine rejects (an illegal move,
 * an invalid FEN) reaches the browser as an AuraHandledException carrying the engine's message.
 */
public with sharing class SLChessController {
    @AuraEnabled
    public static List<String> legalMoves(String fen) {
        try {
            return SLChessEngine.legalMoves(fen);
        } catch (SLChessEngine.IllegalMoveException e) {
            throw handled(e);
        }
    }

    @AuraEnabled
    public static String applyMove(String fen, String move) {
        try {
            return SLChessEngine.applyMove(fen, move);
        } catch (SLChessEngine.IllegalMoveException e) {
            throw handled(e);
        }
    }

    @AuraEnabled
    public static String status(String fen) {
        try {
            return SLChessEngine.status(fen);
        } catch (SLChessEngine.IllegalMoveException e) {
            throw handled(e);
        }
    }

    // An AuraHandledException shows its own message only when setMessage has been called on it.
    private static AuraHandledException handled(Exception e) {
        AuraHandledException wrapped = new AuraHandledException(e.getMessage());
        wrapped.setMessage(e.getMessage());
        return wrapped;
    }
}
