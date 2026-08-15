# prompt-on-change — host-local schedule

Host-agnostic Layer-1 prompt. Fill placeholders, then run on the current host.
Do not pin a model. Do not require a single host CLI as the only path.
Do not claim Cursor Automations (or any one host’s scheduler) as runtime.

## Input

Skill root: `{{SKILL_ROOT}}`  
Config path: `{{CONFIG}}`  
Preferred cadence (optional): `{{CADENCE}}`

## Task

Propose **one** host-local way to re-run the detect CLI. Pick from:

1. **Ask again** — the user re-invokes this skill; no scheduler.
2. **cron** (Linux/macOS) — `scripts/prompt-on-change run --config {{CONFIG}}`
   on an interval. Use `$POC_STATE_DIR` / `$SKILL_ROOT`; never `/opt/data`
   as the only recipe.
3. **launchd** (macOS) — same command, same env binding.

Do not invent a Hermes cron, a Cursor Automation, or a cloud webhook.

## Output

A short recipe (command + env) for the chosen option, plus residual risk
(missed polls, overlapping runs). If cadence is unset, default to “ask again”.
