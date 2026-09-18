# Live local-skill observations, 2026-09-18

Each worker was a newly spawned agent with `fork_turns: none`: no parent
conversation or prior trial response. Agents were restricted to their assigned
fixture and frozen package guidance, with no global skills, personal memory,
external actions, further delegation, or ShipLoop callbacks. This is a fresh
conversation boundary, not a tested host `/clear` operation or token benchmark.

The fixture itself was real local files. Only packet predecessor transitions
were synthetic; no Improve run or full ShipLoop delivery was executed. Copies
remove prior `output`, run/history/notes and `.shiploop` directories. Product
contracts, durable lessons, README/index and generated local skills survive.

| Trial | Input lineage | Observed skill decision |
| --- | --- | --- |
| baseline | Original ShipLoop guidance | Created one local release skill |
| a02 | baseline product files | Reused entire skill package unchanged |
| candidate | Revised ShipLoop guidance | Created one local release skill |
| b02 | candidate product files | Reused unchanged with explicit target override |
| b03 | b02 plus additive freshness contract | Reused unchanged; existing contract-driven procedure was sufficient |
| b04 | candidate plus initial incident contract | Created separate incident skill; old release skill unchanged; output schema ambiguous |
| b04r | candidate plus clarified incident contract | Created separate incident skill; old release skill unchanged; exact outputs pass |
| b05 | candidate plus ordinary README typo | Reused unchanged; corrected only the typo and task output |
| b06 | b03 with v1 authority relocated | Updated existing skill's input/contract locators; one skill retained |
| b07 | b06 product files | Reused the edited skill package byte-for-byte unchanged |

Ten fresh agents executed; nine exact task/artifact checks passed. The remaining
original incident output is preserved as the fixture ambiguity described below.

`summary.json` and per-trial `grade.json` are independent output/artifact checks.
`first-grade.json` preserves earlier grading where checks were extended during
bringup. Creation, updating, and separate-skill conclusions additionally come
from inspecting actual file changes and package digests, not merely oracle exit
status. Original and evolved skill files are preserved in their fixture copies.
The wrappers provide local scope and index-reading instructions; this does not
prove native automatic skill discovery or causal benefit from revised guidance.

`b04` is preserved unchanged. Its incident decision and old release behavior were
correct, but receipt rows included identity fields. The initial public contract
did not define the projection assumed by the oracle. Independent review agreed
this was a fixture ambiguity. Only the next fixture's contract was clarified;
the oracle's expected output was not weakened, and a fresh agent ran `b04r`.

The raw launch files and rendered packets retain the original external study
paths under `/Users/dadleet/tmp/shiploop-local-skills-20260918`. They are historical
inputs, not commands to execute against the archived copies. Frozen package
digests and the focused source delta are retained beside them. Both packages
differed only in the intended prompt module and local-skill reference guide.

Agent action notes exist for the initial creation trials and later trials whose
prompt explicitly requested writing notes. Several intermediate agents interpreted
“preserve notes” as leaving an absent file absent; their final task reports were
used for reported-read/verification observations. Output and file/digest checks
were independently repeated. No claim is made that every read was instrumented.

`final-checks.json` retains the five focused test suites (45 passing checks) and
ShipLoop package parity. `calibration/final-oracle-calibration.json` records eight
known-good/mutated-output cases against the final oracle. The bundled skill
frontmatter validator could not run in the system Python because PyYAML was
absent; simple generated frontmatter, index and local links were inspected
without installing a dependency. Full repository CI and multi-host live tests
were outside this bounded study.
