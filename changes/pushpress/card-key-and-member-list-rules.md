---
bump: patch
---
The card now states two safety rules that a no-tenant quiz found missing or too weak. A PushPress API key or webhook secret never goes through chat: if the user offers to paste one, stop them, have them put it straight into the MCP server's environment or a secret store, and treat a key that reached a transcript as burned and to be rotated. A request for a file, note or message that lists members' names, emails, phones or birthdays is declined (including turning pasted rows or an exported report into one), and counts, column names or the PushPress screen are offered instead.
