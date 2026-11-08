# Native setup and readiness fixture

This is a tiny Python-standard-library-only product fixture. The service and
grant are synthetic records; no network, provider account, credential, or real
service is involved. The source fixture is copied into the slice worktree.
Persistent changes made by `readiness_cli.py` go only to the path named by
`NATIVE_SETUP_TARGET`, which the external slice adapter supplies through
`slice.py`'s existing `seed_state` support. ShipLoop's product checkout,
knowledge home, and run artifacts are separate harness outputs and are not
restricted to that state directory.

## Targets and authority

- `service`: its fixture record says ready. `probe service` checks that local
  record; `journey service` runs the local preview path.
- `sandbox`: its fixture record says not provisioned and not configured.
  `authorization.json` explicitly allows provisioning and configuring this
  local sandbox. `setup sandbox` writes a deterministic receipt and is
  idempotent.
- `grant`: its fixture record says unavailable and unauthorized. It has no
  credential or setup operation; the status identifies owner authorization as
  the missing prerequisite.
- `offline_summary.py`: formatting behavior depends only on its input rows and
  is independent of the state path, service, sandbox, and grant.

The word “service” names a local stand-in. `journey` is a deterministic local
consumer exercise, not a deployed or authenticated service interaction.
Configuration readiness and a successful journey are distinct signals.

The offline formatter's required output is exactly `<target>: <status>\n`
for each input row, preserving input order, with no leading or trailing spaces.
An empty list renders as the empty string. This behavior is independent of the
external setup state.

## Commands

Run from this directory, with the environment variable pointing at an
external writable state directory:

```sh
export NATIVE_SETUP_TARGET=/absolute/path/to/the-slice-output/target
python3 readiness_cli.py probe service
python3 readiness_cli.py probe sandbox
python3 readiness_cli.py probe grant
python3 readiness_cli.py setup sandbox
python3 readiness_cli.py probe sandbox
python3 readiness_cli.py setup sandbox       # idempotent; ready, changed=false
python3 readiness_cli.py journey service
python3 readiness_cli.py journey sandbox
python3 readiness_cli.py journey grant       # blocked; no external call
```

Expected probe results are JSON objects with `status` `ready`, `missing`, or
`unavailable`. A ready sandbox also reports `receipt_valid: true`. A successful
setup returns `ready` and `changed: true` on the first call; a repeat returns
`ready` and `changed: false`. The audit JSONL records only a sequence number,
command, target, and result; it contains no timestamp, environment value, or
credential.

`journey` returns `completed` for the ready service and the prepared sandbox;
it returns `blocked` for the external grant. These outputs show consumer use
separately from probe/setup readiness. All journey execution is local and
deterministic.

The seed state is `../readiness-state/`. It is copied to a fresh target for
each slice, so one sample cannot make another sample look prepared.
