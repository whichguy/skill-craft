---
version: 0.1.0
---
New skill: evaluate a prompt change against a rubric over a scenario catalog. Runs arms on Grok 4.7 (medium effort) by default, grades with one evidence-first judge per round (Opus 5.5, medium effort, by default), and decides with scenario-clustered paired intervals, guardrails and recorded run conditions. Ships the architecture suites (up to 34 criteria and 23 scenarios across seven environments, including cross-runtime ones). SPEC.md is the reference for conditions, models, the ship rule, the change lifecycle and process hygiene for long runs.
