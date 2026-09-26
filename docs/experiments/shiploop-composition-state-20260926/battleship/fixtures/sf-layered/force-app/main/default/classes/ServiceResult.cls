/** Uniform envelope returned by every @AuraEnabled method; c/apex unwraps it and shows errors as toasts. */
public class ServiceResult {
    @AuraEnabled public Boolean ok; @AuraEnabled public Object data; @AuraEnabled public String errorCode; @AuraEnabled public String message;
    public static ServiceResult success(Object data) { ServiceResult r = new ServiceResult(); r.ok = true; r.data = data; return r; }
    public static ServiceResult failure(String code, String message) { ServiceResult r = new ServiceResult(); r.ok = false; r.errorCode = code; r.message = message; return r; }
}
