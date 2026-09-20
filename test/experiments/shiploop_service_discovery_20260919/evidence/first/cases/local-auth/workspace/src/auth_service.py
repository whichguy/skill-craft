class PasswordAuth:
    def __init__(self, logger, sessions):
        self.logger, self.sessions = logger, sessions

    def authenticate(self, username, password, valid):
        if not valid:
            self.logger.info(
                "login_failed", extra={"subject": username, "method": "password"}
            )
            raise PermissionError("invalid credentials")
        return self.sessions.issue(username)
