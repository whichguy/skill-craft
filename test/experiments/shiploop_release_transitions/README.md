# Release transition decision cases

These cases exercise the host's interpretation of release guidance. They are not
remote deployment tests or real Improve runs. `cases.json` retains the five
frozen scenarios and criteria from the September 18 outer-transition study.

For each case, give a fresh independent host the current stage prompt from
`shiploop_navigator_v3_prompts.prompt(stage)`, the environment-lifecycle reference
and relevant migration guidance, plus the case input. Ask for the next action,
remaining ordered work, required evidence, recovery and Improve scope. Permit
reads and saving the answer only; do not execute proposed effects or callbacks.
An independent evaluator should receive the case and shared ShipLoop stage/Improve
facts, but not intended fixes or a preferred answer. Evaluate the criteria against
actual decisions; matching a phrase is not proof.

Supply only the current producer prompt in these cases. Do not append the future
Improve handoff: it states that the producer has already returned, which changes
the exercise's current action. An Improve-specific trial needs its own explicitly
pending-child scenario and evidence; it is a separate experiment.

Preserve failures and judge disagreements. In particular, local-only deployment
N/A must not remove current local candidate/consumer evidence checks, and a saved
target version is not a write-time conditional guard. Distinguish planning from
execution and request acceptance from terminal completion. A hypothetical release
runner or local operation ID supplies no provider guarantee.

Keep raw answers, evaluations and runtime evidence outside the product checkout.
The deterministic v3 guidance suite checks reference routing through cold producer
and Improve recovery; this separate manual/live evaluation checks interpretation.
Neither establishes live provider idempotency, concurrency or production behavior.
