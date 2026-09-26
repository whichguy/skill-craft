/** Base for every selector: enforces sharing and field-level security on queries.
 *  Subclasses declare sObjectType() and fields(); controllers and services never write SOQL. */
public inherited sharing abstract class BaseSelector {
    public abstract Schema.SObjectType sObjectType();
    public abstract List<Schema.SObjectField> fields();
    protected String selectClause() { /* builds SELECT from fields() */ return ''; }
    protected List<SObject> query(String whereClause, Map<String, Object> binds) {
        return Database.queryWithBinds(selectClause() + ' WHERE ' + whereClause, binds, AccessLevel.USER_MODE);
    }
}
