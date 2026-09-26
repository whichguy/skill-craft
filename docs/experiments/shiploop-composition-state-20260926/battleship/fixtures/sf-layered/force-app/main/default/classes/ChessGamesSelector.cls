public inherited sharing class ChessGamesSelector extends BaseSelector {
    public override Schema.SObjectType sObjectType() { return Chess_Game__c.SObjectType; }
    public override List<Schema.SObjectField> fields() { return new List<Schema.SObjectField>{ Chess_Game__c.Id, Chess_Game__c.Fen__c, Chess_Game__c.Status__c }; }
    public List<Chess_Game__c> byIds(Set<Id> ids) { return (List<Chess_Game__c>) query('Id IN :ids', new Map<String, Object>{ 'ids' => ids }); }
}
