# ShipLoop navigator state

```shiploop-state
{
  "accepted": {
    "nav-218ea3a3c7654e3391a34c3c4d1d5e50": {
      "evidence_refs": [
        "../evidence/seed-claims.md"
      ],
      "outcome": "done",
      "summary": "SYNTHETIC fixture predecessor for discovery; no producer execution, semantic review, or Improve cycle occurred."
    },
    "nav-3580c2661d5340ec8eab454a829d614b": {
      "evidence_refs": [
        "../evidence/seed-claims.md"
      ],
      "outcome": "done",
      "summary": "SYNTHETIC fixture predecessor for research; no producer execution, semantic review, or Improve cycle occurred."
    },
    "nav-3e31caf977c64fcf8a39f607cb43d1a7": {
      "evidence_refs": [
        "../evidence/seed-claims.md"
      ],
      "outcome": "done",
      "summary": "SYNTHETIC fixture predecessor for prepare; no producer execution, semantic review, or Improve cycle occurred."
    },
    "nav-53d803a65fbc479583a3640afcddbfd1": {
      "evidence_refs": [
        "../evidence/seed-claims.md"
      ],
      "outcome": "done",
      "summary": "SYNTHETIC fixture predecessor for spec; no producer execution, semantic review, or Improve cycle occurred."
    },
    "nav-76ae377e5608481196c2c088c874a742": {
      "evidence_refs": [
        "../evidence/seed-claims.md"
      ],
      "outcome": "done",
      "summary": "SYNTHETIC fixture predecessor for select-work; no producer execution, semantic review, or Improve cycle occurred."
    },
    "nav-8bb0f96f6f8a48dcb1693830b724b251": {
      "evidence_refs": [
        "../evidence/seed-claims.md"
      ],
      "outcome": "done",
      "summary": "SYNTHETIC fixture predecessor for test-strategy; no producer execution, semantic review, or Improve cycle occurred."
    },
    "nav-a7bcdb7888204a49b7e49fc4134f7e8d": {
      "evidence_refs": [
        "../evidence/seed-claims.md"
      ],
      "outcome": "done",
      "summary": "SYNTHETIC fixture predecessor for intake; no producer execution, semantic review, or Improve cycle occurred."
    },
    "nav-bec327c2f88c48419ac498e62bd15d2f": {
      "evidence_refs": [
        "<study>/cold-independent/run/notes/w1-step-plan.md",
        "<study>/cold-independent/product/README.md#Field Notes",
        "<study>/cold-independent/product/docs/design.md#UI identity",
        "<study>/cold-independent/product/docs/platform.md#Deployment target",
        "<study>/cold-independent/product/docs/api.md#Existing API",
        "<study>/cold-independent/product/scripts/probe_environment.py"
      ],
      "outcome": "done",
      "summary": "Revised W1 bounded remote-export-status plan: preserves the Field Notes UI and current v2 constraints; requires an authoritative account-scoped collection source plus documented list/operation/job response contracts before dependent API behavior or fakes; keeps W2 draft persistence out of scope and records planned/unrun checks."
    },
    "nav-f68c2df816ca4bf8baba035f0e4364b1": {
      "evidence_refs": [
        "../evidence/seed-claims.md"
      ],
      "outcome": "done",
      "summary": "SYNTHETIC fixture predecessor for plan; no producer execution, semantic review, or Improve cycle occurred.",
      "work_items": [
        {
          "context": "Required retained sources: product/docs/design.md#UI identity and #Previous environment assumption; product/docs/platform.md; product/docs/api.md; product/scripts/probe_environment.py. UI premise: account selector, note list, stable textarea, controls, focus/touch/narrow layout and visual identity from design.md. Historical-only readiness: fieldnotes-embedded-v1 previously allowed account-scoped persistent browser storage; this is not current availability. Current controlled probe reports fieldnotes-embedded-v2 with client_persistent_storage unavailable and draft_api false. Plan the listed checks, including rerunning the current probe, source/behavior tests appropriate to the selected item, and an explicit unavailable-boundary result. Treat the historical v1 receipt and current v2 probe as distinct evidence; do not treat either as a completed producer or Improve review. Selected scope is remote export status using GET/POST /api/exports, GET /api/operations/:clientOperationId and GET /api/exports/:jobId from api.md; it has no persistent-draft dependency. Pending blocked draft persistence remains separate future work.",
          "id": "W1",
          "title": "Add remote export status using the existing API"
        },
        {
          "context": "Required retained sources: product/docs/design.md#UI identity and #Previous environment assumption; product/docs/platform.md; product/docs/api.md; product/scripts/probe_environment.py. UI premise: account selector, note list, stable textarea, controls, focus/touch/narrow layout and visual identity from design.md. Historical-only readiness: fieldnotes-embedded-v1 previously allowed account-scoped persistent browser storage; this is not current availability. Current controlled probe reports fieldnotes-embedded-v2 with client_persistent_storage unavailable and draft_api false. Plan the listed checks, including rerunning the current probe, source/behavior tests appropriate to the selected item, and an explicit unavailable-boundary result. Treat the historical v1 receipt and current v2 probe as distinct evidence; do not treat either as a completed producer or Improve review. This is intentionally pending future work, not part of W1.",
          "id": "W2",
          "title": "Resolve blocked persistent account-scoped drafts after storage availability is established"
        }
      ]
    }
  },
  "action": null,
  "active_improve": null,
  "bound_plan": "",
  "completed_work_items": [],
  "execution_mode": "navigator",
  "history": [
    {
      "action": "nav-a7bcdb7888204a49b7e49fc4134f7e8d",
      "outcome": "done",
      "stage": "intake",
      "summary": "SYNTHETIC fixture predecessor for intake; no producer execution, semantic review, or Improve cycle occurred.",
      "workitem": null
    },
    {
      "action": "nav-218ea3a3c7654e3391a34c3c4d1d5e50",
      "outcome": "done",
      "stage": "discovery",
      "summary": "SYNTHETIC fixture predecessor for discovery; no producer execution, semantic review, or Improve cycle occurred.",
      "workitem": null
    },
    {
      "action": "nav-3580c2661d5340ec8eab454a829d614b",
      "outcome": "done",
      "stage": "research",
      "summary": "SYNTHETIC fixture predecessor for research; no producer execution, semantic review, or Improve cycle occurred.",
      "workitem": null
    },
    {
      "action": "nav-53d803a65fbc479583a3640afcddbfd1",
      "outcome": "done",
      "stage": "spec",
      "summary": "SYNTHETIC fixture predecessor for spec; no producer execution, semantic review, or Improve cycle occurred.",
      "workitem": null
    },
    {
      "action": "nav-8bb0f96f6f8a48dcb1693830b724b251",
      "outcome": "done",
      "stage": "test-strategy",
      "summary": "SYNTHETIC fixture predecessor for test-strategy; no producer execution, semantic review, or Improve cycle occurred.",
      "workitem": null
    },
    {
      "action": "nav-f68c2df816ca4bf8baba035f0e4364b1",
      "outcome": "done",
      "stage": "plan",
      "summary": "SYNTHETIC fixture predecessor for plan; no producer execution, semantic review, or Improve cycle occurred.",
      "workitem": null
    },
    {
      "action": "nav-3e31caf977c64fcf8a39f607cb43d1a7",
      "outcome": "done",
      "stage": "prepare",
      "summary": "SYNTHETIC fixture predecessor for prepare; no producer execution, semantic review, or Improve cycle occurred.",
      "workitem": null
    },
    {
      "action": "nav-76ae377e5608481196c2c088c874a742",
      "outcome": "done",
      "stage": "select-work",
      "summary": "SYNTHETIC fixture predecessor for select-work; no producer execution, semantic review, or Improve cycle occurred.",
      "workitem": "W1"
    },
    {
      "action": "nav-bec327c2f88c48419ac498e62bd15d2f",
      "outcome": "done",
      "stage": "step-plan",
      "summary": "Revised W1 bounded remote-export-status plan: preserves the Field Notes UI and current v2 constraints; requires an authoritative account-scoped collection source plus documented list/operation/job response contracts before dependent API behavior or fakes; keeps W2 draft persistence out of scope and records planned/unrun checks.",
      "workitem": "W1"
    }
  ],
  "improve_results": {
    "nav-218ea3a3c7654e3391a34c3c4d1d5e50": {
      "claim": "No actual selected Improve runtime was invoked or imported.",
      "kind": "synthetic-fixture-predecessor",
      "seed_result": {
        "evidence_refs": [
          "../evidence/seed-claims.md"
        ],
        "outcome": "done",
        "summary": "SYNTHETIC fixture predecessor for discovery; no producer execution, semantic review, or Improve cycle occurred."
      },
      "stage": "discovery"
    },
    "nav-3580c2661d5340ec8eab454a829d614b": {
      "claim": "No actual selected Improve runtime was invoked or imported.",
      "kind": "synthetic-fixture-predecessor",
      "seed_result": {
        "evidence_refs": [
          "../evidence/seed-claims.md"
        ],
        "outcome": "done",
        "summary": "SYNTHETIC fixture predecessor for research; no producer execution, semantic review, or Improve cycle occurred."
      },
      "stage": "research"
    },
    "nav-3e31caf977c64fcf8a39f607cb43d1a7": {
      "claim": "No actual selected Improve runtime was invoked or imported.",
      "kind": "synthetic-fixture-predecessor",
      "seed_result": {
        "evidence_refs": [
          "../evidence/seed-claims.md"
        ],
        "outcome": "done",
        "summary": "SYNTHETIC fixture predecessor for prepare; no producer execution, semantic review, or Improve cycle occurred."
      },
      "stage": "prepare"
    },
    "nav-53d803a65fbc479583a3640afcddbfd1": {
      "claim": "No actual selected Improve runtime was invoked or imported.",
      "kind": "synthetic-fixture-predecessor",
      "seed_result": {
        "evidence_refs": [
          "../evidence/seed-claims.md"
        ],
        "outcome": "done",
        "summary": "SYNTHETIC fixture predecessor for spec; no producer execution, semantic review, or Improve cycle occurred."
      },
      "stage": "spec"
    },
    "nav-76ae377e5608481196c2c088c874a742": {
      "claim": "No actual selected Improve runtime was invoked or imported.",
      "kind": "synthetic-fixture-predecessor",
      "seed_result": {
        "evidence_refs": [
          "../evidence/seed-claims.md"
        ],
        "outcome": "done",
        "summary": "SYNTHETIC fixture predecessor for select-work; no producer execution, semantic review, or Improve cycle occurred."
      },
      "stage": "select-work"
    },
    "nav-8bb0f96f6f8a48dcb1693830b724b251": {
      "claim": "No actual selected Improve runtime was invoked or imported.",
      "kind": "synthetic-fixture-predecessor",
      "seed_result": {
        "evidence_refs": [
          "../evidence/seed-claims.md"
        ],
        "outcome": "done",
        "summary": "SYNTHETIC fixture predecessor for test-strategy; no producer execution, semantic review, or Improve cycle occurred."
      },
      "stage": "test-strategy"
    },
    "nav-a7bcdb7888204a49b7e49fc4134f7e8d": {
      "claim": "No actual selected Improve runtime was invoked or imported.",
      "kind": "synthetic-fixture-predecessor",
      "seed_result": {
        "evidence_refs": [
          "../evidence/seed-claims.md"
        ],
        "outcome": "done",
        "summary": "SYNTHETIC fixture predecessor for intake; no producer execution, semantic review, or Improve cycle occurred."
      },
      "stage": "intake"
    },
    "nav-bec327c2f88c48419ac498e62bd15d2f": {
      "action_id": "nav-bec327c2f88c48419ac498e62bd15d2f",
      "binding_id": "nav-807dba2edaea4c7d86a59fc53090b1a3/nav-bec327c2f88c48419ac498e62bd15d2f",
      "evidence": [
        {
          "archive": "improve/nav-bec327c2f88c48419ac498e62bd15d2f/evidence/01-review-three.md",
          "sha256": "4ddcb99ffba5ef22569b79e29746a0e5c5209b5d38a5888e1af3c49a071c4ae1",
          "source": ".shiploop-improve/nav-807dba2edaea4c7d86a59fc53090b1a3/nav-bec327c2f88c48419ac498e62bd15d2f/reviews/review-three.md"
        },
        {
          "archive": "improve/nav-bec327c2f88c48419ac498e62bd15d2f/evidence/02-review-four.md",
          "sha256": "ac8ad967cba8d5c7f2c43ecfadf2e78cd6a4afd7f9a1dd35ab356cd32dcee255",
          "source": ".shiploop-improve/nav-807dba2edaea4c7d86a59fc53090b1a3/nav-bec327c2f88c48419ac498e62bd15d2f/reviews/review-four.md"
        },
        {
          "archive": "improve/nav-bec327c2f88c48419ac498e62bd15d2f/evidence/03-checks.md",
          "sha256": "536da483763350775acbd2635118390de44e1c02694335934c936c3c17869af5",
          "source": ".shiploop-improve/nav-807dba2edaea4c7d86a59fc53090b1a3/nav-bec327c2f88c48419ac498e62bd15d2f/reviews/checks.md"
        }
      ],
      "identities": {
        "context_sha256": "fb22906a597c458c1c27751ef31920158a1f095e6680b5126f0ba6a43e74dce7",
        "evidence_sha256": {
          ".shiploop-improve/nav-807dba2edaea4c7d86a59fc53090b1a3/nav-bec327c2f88c48419ac498e62bd15d2f/reviews/checks.md": "536da483763350775acbd2635118390de44e1c02694335934c936c3c17869af5",
          ".shiploop-improve/nav-807dba2edaea4c7d86a59fc53090b1a3/nav-bec327c2f88c48419ac498e62bd15d2f/reviews/review-four.md": "ac8ad967cba8d5c7f2c43ecfadf2e78cd6a4afd7f9a1dd35ab356cd32dcee255",
          ".shiploop-improve/nav-807dba2edaea4c7d86a59fc53090b1a3/nav-bec327c2f88c48419ac498e62bd15d2f/reviews/review-three.md": "4ddcb99ffba5ef22569b79e29746a0e5c5209b5d38a5888e1af3c49a071c4ae1"
        },
        "last_report_sha256": "16d66301d89824d99ad13b690f97ec2888e83407c1407301e9804fddc847cfa0",
        "terminal_packet_sha256": "96d7d2e96258c61755bcad5fbb1781af1d91124529ec7bf48166ce75897b8cca"
      },
      "receipt": {
        "check_refs": [
          ".shiploop-improve/nav-807dba2edaea4c7d86a59fc53090b1a3/nav-bec327c2f88c48419ac498e62bd15d2f/reviews/checks.md"
        ],
        "final_result": {
          "evidence_refs": [
            "<study>/cold-independent/run/notes/w1-step-plan.md",
            "<study>/cold-independent/product/README.md#Field Notes",
            "<study>/cold-independent/product/docs/design.md#UI identity",
            "<study>/cold-independent/product/docs/platform.md#Deployment target",
            "<study>/cold-independent/product/docs/api.md#Existing API",
            "<study>/cold-independent/product/scripts/probe_environment.py"
          ],
          "outcome": "done",
          "summary": "Revised W1 bounded remote-export-status plan: preserves the Field Notes UI and current v2 constraints; requires an authoritative account-scoped collection source plus documented list/operation/job response contracts before dependent API behavior or fakes; keeps W2 draft persistence out of scope and records planned/unrun checks."
        },
        "lessons": "For W1, an authoritative account-scoped collection source and documented list/operation/job response shapes must exist before fake API paths can be treated as evidence. Keep missing integration contracts separate from missing local-harness coverage. This fixture is a Git archive without history, and the two qualifying reviews are self-review evidence.",
        "review_refs": [
          ".shiploop-improve/nav-807dba2edaea4c7d86a59fc53090b1a3/nav-bec327c2f88c48419ac498e62bd15d2f/reviews/review-three.md",
          ".shiploop-improve/nav-807dba2edaea4c7d86a59fc53090b1a3/nav-bec327c2f88c48419ac498e62bd15d2f/reviews/review-four.md"
        ],
        "summary": "Actual selected Improve completed four distinct W1 step-plan review cycles: two material plan corrections followed by two consecutive qualifying no-change reviews. The revised plan keeps Field Notes and the W1/W2 boundary intact, makes the authoritative account-scoped collection source and list/operation/job response contracts explicit prerequisites for dependent API behavior and fakes, and records planned/unrun checks honestly. The original producer output was preserved."
      },
      "runtime_phase": "complete",
      "seed_result": {
        "evidence_refs": [
          "<study>/cold-independent/run/notes/w1-step-plan.md",
          "<study>/cold-independent/product/README.md#Field Notes",
          "<study>/cold-independent/product/docs/design.md#UI identity",
          "<study>/cold-independent/product/docs/platform.md#Deployment target",
          "<study>/cold-independent/product/docs/api.md#Existing API",
          "<study>/cold-independent/product/scripts/probe_environment.py"
        ],
        "outcome": "done",
        "summary": "Recorded W1's bounded remote-export-status plan, current v2 probe/hash and syntax-baseline evidence. The plan preserves the existing Field Notes UI, uses only the documented same-origin API flow, and retains the undocumented collectionId source as an explicit pre-implementation dependency; draft persistence stays outside W1."
      },
      "skill": {
        "runtime_card": "<study>/frozen/improve/runtime/until-loop/ADAPTER.md",
        "runtime_cli": "<study>/frozen/improve/runtime/until-loop/scripts/until_loop_ephemeral.py",
        "runtime_version": "0.4.0-rc.2",
        "skill_card": "<study>/frozen/improve/SKILL.md",
        "skill_version": "0.2.0-rc.1"
      },
      "stage": "step-plan",
      "stale_check_note": "This import records a host-preserved structurally valid terminal Until Loop packet and current declared local evidence. It does not prove the packet was issued by the runtime, review or check claims, candidate scope, semantic Improve convergence, or future freshness; those remain the selected Improve skill and parent action's responsibility.",
      "submission": {
        "check_refs": [
          "<study>/cold-independent/product/.shiploop-improve/nav-807dba2edaea4c7d86a59fc53090b1a3/nav-bec327c2f88c48419ac498e62bd15d2f/reviews/checks.md"
        ],
        "final_result": {
          "evidence_refs": [
            "<study>/cold-independent/run/notes/w1-step-plan.md",
            "<study>/cold-independent/product/README.md#Field Notes",
            "<study>/cold-independent/product/docs/design.md#UI identity",
            "<study>/cold-independent/product/docs/platform.md#Deployment target",
            "<study>/cold-independent/product/docs/api.md#Existing API",
            "<study>/cold-independent/product/scripts/probe_environment.py"
          ],
          "outcome": "done",
          "summary": "Revised W1 bounded remote-export-status plan: preserves the Field Notes UI and current v2 constraints; requires an authoritative account-scoped collection source plus documented list/operation/job response contracts before dependent API behavior or fakes; keeps W2 draft persistence out of scope and records planned/unrun checks."
        },
        "lessons": "For W1, an authoritative account-scoped collection source and documented list/operation/job response shapes must exist before fake API paths can be treated as evidence. Keep missing integration contracts separate from missing local-harness coverage. This fixture is a Git archive without history, and the two qualifying reviews are self-review evidence.",
        "review_refs": [
          "<study>/cold-independent/product/.shiploop-improve/nav-807dba2edaea4c7d86a59fc53090b1a3/nav-bec327c2f88c48419ac498e62bd15d2f/reviews/review-three.md",
          "<study>/cold-independent/product/.shiploop-improve/nav-807dba2edaea4c7d86a59fc53090b1a3/nav-bec327c2f88c48419ac498e62bd15d2f/reviews/review-four.md"
        ],
        "summary": "Actual selected Improve completed four distinct W1 step-plan review cycles: two material plan corrections followed by two consecutive qualifying no-change reviews. The revised plan keeps Field Notes and the W1/W2 boundary intact, makes the authoritative account-scoped collection source and list/operation/job response contracts explicit prerequisites for dependent API behavior and fakes, and records planned/unrun checks honestly. The original producer output was preserved."
      },
      "version": 1,
      "workspace": "<study>/cold-independent/product"
    },
    "nav-f68c2df816ca4bf8baba035f0e4364b1": {
      "claim": "No actual selected Improve runtime was invoked or imported.",
      "kind": "synthetic-fixture-predecessor",
      "seed_result": {
        "evidence_refs": [
          "../evidence/seed-claims.md"
        ],
        "outcome": "done",
        "summary": "SYNTHETIC fixture predecessor for plan; no producer execution, semantic review, or Improve cycle occurred.",
        "work_items": [
          {
            "context": "Required retained sources: product/docs/design.md#UI identity and #Previous environment assumption; product/docs/platform.md; product/docs/api.md; product/scripts/probe_environment.py. UI premise: account selector, note list, stable textarea, controls, focus/touch/narrow layout and visual identity from design.md. Historical-only readiness: fieldnotes-embedded-v1 previously allowed account-scoped persistent browser storage; this is not current availability. Current controlled probe reports fieldnotes-embedded-v2 with client_persistent_storage unavailable and draft_api false. Plan the listed checks, including rerunning the current probe, source/behavior tests appropriate to the selected item, and an explicit unavailable-boundary result. Treat the historical v1 receipt and current v2 probe as distinct evidence; do not treat either as a completed producer or Improve review. Selected scope is remote export status using GET/POST /api/exports, GET /api/operations/:clientOperationId and GET /api/exports/:jobId from api.md; it has no persistent-draft dependency. Pending blocked draft persistence remains separate future work.",
            "id": "W1",
            "title": "Add remote export status using the existing API"
          },
          {
            "context": "Required retained sources: product/docs/design.md#UI identity and #Previous environment assumption; product/docs/platform.md; product/docs/api.md; product/scripts/probe_environment.py. UI premise: account selector, note list, stable textarea, controls, focus/touch/narrow layout and visual identity from design.md. Historical-only readiness: fieldnotes-embedded-v1 previously allowed account-scoped persistent browser storage; this is not current availability. Current controlled probe reports fieldnotes-embedded-v2 with client_persistent_storage unavailable and draft_api false. Plan the listed checks, including rerunning the current probe, source/behavior tests appropriate to the selected item, and an explicit unavailable-boundary result. Treat the historical v1 receipt and current v2 probe as distinct evidence; do not treat either as a completed producer or Improve review. This is intentionally pending future work, not part of W1.",
            "id": "W2",
            "title": "Resolve blocked persistent account-scoped drafts after storage availability is established"
          }
        ]
      },
      "stage": "plan"
    }
  },
  "improve_skill": "<study>/frozen/improve/SKILL.md",
  "inner_loops": {
    "W1": {
      "action": {
        "id": "nav-ace188775d224fdda299d583b2e9521e",
        "stage": "test-spec"
      },
      "stage": "test-spec"
    }
  },
  "navigator_protocol_version": 3,
  "prompt": "Bounded cold fixture: evaluate the selected remote export status work item from the rendered step-plan packet.",
  "repo": "<study>/cold-independent/product",
  "revision": 19,
  "run_id": "nav-807dba2edaea4c7d86a59fc53090b1a3",
  "stage": "inner-loop",
  "status": "active",
  "version": 3,
  "work_index": 0,
  "work_items": [
    {
      "context": "Required retained sources: product/docs/design.md#UI identity and #Previous environment assumption; product/docs/platform.md; product/docs/api.md; product/scripts/probe_environment.py. UI premise: account selector, note list, stable textarea, controls, focus/touch/narrow layout and visual identity from design.md. Historical-only readiness: fieldnotes-embedded-v1 previously allowed account-scoped persistent browser storage; this is not current availability. Current controlled probe reports fieldnotes-embedded-v2 with client_persistent_storage unavailable and draft_api false. Plan the listed checks, including rerunning the current probe, source/behavior tests appropriate to the selected item, and an explicit unavailable-boundary result. Treat the historical v1 receipt and current v2 probe as distinct evidence; do not treat either as a completed producer or Improve review. Selected scope is remote export status using GET/POST /api/exports, GET /api/operations/:clientOperationId and GET /api/exports/:jobId from api.md; it has no persistent-draft dependency. Pending blocked draft persistence remains separate future work.",
      "id": "W1",
      "title": "Add remote export status using the existing API"
    },
    {
      "context": "Required retained sources: product/docs/design.md#UI identity and #Previous environment assumption; product/docs/platform.md; product/docs/api.md; product/scripts/probe_environment.py. UI premise: account selector, note list, stable textarea, controls, focus/touch/narrow layout and visual identity from design.md. Historical-only readiness: fieldnotes-embedded-v1 previously allowed account-scoped persistent browser storage; this is not current availability. Current controlled probe reports fieldnotes-embedded-v2 with client_persistent_storage unavailable and draft_api false. Plan the listed checks, including rerunning the current probe, source/behavior tests appropriate to the selected item, and an explicit unavailable-boundary result. Treat the historical v1 receipt and current v2 probe as distinct evidence; do not treat either as a completed producer or Improve review. This is intentionally pending future work, not part of W1.",
      "id": "W2",
      "title": "Resolve blocked persistent account-scoped drafts after storage availability is established"
    }
  ]
}
```
