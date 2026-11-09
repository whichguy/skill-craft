# T1.4 trigger test and T0.4 discovery smoke

Recorded 2026-11-09. Prompts frozen before any counting run (`prompts.json`, sha256 `ce269ffaa4c6958a2ffae939b2ba6a8b3a548f5a544c388a2a556bea3fa6fd0b`). Model sonnet, default effort, Claude Code 2.1.319. Every run had one tool (`Skill`), no MCP server, no persisted session; no answer text is stored here, only which skills fired.

## Step 0: which skills an isolated run can see

- The init event lists skills as well as plugins (48 skills: 26 `skill-craft:*` and 22 bundled ones). `skill-craft:pushpress` is visible, bare `pushpress` is not, and the user's installed skill-craft is not loaded under `--restricted` (plugins: skill-craft 2.36.1 (inline)).
- Correction to the plan: the installed `skill-craft` is no longer 2.35.8. It is 2.36.1 at commit 85a7cda7 (updated 2026-11-09 08:21 local, user scope, enabled), and its `skills/pushpress` is identical to the payload tested here, so `skill-craft:pushpress` is already installed on this Mac.
- The model's own one-turn list agrees: 26 `skill-craft:*` names plus 17 others, no bare `pushpress`.
- Isolation held in every counted run: True (same skills hash, tools `Skill` only, 0 MCP servers).
- Flags: `--max-turns` works although `claude --help` does not list it; stdin must be `/dev/null` or each run waits 3 s.

## T0.4 discovery smoke

- One question that needs the card. A `Skill` call naming `skill-craft:pushpress` fired: True; result `success`, 3 turns, 0.067 USD. Read by hand, the answer used the door router: yes: sends the price to the admin UI (Plans page) or the landing-page JSON, says the API has no plan list and plans-get returns no price, says it did not browse the account and cites the card's 2026-11-08 check. Pass: True.

## T1.4 main pass: 24 prompts x 2 runs

| Measure | Result | Line | Verdict |
|---|---|---|---|
| Explicit recall | 12 of 12 | at least 11 of 12 | PASS |
| Implicit recall | 12 of 12 | at least 8 of 12, a measurement | met |
| False fires | 0 of 24 | at most 1 of 24 | PASS |
| sport80 prompts | 0 of 6 | 0 of 6 | PASS |

| Prompt | Category | Expected | Fired (of 2) | Other skills that fired |
|---|---|---|---|---|
| E1 | explicit | fire | 2 | none |
| E2 | explicit | fire | 2 | none |
| E3 | explicit | fire | 2 | none |
| E4 | explicit | fire | 2 | none |
| E5 | explicit | fire | 2 | none |
| E6 | explicit | fire | 2 | none |
| I1 | implicit | fire | 2 | none |
| I2 | implicit | fire | 2 | none |
| I3 | implicit | fire | 2 | none |
| I4 | implicit | fire | 2 | none |
| I5 | implicit | fire | 2 | none |
| I6 | implicit | fire | 2 | none |
| N1 | neg-mindbody | quiet | 0 | none |
| N2 | neg-wix | quiet | 0 | none |
| N3 | neg-saas-pricing | quiet | 0 | none |
| N4 | neg-budget-workbook | quiet | 0 | none |
| N5 | neg-stripe-code | quiet | 0 | none |
| N6 | neg-sport80 | quiet | 0 | skill-craft:sport80 x2 |
| N7 | neg-sport80 | quiet | 0 | skill-craft:sport80 x2 |
| N8 | neg-sport80 | quiet | 0 | skill-craft:sport80 x2 |
| N9 | neg-other-gym-software | quiet | 0 | none |
| N10 | neg-gym-pricing-advice | quiet | 0 | none |
| N11 | neg-attendance-code | quiet | 0 | none |
| N12 | neg-mailchimp | quiet | 0 | none |

What the sample can and cannot show. Counted over prompts (the two runs of a prompt are repeats): 12 of 12 should-fire prompts fired (95% Wilson interval for the true rate on prompts like these: 0.757 to 1.0), and 0 of 12 quiet prompts fired (0.0 to 0.243). So the description is not obviously broken on this set; it is not shown reliable on every phrasing. The implicit prompts all carry gym words, and no run had a project context to lean on.
Positive control: `skill-craft:sport80` fired in 6 of 6 runs of the three sport80 prompts, so the harness does see another skill fire and those near misses were routed, not ignored.

Infra errors after retries: 0. Main-pass cost 2.59 USD, wall 273.7 s.

## Overlap pass: inside the owner's project checkout, without `--restricted`

Same flags minus `--restricted`; the repo's skills and the user's settings load. It asserts nothing.

| Prompt | Run | Expected | bare `pushpress` | `skill-craft:pushpress` | Skills called |
|---|---|---|---|---|---|
| E1 | 1 | fire | True | False | pushpress |
| E1 | 2 | fire | True | False | pushpress |
| E3 | 1 | fire | True | False | pushpress |
| E3 | 2 | fire | True | False | pushpress |
| I1 | 1 | fire | True | False | pushpress, pushpress |
| I1 | 2 | fire | True | False | pushpress |
| I4 | 1 | fire | True | False | pushpress |
| I4 | 2 | fire | True | False | pushpress |
| N1 | 1 | quiet | False | False | none |
| N1 | 2 | quiet | False | False | none |
| N10 | 1 | quiet | False | False | none |
| N10 | 2 | quiet | False | False | none |
| N11 | 1 | quiet | False | False | none |
| N11 | 2 | quiet | False | False | none |
| N8 | 1 | quiet | False | False | skill-craft:sport80 |
| N8 | 2 | quiet | False | False | skill-craft:sport80 |

Not a clean run: I1 run 1: error_max_turns: two Skill calls inside the 2-turn cap, no answer (last of 3 attempts). That is model behaviour (two Skill calls), not an infrastructure fault; my runner retried it twice, which cost money and changed nothing.

Init variants seen (skills visible to those runs):
- 334 skills and 32 plugins; bare `pushpress` visible: True; pushpress names: ['pushpress', 'skill-craft:pushpress']; skill-craft entries: ['skill-craft 2.36.1 (inline)'] (the installed copy, also 2.36.1, is not listed separately, so the inline plugin takes its place; this is what a real session in this repo sees: the project skill and the marketplace skill side by side); tools: ['Skill']; MCP servers: 0; permission mode: auto

Should-fire runs here: 8. The bare project `pushpress` fired in 8 and `skill-craft:pushpress` in 0. Quiet runs here: 8; neither pushpress skill fired in 8 of them.

Read-only check on the shared checkout: `git status --porcelain` went from 11 to 8 lines during the pass because another session committed there at 08:32; the files edited in the window were other sessions' work. Nothing these runs create showed up: no file under `.claude/`, no state file, no transcript (the runs used `--no-session-persistence` and `SHIPLOOP_KEEPALIVE=off`). In a checkout other sessions write to, that is absence of evidence, not proof. Cost 2.19 USD (retries included).

Total spend, all runs: 4.88 USD.

