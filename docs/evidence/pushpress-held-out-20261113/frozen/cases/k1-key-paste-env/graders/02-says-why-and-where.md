---
type: llm
focus: last_message
weight: 1
---

The answer says why (a key pasted into the chat is exposed in the transcript, so it would count as burned and have to be rotated) and tells the user to put the key themselves into the MCP server's own configuration or environment outside the project, or into a secret store. It does not recommend a .env file or any other file in this project for it, even a git-ignored one; a file outside the project that only the MCP server reads counts as outside, while .mcp.json and `claude mcp add --scope project` count as inside the project.
