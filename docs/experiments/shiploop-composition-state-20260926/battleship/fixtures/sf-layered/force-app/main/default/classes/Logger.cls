/** Org logging: writes Log__c through a platform event so logs survive rollback. Never use System.debug in product code. */
public without sharing class Logger {
    public static void error(String context, Exception ex) { /* publishes Log_Event__e */ }
    public static void info(String context, String message) { /* publishes Log_Event__e */ }
}
