// Reference: make the intended user-mode behavior visible at both a read and a write.
public with sharing class ExpenseControllerReference {
    @AuraEnabled
    public static List<Account> listAccounts() {
        return [SELECT Id, Name FROM Account WITH USER_MODE];
    }

    @AuraEnabled
    public static void rename(List<Account> accounts) {
        Database.update(accounts, AccessLevel.USER_MODE);
    }
}
