trigger AccountContactReference on Account (after update) {
    Set<Id> accountIds = new Map<Id, Account>(Trigger.new).keySet();
    List<Contact> contacts = [
        SELECT Id, Description
        FROM Contact
        WHERE AccountId IN :accountIds
    ];
    for (Contact contact : contacts) {
        contact.Description = 'updated by reference';
    }
    if (!contacts.isEmpty()) {
        update contacts;
    }
}
