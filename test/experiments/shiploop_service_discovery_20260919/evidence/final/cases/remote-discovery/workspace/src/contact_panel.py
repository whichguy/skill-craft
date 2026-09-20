def display_contact(contact):
    return {"name": contact["Name"], "score": contact.get("ComputedScore__c")}
