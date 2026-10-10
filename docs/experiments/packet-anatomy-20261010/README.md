# Packet anatomy baseline, 2026-10-10 (packet-compaction Phase 0)

Bytes per section of today's packet print order, per stage, for the two frozen baseline runs and for a no-model walk of the
current engine. Produced by `test/shiploop_e2e/packet_anatomy.py`; the sections follow `render()` and `_render_improve()` in
`skills/shiploop/scripts/shiploop_navigator.py` (see the tool's docstring and `RULES`). Sections plus `unclassified` always sum
to the file bytes; the unclassified share is printed in each table.

| file | source | packets |
|---|---|---|
| `checkers-1.md/.json` | the Run Review page's `packets` documents of run checkers-1 (ShipLoop 0.58.0, release 1.26.0), re-written to `nav-<id>[-improve].md` | 45 (37 producer, 8 Improve) |
| `battleship-1.md/.json` | same, run battleship-1 | 45 |
| `no-model-walk-current-engine.md/.json` | `packet_anatomy.py --walk DIR` on this checkout, inline delegation, synthetic results | 50 (34 producer, 8 improve-bind, 8 improve-start) |

The reviewer's 1.81 MB / 38 producer packets for checkers-1 (`docs/experiments/packet-review-20261010/01-shared-frame.md`)
differs from the 45 packets here by one producer packet that the page does not hold; the mean producer packet (37.8 KB here,
37.7 KB there) and the absolute-path share (23.1%) agree. The raw packets are not copied: they live in the Run Review page.
The walk's paths are short temporary paths, so its path share is a floor, not a comparison with the e2e runs.

Rerun:

```sh
python3 test/shiploop_e2e/packet_anatomy.py <run>/run/packets --label NAME --out docs/experiments/packet-anatomy-20261010
python3 test/shiploop_e2e/packet_anatomy.py --walk /tmp/walk --label no-model-walk-current-engine --out DIR   # about 17 s
```
