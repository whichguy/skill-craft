trigger ChessGameTrigger on Chess_Game__c (before insert, before update, after update) { new ChessGameTriggerHandler().run(); }
