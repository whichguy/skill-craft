# Generalized-discovery experiment oracle

`oracle.py` is a coordinator-owned calibration and evidence collector for the
four public synthetic fixture families. It does not inspect a worker report for
keywords or decide whether a report is semantically sound. A blind reviewer
assesses explanations, reuse choices, justified N/A decisions, evidence fidelity,
and bounded stopping from anonymized materials.

## Frozen factual rubric

| Family | Facts a reviewer may expect when evidence supports them | Allowed unresolved boundary |
| --- | --- | --- |
| F1 | The selected bundled parser differs from the manifest in the reference fixture; the atomic export wrapper and local permission boundary are reusable evidence. | No remote service, browser, or MCP application role is supplied. |
| F2 | `receipt.created` reaches a host-selected schema-2 component; producer acknowledgement is distinct from the local retry/effect model. | A configured `consumerRuntime` does not prove the probe interpreter or deployed host. The in-memory effect model does not prove persistence. |
| F3 | Metadata succeeds, task data is denied with `scope_required`, and the advertised connector is unrelated. | The local simulation establishes no real account, identity, permission, or hosted-target behavior. The denial blocks only its dependent conclusion. |
| F4 | The local completion model rejects the older response, `BoardPanel` is the existing component, and store/cache roles are separate. | No browser rendering, network timing, deployed behavior, cache expiration, or user access is established. |

The frozen output includes the evidence paths for each family. It must be stored
outside every worker workspace before trials, normally at
`<study>/private/oracle-calibration.json`.

## Calibration

Run from the repository root after finalizing the fixture bytes and before any
trial workspace is prepared:

```sh
python3 test/experiments/shiploop_generalized_discovery/oracle.py \
  --calibrate \
  --output /absolute/study/private/oracle-calibration.json
```

Calibration materializes fresh reference and altered-variant directories for
each family, runs every documented public `probe.py` command, records exact argv,
stdout, parsed JSON, return code, and source-tree hashes, then checks the public
reference facts. It also confirms that each controlled altered variant changes
its declared observation. Those altered variants establish that the factual
oracle is not vacuous; they do not label an alternate state as universally
incorrect or prove report quality.

## Arm evidence

After a runner has completed an arm, collect deterministic evidence with:

```sh
python3 test/experiments/shiploop_generalized_discovery/oracle.py \
  --study /absolute/study --arm trial-01 \
  --receipts /absolute/study/receipts.jsonl \
  --output /absolute/study/private/grades/trial-01.json
```

The arm record checks supplied-source hashes before and after the run, report
presence and runner metadata, plus any coordinator-owned probe receipts. It does
not require every probe to have run: a worker can support a finding from inspected
source, and an inaccessible runtime remains an allowed unresolved gap. If a probe
was observed, its receipt is compared with frozen calibration output. Missing or
malformed receipts remain explicit evidence gaps rather than a prose score.
