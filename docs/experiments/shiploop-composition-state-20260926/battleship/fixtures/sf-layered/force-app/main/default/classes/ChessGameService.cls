public with sharing class ChessGameService {
    public static Chess_Game__c save(Id gameId, String fen) {
        Chess_Game__c g = new ChessGamesSelector().byIds(new Set<Id>{ gameId })[0];
        g.Fen__c = fen; update as user g; return g;
    }
}
