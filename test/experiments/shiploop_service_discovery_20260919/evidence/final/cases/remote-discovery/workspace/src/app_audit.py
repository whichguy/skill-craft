import logging

audit = logging.getLogger("app.audit")


def record_contact_change(contact_id, field):
    audit.info("contact_change", extra={"contact_id": contact_id, "field": field})
