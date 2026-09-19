// Mutant: elevated behavior is visible but has no documented authorization reason.
public without sharing class ExpenseControllerMutant {
    @AuraEnabled
    public static List<Account> listAccounts() {
        return [SELECT Id, Name FROM Account WITH SYSTEM_MODE];
    }

    @AuraEnabled
    public static void rename(List<Account> accounts) {
        Database.update(accounts, AccessLevel.SYSTEM_MODE);
    }
}
