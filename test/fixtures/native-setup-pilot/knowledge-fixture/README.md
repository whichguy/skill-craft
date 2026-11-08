# Code-knowledge review examples

These six frozen source examples separate working behavior from diagnostic quality and durable implementation knowledge. Reviewers should explain the causal risk in the code, not count comments or require a historical warning everywhere.

| Case | Distinction under review |
| --- | --- |
| A17 | Correct replay guard, useful diagnostics and sufficient incident rationale. |
| B04 | Correct behavior and diagnostics, but missing the reason replay lookup must precede the version check. |
| C82 | Correct behavior with a misleading comment proposing removal of the needed guard. |
| D31 | The replay guard is missing; a correct contract docstring does not fix behavior. |
| E56 | Simple formatter with a validated caller; no removed-path warning is warranted. |
| F90 | Correct behavior and rationale, but insufficient received-value diagnostics. |

registration.json retains the prospectively frozen expectations and hashes of all 13 inputs. review-guidance.txt supplies the common four-dimension lens. The original exercise requested Terra xhigh; served identity was unverified. All six single-sample conclusions matched these expectations and independent semantic review supported them. B04 remains a judgment boundary, rather than a universal rule about comment length.

The preceding five-case version had real gaps in its supposed positive control. It remains in external evidence and is not counted as a false-positive rate. This version is a narrow calibration, not a prompt comparison or measured general ShipLoop improvement.

No model calls run in CI. Reuse these cases for blind review calibration, preserving hashes and labels before collecting responses; retain contrary evidence rather than altering labels to match a reviewer.
