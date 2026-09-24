# /shiploop

Start a new ShipLoop run (navigator protocol 3; protocol 4 is opt-in). The
script owns the graph: it returns the prompt for the current step and the one
callback that completes it. Do that step, then run the printed callback.

~~~sh
# New Git-backed work in an isolated worktree (preferred):
python3 "$SKILL_ROOT/scripts/shiploop" workspace start \
  --repo "$REPO" --workspace-root "$WORKSPACE_ROOT" --prompt='<user request>'
# Explicit in-place or non-Git run:
python3 "$SKILL_ROOT/scripts/shiploop" init \
  --repo "$REPO" --run-dir "$RUN_DIR" --prompt='<user request>'
~~~

Optional flags on either entry: `--improve-skill=<absolute selected Improve
SKILL.md>`, `--delegation=ask-agent` (default `inline`), `--delivery-contract`,
and `--protocol-version 4` (`workspace start`) or `--navigator-version 4`
(`init`). A saved run from an older protocol (v1/v2, managed or legacy) is
refused with an error naming it; start a fresh run directory instead.

Read the returned packet, retrieve only the durable context it points to, and
follow its first callback line. See the skill card and
[navigator guide](../references/navigator.md).
