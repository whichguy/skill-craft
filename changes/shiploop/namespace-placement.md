---
bump: minor
---
Planning now decides where new code and its data live. The `plan` stage maps
the current library structure, the runtime's actual name space, the libraries
the code shares it with, and how data is stored there (existing and
destination schema, or a new schema with its storage policy), and records a
Namespace and data map. `step-plan` names each new file, module, public symbol
and stored field with its home, visibility and collision or round-trip check.
Code craft gains rule 8, "Put it where it belongs", which the quality loop
reviews. New Namespaces and placement and Schema and storage practice cards,
plus runtime notes for Apps Script, Python, Bash, Salesforce and UI.

UI work now defaults to an ambitious, highly interactive interface: plans name
the rich interactions they deliver and any they scale back with a reason, and
KISS/YAGNI no longer justify trimming the planned UI.
