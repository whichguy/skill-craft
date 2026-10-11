# Host evidence

This prompt-only package needs repository reading, document writing and optional
local command execution. Git/network are needed only for cloning/history. A
missing runtime limits execution evidence, not source inspection.

| Host | Intended execution | Evidence |
| --- | --- | --- |
| Codex | Native conversation and optional native review | Native generation exercised on JavaScript/Python libraries and a preservation fixture; local probes and scoped source review |
| Claude Code | Native conversation and available inspection tools | Not exercised |
| Grok | Native conversation and available inspection tools | Not exercised |
| Hermes | Native conversation and available inspection tools | Not exercised |

No required host CLI, model, MCP server or companion skill. Package validation
and discovery do not establish runtime behavior on an untested host.
