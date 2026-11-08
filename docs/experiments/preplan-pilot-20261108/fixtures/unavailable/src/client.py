"""Offline surrogate for the external inventory service transport.

No external endpoint or credential is configured in this fixture. Its failure
deliberately conveys no information about the service's batch contract.
"""
def apply(target, rows):
    raise ConnectionError("approved sandbox not provisioned; no request sent")
