# Ratchet against ShipLoop: results

| Case | Arm | Minutes | Output tokens | Input tokens | Held-out checks | Faults caught by own tests | Line coverage (changed, Node) | Docs: new surfaces named | Tests run |
|---|---|---|---|---|---|---|---|---|---|
| shared-expenses | ShipLoop | 14.3 | 28k | 10.7M | 6 of 6 | 82% | 95% | 0 of 3 | 5 |
| shared-expenses | Ratchet | 46.4 (first build 10.2) | 111k | 8.1M | 6 of 6 (first build 6) | 52% | 93% | 4 of 4 | 13 |
| node-chess-engine | ShipLoop | 10.4 | 21k | 6.0M | 10 of 10 | 80% | 99% | 0 of 5 | 8 |
| node-chess-engine | Ratchet | 37.2 (first build 8.5) | 88k | 6.5M | 10 of 10 (first build 10) | 83% | 98% | 5 of 5 | 16 |
| ticket-assignment | ShipLoop | 15.3 | 30k | 11.8M | 18 of 18 | 100% | 95% | 2 of 2 | 123 |
| ticket-assignment | Ratchet | 100.4 (first build 11.1) | 132k | 12.4M | 18 of 18 (first build 18) | 96% | 100% | 2 of 2 | 134 |
| grokbot-local | ShipLoop | 26.5 | 53k | 18.6M | 77 of 77 | 45% | 94% | 3 of 6 | 8 |
| grokbot-local | Ratchet | 162.3 (first build 20.0) | 234k | 31.4M | 77 of 77 (first build 77) | 53% | 97% | 3 of 8 | 19 |

## Readings (registered margins; a blank is no difference shown)

| Case | R1 time | R2 tokens | R3 breadth | R4 depth | R5 coverage | R6 documentation | R7 code quality | R4b calibrated defects |
|---|---|---|---|---|---|---|---|---|
| shared-expenses | ShipLoop |  |  | ShipLoop |  | Ratchet | Ratchet |  |
| node-chess-engine | ShipLoop |  |  |  |  | Ratchet | ShipLoop |  |
| ticket-assignment | ShipLoop |  |  |  |  |  |  | Ratchet |
| grokbot-local | ShipLoop | ShipLoop |  |  |  |  | Ratchet |  |

**Overall:** no difference in results shown (quality cells ahead: ShipLoop 2, Ratchet 4).

## Predictions

- P1 ShipLoop ahead on time in 4 of 4: right
- P2 ShipLoop ahead on tokens in 4 of 4: wrong
- P3 breadth no difference in at least 3: right
- P4 ShipLoop ahead on depth (a) in at least 2: wrong
- P5 coverage no difference in at least 3: right
- P6 documentation no difference in at least 3: wrong
- P7 judge split or absent in at least 3: wrong
- P8 overall no difference in results shown: right
