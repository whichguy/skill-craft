trigger AccountContactSeed on Account (after update) {
    for (Account account : Trigger.new) {
        List<Contact> contacts = [
            SELECT Id, Description
            FROM Contact
            WHERE AccountId = :account.Id
        ];
        for (Contact contact : contacts) {
            contact.Description = 'updated by seed';
        }
        update contacts;
    }
}
