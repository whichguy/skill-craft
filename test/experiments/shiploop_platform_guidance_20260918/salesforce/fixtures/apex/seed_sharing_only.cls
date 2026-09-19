// Baseline: explicit record sharing but no visible SOQL/DML access-mode choice.
// API 67+ can still default this code to user mode; this fixture is rejected only
// by the experiment's explicit-intent scanner, not proven insecure by it.
public with sharing class ExpenseControllerSeed {
    @AuraEnabled
    public static List<Account> listAccounts() {
        return [SELECT Id, Name FROM Account];
    }

    @AuraEnabled
    public static void rename(List<Account> accounts) {
        update accounts;
    }
}
