ADMIN = "admin-demo"
STAFF = "staff-demo"

ASSIGNMENTS = {
    ADMIN: {"board:read", "board:metadata:read"},
    STAFF: {"board:read"},
}


def has_access(principal, permission):
    return permission in ASSIGNMENTS.get(principal, set())
