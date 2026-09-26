public with sharing class ChessGameController {
    @AuraEnabled
    public static ServiceResult save(Id gameId, String fen) {
        try { return ServiceResult.success(ChessGameService.save(gameId, fen)); }
        catch (Exception ex) { Logger.error('ChessGameController.save', ex); return ServiceResult.failure('SAVE_FAILED', ex.getMessage()); }
    }
}
