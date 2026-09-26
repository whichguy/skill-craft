---
bump: minor
---
Planning now decides where new code and its data live, in every execution
environment the change runs in or reaches: the local checkout, a remote runtime
behind an MCP server, API or CLI, a hosted platform, and each service of a
multi-service system. The `plan` stage maps each environment's library
structure, how it resolves names, the libraries and services the code shares
names with, and how it stores data (existing and destination schema with their
owner, or a new schema with its storage policy), and records a Namespace and
data map. `step-plan` names each new file, module, public symbol and stored
field with its environment, home, visibility and collision or round-trip
check. Code craft gains rule 8, "Put it where it belongs", which the quality
loop reviews. New stack-neutral Namespaces and placement and Schema and storage
practice cards; the platform cards give Apps Script, Python, Bash, Salesforce
and UI examples.

UI work now defaults to an ambitious, highly interactive interface: plans name
the rich interactions they deliver and any they scale back with a reason, and
KISS/YAGNI no longer justify trimming the planned UI.
