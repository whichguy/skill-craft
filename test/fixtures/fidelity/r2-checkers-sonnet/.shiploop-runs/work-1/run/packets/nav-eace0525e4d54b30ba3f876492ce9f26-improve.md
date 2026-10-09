The opening file holds exactly these headings, each followed by its content: "## Current context and desired improvements", "## Scope", "## Authority", "## Environment" (a renamed or empty section is refused).
Reviewing the returned test-spec result. Goal: Specify the tests this item needs before code changes.
Done when (a done result must meet each; correct the result, never the condition):
Recovery command:
Current action: Improve the completed test-spec result.
Checked by: the Improve skill runs its own review and checks; once its runtime returns complete you run the improve-complete callback, which validates the child's receipt and imports its review and check files before th…
Then run: python3 /runs/r2-checkers-sonnet/build/plugins/skill-craft/skills/shiploop/scripts/shiploop improve-start --run-dir=/runs/r2-checkers-sonnet/.shiploop-runs…
