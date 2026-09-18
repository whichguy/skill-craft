# Generalized discovery fixture contracts

These four fixture families support a bounded local discovery study. They are
small synthetic environments, not vendor adapters, production systems, or proof
of access to a hosted target. Materialization creates a disposable worker root
with source, a `README.md`, and a read-only local `probe.py`.

Use the task text supplied by `fixtures.TASKS[family]`. It asks for a discovery
report without prescribing technologies or expected conclusions. Workers may
read supplied files and use the documented probe commands. They must not install
tools, change permissions, make network calls, or edit the fixture.

| Family | Focus | Safe observations |
| --- | --- | --- |
| `f1` | A local batch process, selected dependency, existing output mechanism, and local file boundary. | `python3 probe.py dependency`, `python3 probe.py permissions`, `python3 probe.py export` |
| `f2` | An event producer, a host-selected consumer component, and retry handling. | `python3 probe.py runtime`, `python3 probe.py retry` |
| `f3` | A local reader for an existing simulated managed target and an advertised unrelated connector. | `python3 probe.py metadata`, `python3 probe.py task-data`, `python3 probe.py connectors` |
| `f4` | An interactive client/service control with local presentation, state, and cache sources. | `python3 probe.py completion-order`, `python3 probe.py storage`, `python3 probe.py component` |

Each probe prints one JSON object to standard output and uses only the files in
its own workspace. Its command name and JSON shape are stable across controlled
materializations; an alternate materialization can change an observed behavior
for oracle calibration without changing that public interface.

`f3` is explicitly a local simulation. Its metadata and task-data observations
are demonstrations of distinct local operations, not a real account, identity,
connection, permission grant, or vendor API. An unavailable task-data observation
supports a blocked conclusion only for the dependent question; it does not erase
the other evidence or authorize a different connector or target.

`f4` uses a deterministic local harness. A completion-order observation supports
only the modeled local behavior. It does not prove browser rendering, an actual
client connection, network timing, deployed service behavior, or user access.

`f2`'s retry observation models local in-memory record handling: producer
acceptance and modeled consumer handling are distinct, but process-surviving
durability is not established. `f4`'s storage observation shows separate local
source and cache code plus a configured TTL value; it does not establish
process-surviving storage or TTL expiry. Oracles must not grade either as proof
of those unobserved properties.

The public sources and permitted probes are the evidence surface. A report should
separate observed facts, reasonable inferences, inapplicable categories with a
reason, and open questions. Reuse recommendations should point to an existing
source mechanism and state the relevant runtime or access boundary.
