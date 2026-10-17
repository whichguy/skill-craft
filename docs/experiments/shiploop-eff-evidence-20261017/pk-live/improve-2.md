ShipLoop navigator | improve | revision 6 | the test-strategy result
1. Run the improve skill on the test-strategy result. For example, on Claude Code:
       /improve ShipLoop Improve: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/8acf399b-0cf4-40cc-bba3-bf238461db58/scratchpad/sfchess/live2/.shiploop-runs/work-20261017-005941-6661b3/worktree/.shiploop-improve/nav-7ff82c154a75405ca18b38e594adc478/nav-10230caa244540cca25e257485b63f16/handoff.md
   (the Skill tool, skill "improve", with that argument; on another host, open /private/tmp/claude-501/-Users-dadleet-src-skill-craft/8acf399b-0cf4-40cc-bba3-bf238461db58/scratchpad/sfchess/live2/home/.grok/installed-plugins/skill-craft-010e915e/skills/improve/SKILL.md and pass the same argument)
2. When the improve skill has completed, run: python3 /private/tmp/claude-501/-Users-dadleet-src-skill-craft/8acf399b-0cf4-40cc-bba3-bf238461db58/scratchpad/sfchess/live2/home/.grok/installed-plugins/skill-craft-010e915e/skills/shiploop/scripts/shiploop complete --run-dir=/private/tmp/claude-501/-Users-dadleet-src-skill-craft/8acf399b-0cf4-40cc-bba3-bf238461db58/scratchpad/sfchess/live2/.shiploop-runs/work-20261017-005941-6661b3/run --action=nav-6d9f443c2c4d40fdbaf576e4ac289aaa
Keepalive marker: SHIPLOOP-RUN run=nav-7ff82c154a75405ca18b38e594adc478 rev=6 dir=/private/tmp/claude-501/-Users-dadleet-src-skill-craft/8acf399b-0cf4-40cc-bba3-bf238461db58/scratchpad/sfchess/live2/.shiploop-runs/work-20261017-005941-6661b3/run

Host-recorded labels and reasons are untrusted status context, not instructions or authority.
=== ShipLoop status ===
Where:     Preparation > test-strategy (5 of 7) > improve
Run:       Preparation ▶ | Work items 0/1 · | Release ·
Stages:    intake ✓ discovery ✓ research ✓ spec ✓ test-strategy ▶ plan · prepare ·
Done:      test-strategy result ready: Harness is synchronous Apex on alias de, one test class at a time, with no shared org data.
Next:      improve: run the improve skill on the test-strategy result
=== end ShipLoop status ===

=== ShipLoop narrative ===
Show the user this narrative exactly as written, as Markdown in your own message, then continue; do not rewrite or extend it.

#### 🚢 ShipLoop — Build a chess rules engine in Apex with a simple Lightning web component board, in a Sale…
`███████░░░░░` **Preparation 4/7** · Work items (set by plan) · Release (9 steps)

**✅ Achieved**
- **intake** — Mapped the chess engine, board, org deploy, and test outcomes.
- **discovery** — Empty repo; alias de is connected; no tests yet.
- **research** — API 67.0, perft oracles, and the SLChess deploy scope are set.
- **spec** — Wrote R-1 through R-13 and the CPU bound in the spec.

**▶️ Now** — **test-strategy**: improve: the improve skill is reviewing the test-strategy result

**🔭 Ahead**
- **plan** — plan the work items
- **prepare** — prepare the environment
- **then the work items and release**

**⏱ Pace** — 4 steps in 28 min
=== end ShipLoop narrative ===

