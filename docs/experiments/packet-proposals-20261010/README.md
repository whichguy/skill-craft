# Packet proposals, 2026-10-10

Four representative ShipLoop packets redrafted under the compaction plan
(`docs/shiploop-packet-compaction-plan-2026-10-10.md`, branch rr23-9f8c87; owner decision the same day: the renderer and the
re-cut are owned by the session working on branch exp/step-slice-32c6ee, and these drafts are its **acceptance checks**).
Source packets: the release-A verification run (`/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet`, Checkers on Sonnet 5.5).
Each `<stage>.md` holds the proposed packet, its size, an obligation map (one row per instruction, rule, fact or locator of
the current packet, with its disposition and reason), risks after a context clear, the engine changes it needs, and an
independent adversarial check. `<stage>.packet.txt` is the proposed packet alone.

| Packet | Current bytes | Proposed bytes | Map rows | Check verdict |
|---|--:|--:|--:|---|
| plan | 57,289 | 22,975 | 177 | safe with fixes; one blocker: it relies on `shiploop ref` and `shiploop backchain-start`, which do not exist |
| test-green | 41,318 | 20,612 | 154 | safe with fixes |
| release-verify | 36,881 | 17,572 | 145 | safe with fixes |
| spec Improve parent | 48,101 | 23,864 | 163 | safe with fixes |

Findings common to the four (the checks agree):
- Every obligation a gate refuses fits in the first screen as one line; keeping each refusal as its own line is why the plan
  packet lands at 23 KB, not the 11-12 KB estimate.
- `shiploop ref` (and for plan `backchain-start`) must ship with the packets, or the packet keeps an "open REF/<file> at that
  heading" fallback and, for the Backchain child, its inline start contract.
- Root-relative paths are the main S-6 risk: a cleared model may write a literal `WT/...` or `CHILD/...` path, and the evidence
  gate checks only paths that start with `/`. Files the model must write, and every evidence path, should print absolute.
- "Checked by" gains refusals the engine already applies but today's packets omit (plan: credential screen, dropped
  requirement id, work_items field rules).
- Measurement readers (E2E counters, `test/shiploop_e2e/packet_anatomy.py`, the Run Review exporter) match today's labels
  ("Callback for this stage", "Recovery command:", "Call this when done:"); a new layout must update them in the same change.
- Probe before shipping: a context clear inside the loop (test-green, the Until Loop card no longer read in full), inside
  release-verify with a clause missing from spec.md (the verbatim request dropped), and inside an Improve child (relative paths).
