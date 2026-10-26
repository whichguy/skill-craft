/**
 * AuraEnabled chess API for one screen. Rules stay in SLChessEngine.
 * No queries and no DML. The caller keeps the FEN.
 */
public class SLChessController {
    /**
     * @param fen Six-field FEN. A blank value is rejected here.
     * @return Legal UCI moves for the side to move, the same list as SLChessEngine.legalMoves.
     * @throws AuraHandledException when fen is blank or the engine rejects the position.
     * Side effect: none.
     */
    @AuraEnabled
    public static List<String> legalMoves(String fen) {
        requireFen(fen);
        try {
            return SLChessEngine.legalMoves(fen);
        } catch (SLChessEngine.IllegalMoveException ex) {
            throw aura(ex.getMessage());
        }
    }

    /**
     * @param fen Six-field FEN. A blank value is rejected here.
     * @param move Legal UCI move in fen, such as e2e4 or e7e8q.
     * @return The FEN SLChessEngine.applyMove returns for that move.
     * @throws AuraHandledException when fen is blank, or the engine rejects fen or move.
     * Side effect: none. No FEN is stored.
     */
    @AuraEnabled
    public static String applyMove(String fen, String move) {
        requireFen(fen);
        try {
            return SLChessEngine.applyMove(fen, move);
        } catch (SLChessEngine.IllegalMoveException ex) {
            throw aura(ex.getMessage());
        }
    }

    /**
     * @param fen Six-field FEN. A blank value is rejected here.
     * @return ongoing, check, checkmate, or stalemate, the same word as SLChessEngine.status.
     * @throws AuraHandledException when fen is blank or the engine rejects the position.
     * Side effect: none.
     */
    @AuraEnabled
    public static String status(String fen) {
        requireFen(fen);
        try {
            return SLChessEngine.status(fen);
        } catch (SLChessEngine.IllegalMoveException ex) {
            throw aura(ex.getMessage());
        }
    }

    private static void requireFen(String fen) {
        if (fen == null || fen.trim().length() == 0) {
            throw aura('fen is required and was blank');
        }
    }

    // AuraHandledException.getMessage stays "Script-thrown exception" unless setMessage is called.
    private static AuraHandledException aura(String message) {
        AuraHandledException ex = new AuraHandledException(message);
        ex.setMessage(message);
        return ex;
    }
}
