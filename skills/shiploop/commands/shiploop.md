# /shiploop

Start a new ShipLoop run (navigator protocol 4, the only protocol). The
script owns the graph: it returns the prompt for the current step and the one
callback that completes it. Do that step, then run the printed callback.

~~~sh
# New Git-backed work in an isolated worktree (preferred):
python3 "$SKILL_ROOT/scripts/shiploop" workspace start \
  --repo "$REPO" --prompt='<user request>'   # prints its new .shiploop-runs root
# Explicit in-place or non-Git run:
python3 "$SKILL_ROOT/scripts/shiploop" init \
  --repo "$REPO" --run-dir "$RUN_DIR" --prompt='<user request>'
~~~

Optional flags on either entry: `--improve-skill=<absolute selected Improve
SKILL.md>` (required with `--planning-review none`), `--delegation=ask-agent` (default `inline`) and `--delivery-contract`.
Without `--improve-skill`, `init` records the Improve card installed beside ShipLoop.
There is no protocol selector. A saved run from an older protocol (v1/v2/v3,
managed or legacy) is
refused with an error naming it; start a fresh run directory instead.

Exit code 3 with `SHIPLOOP-GRANT-NEEDED` means this session's sandbox refuses a
write the run needs; nothing was created. Show the block to the user, wait for
the grant it names, then run its printed rerun command. Do not work around it.

Read the returned packet, retrieve only the durable context it points to, and
follow its first callback line. See the skill card and
[navigator guide](../references/navigator.md).
