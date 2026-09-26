/** One trigger per object; logic lives in a handler subclass. */
public virtual class TriggerHandler {
    public void run() { /* dispatches to beforeInsert/afterUpdate... with recursion guard */ }
    protected virtual void beforeInsert() {} protected virtual void afterInsert() {}
    protected virtual void beforeUpdate() {} protected virtual void afterUpdate() {}
}
