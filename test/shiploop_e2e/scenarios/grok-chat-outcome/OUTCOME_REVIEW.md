# Independent Grok Bot outcome and coverage review

Keep this procedure, the reference archive and all review evidence on the operator side. The builder receives the literal [customer brief](BUILDER_PROMPT.md) and the attempt's authorized environment binding. The case supplies zero fixed checks. Fresh live discovery starts at **NOT_STARTED**. This report can describe one delivery. Its evaluator is **UNQUALIFIED** and generic ShipLoop improvement is **NOT_MEASURED**.

## Inspect customer journeys

Give one fresh independent Astra-high reviewer the sealed generation, relevant official Grok Bot references, actual observations, generated test sources and execution receipts. Record the explicit discovered Astra model, reasoning effort, default child controls, catalog and launch/exit receipts. The adapter authenticates these receipts and pins the exact output bytes. Each journey needs a product verdict and a separate account of test coverage.

| Journey ID | Independent product observation | Coverage questions where applicable |
| --- | --- | --- |
| `grok_bot_experience` | Compare observed collaboration, follow-up, steering, bots and roster navigation, reading, composition and contextual approvals with the archived Grok Bot behavior and design. | Which tests exercise customer tasks and reference fidelity? What are the limits of visual or interaction snapshots? |
| `setup` | Follow the rendered first-use flow and actual provider behavior, including useful recovery when prerequisites are missing or incorrect. | What runs with missing configuration, denied access, provider errors and corrected configuration? |
| `read_followup` | Compare a grounded answer and its follow-up in the rendered conversation with actual provider use and independently read synthetic records. | What asserts grounding, retained context, empty or error results and data access boundaries? |
| `approved_writes` | Observe exact create and update proposals, rejection and confirmation. Read records independently to verify effects. Each exact business create or update requires human confirmation. | What asserts rejection, revision, confirmed effects and protection against repetition, reload and cancellation? |
| `history_memory` | Return to named bots and conversations. Reuse instructions or tasks, correct and forget memory, then observe subsequent behavior and user/bot separation. | What asserts persistence after reload, removal, repeat behavior and isolation? |
| `background_recovery` | Leave during useful work, return, steer or cancel, and observe a recoverable interruption. Compare visible progress with native work and effects as relevant. | What asserts async completion, interruption, cancellation, duplicate suppression and recovery? |
| `responsive_keyboard` | Complete real tasks on desktop, at a narrow width and by keyboard. Observe navigation, focus, reading, composition, approval and recovery. | Which workflows actually run at narrow widths or with keyboard input? Do the assertions verify usable results? |

Assign product **PASS** when specific independent observations establish the journey, **FAIL** for a demonstrated unmet outcome and **UNKNOWN** when evidence is missing, ambiguous or blocked. A rendered proposal and a record readback establish different facts. A demonstrated product defect stays FAIL alongside passing app tests. A screenshot from an unrelated flow cannot establish a verdict. Choose relevant coverage axes for each journey and state material limits.

For coverage, identify each test or scenario and its actual assertion. Use app **NOT_RUN** when the seal establishes that a generated test belongs to this generation and no execution is established. When definition provenance is missing, describe the gap without claiming a generated test. Use **UNKNOWN** when execution, assertion, result or exact version cannot be established. App unit, integration, Salesforce-native, live provider, rendered UI and harness self-tests represent different layers. A mock provider result measures the mocked path. Harness and adapter banks measure the apparatus. Totals count cited journey findings and can repeat an execution across journeys. Coverage breadth is described by the asserted behaviors, environments and gaps.

## Seal the actual generation

The operator or adapter creates the immutable discovery JSON from the held generation's stable `retained.json`, deployed-source/deployment evidence, actual installed build and original observation receipts. Keep the adapter's other discovery fields. Pin the file as an evidence reference `{"path": "<canonical absolute file path>", "sha256": "<64 lowercase hex digits>"}`. Use its exact bytes for the review prompt, report and replay. Later settlement and retirement have separate receipts.

The discovery JSON supplies these evaluation fields.

| Field | Contents |
| --- | --- |
| `evaluation_generation` | `generation_id`, `build_sha256`, `source_sha256`, `deployment_ids`, `org_id`, `user_id`, `prefix`, `app_url`, `retained_state`. Use the exact retained attempt ID, the full installed build digest, the exact deployed source digest and ordered unique terminal deployment IDs. If several approved payloads contribute to the deployed app, use the independently verified component-to-payload manifest digest. Use `null` for unavailable digests, target strings or URL, and `[]` for unavailable deployment IDs. Use a verified HTTPS app URL without credentials, query or fragment. |
| `evaluation_routes` | The observed `browser`, `provider`, `native` and `records` artifacts as a mapping from route to evidence reference. Include those with OBSERVED receipts and omit unknown routes. Keep these independently produced artifacts outside builder output. Each route artifact can contain multiple specific trace events or a screenshot. |
| `evaluation_test_artifacts` | Optional array of `{artifact, tested_generation, layer, environment}` rows. Before sealing, register the exact definition reference for each verified generated test and the exact execution and assertion references for each verified terminal result. One artifact can support multiple claims where its located evidence establishes each claim. |
| `evaluation_reference_artifacts` | Optional array of `{label, artifact}` rows for retained official references, source and deployment manifests, screenshots and similar owner-facing evidence. |

