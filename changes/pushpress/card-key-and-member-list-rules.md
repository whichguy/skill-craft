---
bump: patch
---
The card now states two safety rules that a no-tenant quiz found missing or too weak. An API key or webhook secret never goes through chat: the agent does not ask for one, print it, write it anywhere or screenshot it, and if the user offers to paste one it stops them, says that a key or secret pasted into chat is burned, and has them put it straight into the MCP server's environment or a secret store (one pasted anyway is not saved or reused, and the user is told to rotate it). A request for a project file, note or outbound message that lists members' names, emails, phones or birthdays is declined, whether it would be built from the live report, pasted rows or an exported report, and counts, column names or the PushPress screen are offered instead.
