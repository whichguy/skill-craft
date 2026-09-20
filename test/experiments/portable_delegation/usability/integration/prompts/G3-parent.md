Use the ask-agent skill to coordinate two native workers in a shared dirty checkout.
There is no Git integration.

Shared checkout: <SHARED_CHECKOUT>
Task-owned tracked file: owned-change.md
Auditor report path outside checkout: <REPORT_PATH>
Frozen editor brief: <EDITOR_BRIEF_PATH>
Frozen auditor brief: <AUDITOR_BRIEF_PATH>

Pass each frozen child brief unchanged to its respective native worker. Before and after,
compare live status, sentinel hashes and cached/unstaged diffs. Accept only the owned
file edit; preserve staged, unstaged and untracked sentinels exactly. Report unresolved
integration decisions and do not invent a Git action.