Preserve the generated repository and test files along with this evidence. Verify each registered definition against the retained source of this attempt before sealing. Register an archived copy only after checking its exact bytes against that source. A path in a live builder tree does not establish provenance. Register harness-owned evidence under `harness_self_test`. For execution and assertion evidence, independently verify what ran against which exact source and deployment. For owner-facing material, use concise nonsecret labels and excerpts in the report itself. Use the exact evidence anchors for detailed inspection. Keep raw logs, tokens, session URLs, authentication material and unrelated private records out of the report.

## Produce the independent result

Write bare JSON as the independent session's actual final output. Use [evaluation.example.json](evaluation.example.json) for the complete all-UNKNOWN shape. Substitute the real discovery anchor in the review prompt. A complete report can have seven UNKNOWN outcomes with seven coverage-gap statements. The operator retains actual output bytes and the adapter checks the launch, catalog, exit and output receipts before scoring or rendering.

- Each `product` has `verdict`, `reason` and `observations`. A decisive observation is `{route, artifact, locator, proves}` and cites the exact reference from its sealed route. Explain what the located evidence establishes. PASS requires `browser` for all journeys, plus `provider` for setup, `provider` and `records` for reads, `records` for writes, and `native` for background recovery. FAIL requires a specific counterexample from at least one of the journey's listed routes. Decisive claims require a known build, deployed source, deployment, org, user and prefix.
- Each `coverage` has `tests` and nonempty `gaps`. Each test has `test_id`, `behavior`, `layer`, `environment`, `generated` (boolean), `status`, `tested_generation`, `test_definition`, `execution`, `assertion` and `limitations` (array of strings). Explain limits explicitly for mock and harness tests.
- A test evidence link is `{artifact, locator, proves}`. For `generated: true`, cite a `test_definition` artifact registered in the seal for the same generation, layer and environment. Use `null` when a definition is unavailable for other tests. Terminal PASS and FAIL require execution and assertion links whose artifacts are sealed for the same layer, environment and `tested_generation`. The identity in a sealed registration carries `generation_id`, `build_sha256`, `source_sha256` and `deployment_ids`. Use the seal's exact deployment IDs for hosted evidence and `[]` for local or mock evidence. NOT_RUN and UNKNOWN use `null` for the review's `tested_generation`, `execution` and `assertion`. Describe why execution is unproven in the gaps or limitations.
- Use layer `app_unit` for `local` or `mock`; `integration` for `local`, `mock` or `hosted`; `salesforce_native` for `mock` or `hosted`; `live_provider` and `rendered_ui` for `hosted`; and `harness_self_test` for `local` or `mock`. Pick the layer that actually ran.

| Locator | Example |
| --- | --- |
| JSON event or assertion | `{"kind":"json_pointer","pointer":"/events/5/assertion"}` uses a non-root RFC 6901 pointer. |
| UTF-8 text, JSONL or source line | `{"kind":"lines","start":14,"end":16}` uses inclusive one-based lines. |
| PNG region | `{"kind":"png_region","x":40,"y":30,"width":120,"height":80}` uses zero-based pixels within the image dimensions. |

The validator checks reference hashes, paths, locations and sealed provenance for generated definitions and terminal results. Semantic relevance remains the reviewer's judgment. For example, a mock of provider recovery can have a sealed integration execution result while the actual setup verdict remains UNKNOWN. Supply the observed browser and live provider evidence before awarding setup PASS.

## Validate and render from the checkout

After the adapter verifies the independent launch and output reference, call [the evaluation module](../../hosted_outcome/evaluation.py) from the repository root. Set `DISCOVERY` to the seal path, `DISCOVERY_SHA256` to its already verified digest, `REVIEW` to the actual independent output path, `REVIEW_SHA256` to its verified digest, `BUILDER_OUTPUT` to the exact runner output directory, and `REPORT_DIR` to an existing separate operator directory. Paths must be canonical and absolute.

```sh
PYTHONPATH=test/shiploop_e2e python3.15 -B - \
  "$DISCOVERY" "$DISCOVERY_SHA256" "$REVIEW" "$REVIEW_SHA256" "$BUILDER_OUTPUT" "$REPORT_DIR" <<'PY'
import json
import sys
from pathlib import Path
from hosted_outcome.evaluation import assess, render_html

discovery, digest, review, review_digest, builder, report = sys.argv[1:]
anchor = {"path": discovery, "sha256": digest}
routes = json.loads(Path(discovery).read_bytes())["evaluation_routes"]
summary = assess(review, anchor=anchor, routes=routes, builder_output=builder)
if summary["review_result"] != {"path": review, "sha256": review_digest}:
    raise SystemExit("Independent review output differs from its verified reference")
directory = Path(report)
for name, contents in (
    ("evaluation.json", json.dumps(summary, indent=2) + "\n"),
    ("evaluation.html", render_html(summary)),
):
    with (directory / name).open("x", encoding="utf-8") as stream:
        stream.write(contents)
PY
```

The HTML carries the app link when known and labels retained state as of sealing. It shows journey findings, coverage limits, identity, and links to the independent result and reference evidence. A report with zero observed journeys is titled **Grok Bot E2E effectiveness unmeasured**. Before launch, `render_html(unmeasured_summary(reason))` can produce a status artifact with no generation or review claim. Share local outputs if shared Run Review publication is unavailable. An evaluation artifact supplies no retirement authority.
