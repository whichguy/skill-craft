/**
 * The calls the slBattleBoard component makes. Each delegates to SLBattleEngine; an invalid shot reaches the browser as an
 * AuraHandledException carrying the engine's message.
 */
public with sharing class SLBattleController {
    @AuraEnabled
    public static String newGame(Integer seed) {
        return SLBattleEngine.newGame(seed);
    }

    @AuraEnabled
    public static String fire(String game, Integer row, Integer col) {
        try {
            return SLBattleEngine.fire(game, row, col);
        } catch (SLBattleEngine.InvalidShotException e) {
            // An AuraHandledException shows its own message only when setMessage has been called on it.
            AuraHandledException wrapped = new AuraHandledException(e.getMessage());
            wrapped.setMessage(e.getMessage());
            throw wrapped;
        }
    }
}
