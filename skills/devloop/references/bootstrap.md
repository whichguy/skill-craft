# Engine provisioning boundary

The distributed **devloop** skill is a runtime shim, not an installer. It only
resolves an already present engine and exits **2** when none is available. A
marketplace host must never fetch, unpack, or execute a setup override while a
skill is handling a user request.

## Operator-only provisioner

An operator who already has a trusted `skill-craft` checkout may provision an
engine with the repository-level command:

```sh
bash /absolute/path/to/skill-craft/scripts/devloop-setup.sh --help
```

That script is intentionally **outside** `skills/devloop/`; generated plugin
views do not contain it. It verifies a pinned archive or approved local source,
uses a lock plus staged atomic replacement, writes an ownership marker only
after its dependency/CLI preflight validates, and never overwrites the foreign
Hermes skill leaf. It is a deliberate operator action, not a recovery path the
card may run.

### Interpreter and dependency contract

For a staged engine, setup selects `ENGINE/.venv/bin/python3` when executable;
otherwise it selects `python3` on `PATH`. The runtime uses the same order. The
operator must preinstall the current engine dependency `pytest` in that selected
interpreter. Before activation, setup runs `import pytest` and
`scripts/devloop_cli.py --help`, so an import-broken CLI receives exit **2** and
no marker is written. It does **not** install Python packages, create a virtual
environment, or claim to validate arbitrary future lazy dependencies; a future
engine dependency must extend this explicit release contract and its tests.

After provisioning, select the engine by either:

1. setting `DEVLOOP_HOME` to its engine root; or
2. placing the owned engine at `${DEVLOOP_DATA_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}}/devloop`.

## Host affinity

The runtime keeps the logical installed skill path distinct from the physical
checkout path. A `~/.grok/skills/devloop` symlink therefore selects `host=grok`
without treating an ambient Hermes engine as an implicit source. Hermes engine
resolution is allowed only on the Hermes host or after an explicit
`DEVLOOP_ALLOW_HERMES_SEED=1` / `--allow-hermes-seed` opt-in.

Codex marketplace/cache paths under `~/.codex/plugins/` are Codex-affine just
like `~/.codex/skills/`. An unrecognized `host=auto` has no native transport and
therefore also requires explicit `DEVLOOP_TRANSPORT=grok` or `=hermes`; only
known Grok and Hermes hosts choose their native transport.

## Runtime honesty

| Host | Runtime behavior |
|------|------------------|
| Hermes | Uses its preinstalled engine and Hermes transport by default. |
| Grok | Uses a preinstalled Grok-capable engine and requires the Grok CLI. |
| Claude, Codex, Cursor | Have no native engine port. They fail closed unless an operator explicitly supplies `DEVLOOP_TRANSPORT=grok` or `=hermes`; no host defaults to Hermes. |

`DEVLOOP_DEPTH` or `DEVLOOP_NESTING` prevents nested invocation. Missing engine,
missing transport, missing Grok CLI, or absent capability declaration returns
exit **2**. The card must not substitute `evidence-gates` for DevLoop.
