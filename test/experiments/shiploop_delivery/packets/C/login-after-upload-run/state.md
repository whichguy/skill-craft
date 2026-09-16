# ShipLoop navigator state

```shiploop-state
{
  "accepted": {
    "nav-0083ce2f4d3941fdb3fb46d36167d2aa": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-1406afd29e064c3392506f21d34ef8a5": {
      "delivery_assessment": {
        "contract_anchor": "nav-73d7385722024790a9c4f73058883826",
        "kind": "observation",
        "observations": [
          {
            "candidate": "candidate-v1",
            "evidence_refs": [
              "synthetic-evidence/pre-drag.md"
            ],
            "obligation_id": "pre-drag",
            "status": "passed",
            "target": "synthetic-private-head"
          }
        ]
      },
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-16112a58686b457a9634d71cf5416ef1": {
      "delivery_assessment": {
        "contract_anchor": "nav-73d7385722024790a9c4f73058883826",
        "kind": "observation",
        "observations": [
          {
            "candidate": "candidate-v1",
            "evidence_refs": [
              "synthetic-evidence/update-effect.md"
            ],
            "obligation_id": "update-effect",
            "status": "passed",
            "target": "synthetic-private-head"
          },
          {
            "candidate": "candidate-v1",
            "evidence_refs": [
              "synthetic-evidence/update-identity.md"
            ],
            "obligation_id": "update-identity",
            "status": "passed",
            "target": "synthetic-private-head"
          }
        ]
      },
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-213db20a5d4043c4aa7ff188077e67ec": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-21ab7151452c4e94ac540dffacf6cf6f": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-2c7472fb0c634098be6b8605e83e9765": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-59fd590d2f804cdd9bced47b654d2315": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-5d9aaaf7761145bdbc38c7d21e878761": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-6e6178d0c6e149e0883dfc438980e7b3": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-73d7385722024790a9c4f73058883826": {
      "delivery_assessment": {
        "contract": {
          "authority": {
            "approval_ref": "Synthetic fixture policy permits only this private target update.",
            "kind": "repo-policy",
            "operation": "sync the approved synthetic private source target",
            "reference": "SYNTHETIC-SHIPLOOP.md#private-head-update",
            "status": "approved",
            "target": "synthetic-private-head"
          },
          "basis": "The synthetic feature must be usable by its declared private player.",
          "behavior": "a drag visibly follows the selected piece",
          "candidate": "candidate-v1",
          "consumer": "synthetic private game page",
          "exclusions": [
            "public access",
            "versioned deployment"
          ],
          "necessity": "required",
          "obligations": [
            {
              "consumer": "synthetic private game page",
              "expected": "existing move checks pass for candidate-v1",
              "id": "pre-drag",
              "kind": "pre-update",
              "phase": "system-test",
              "required": true,
              "target": "synthetic-private-head"
            },
            {
              "consumer": "synthetic private game page",
              "expected": "the approved synthetic source update is recorded",
              "id": "update-effect",
              "kind": "effect",
              "phase": "release",
              "required": true,
              "target": "synthetic-private-head"
            },
            {
              "consumer": "synthetic private game page",
              "expected": "the synthetic target identifies candidate-v1",
              "id": "update-identity",
              "kind": "identity",
              "phase": "release",
              "required": true,
              "target": "synthetic-private-head"
            },
            {
              "consumer": "synthetic private game page",
              "expected": "a dragged piece visibly follows the pointer",
              "id": "visual-drag",
              "kind": "behavior",
              "phase": "release-verify",
              "required": true,
              "target": "synthetic-private-head"
            }
          ],
          "operation": "sync the approved synthetic private source target",
          "target": "synthetic-private-head"
        },
        "kind": "contract"
      },
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-76e4263a87ee4e63aec99cc010d2801f": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-79c7c51a5acd40bb87e057653a325daa": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-7d060149487647219687f732c7bb45fb": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-81abea0a5b4f4dea9fee4944c9422b17": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-8db9cd2258404d9c95dcbc8523cc3897": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-8f9740570cca4591bf7733a400d1a857": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-9d72b226213245bc92dbf22c326b9039": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-a637bc47065d44a49926bfc218e9f5e7": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-e500d8f696d743858503223e221fe4f6": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-e55149632e554a2c92e2174b6ac35fef": {
      "delivery_assessment": {
        "contract_anchor": "nav-73d7385722024790a9c4f73058883826",
        "kind": "observation",
        "observations": [
          {
            "candidate": "candidate-v1",
            "evidence_refs": [
              "synthetic-evidence/visual-drag.md"
            ],
            "obligation_id": "visual-drag",
            "status": "blocked",
            "target": "synthetic-private-head"
          }
        ]
      },
      "evidence_refs": [],
      "outcome": "blocked",
      "summary": "Synthetic private-page login blocks the visual drag check; the synthetic effect and identity records are retained."
    },
    "nav-ed2f28926f6942438e512f1a2feec7ee": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-ef93abe1d9214423a7bdcda34008cbb1": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-f223e0a29479482497f2c51076a9a2c5": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-f637bb740ae74480b40e2050f03c3fff": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    }
  },
  "action": {
    "id": "nav-24cd8637c9a641a09490a6827f070bab",
    "stage": "release-verify"
  },
  "bound_plan": "",
  "completed_work_items": [
    "W1"
  ],
  "delivery_contract_version": 1,
  "execution_mode": "navigator",
  "history": [
    {
      "action": "nav-e500d8f696d743858503223e221fe4f6",
      "outcome": "done",
      "stage": "intake",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-6e6178d0c6e149e0883dfc438980e7b3",
      "outcome": "done",
      "stage": "discovery",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-a637bc47065d44a49926bfc218e9f5e7",
      "outcome": "done",
      "stage": "research",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-9d72b226213245bc92dbf22c326b9039",
      "outcome": "done",
      "stage": "research-improve",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-21ab7151452c4e94ac540dffacf6cf6f",
      "outcome": "done",
      "stage": "spec",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-0083ce2f4d3941fdb3fb46d36167d2aa",
      "outcome": "done",
      "stage": "spec-improve",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-81abea0a5b4f4dea9fee4944c9422b17",
      "outcome": "done",
      "stage": "test-strategy",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-59fd590d2f804cdd9bced47b654d2315",
      "outcome": "done",
      "stage": "plan",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-73d7385722024790a9c4f73058883826",
      "outcome": "done",
      "stage": "plan-improve",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-7d060149487647219687f732c7bb45fb",
      "outcome": "done",
      "stage": "step-plan",
      "summary": "Synthetic local navigator result.",
      "workitem": "W1"
    },
    {
      "action": "nav-76e4263a87ee4e63aec99cc010d2801f",
      "outcome": "done",
      "stage": "step-plan-improve",
      "summary": "Synthetic local navigator result.",
      "workitem": "W1"
    },
    {
      "action": "nav-2c7472fb0c634098be6b8605e83e9765",
      "outcome": "done",
      "stage": "implement",
      "summary": "Synthetic local navigator result.",
      "workitem": "W1"
    },
    {
      "action": "nav-213db20a5d4043c4aa7ff188077e67ec",
      "outcome": "done",
      "stage": "test-refine",
      "summary": "Synthetic local navigator result.",
      "workitem": "W1"
    },
    {
      "action": "nav-f637bb740ae74480b40e2050f03c3fff",
      "outcome": "done",
      "stage": "test-author",
      "summary": "Synthetic local navigator result.",
      "workitem": "W1"
    },
    {
      "action": "nav-ed2f28926f6942438e512f1a2feec7ee",
      "outcome": "done",
      "stage": "document",
      "summary": "Synthetic local navigator result.",
      "workitem": "W1"
    },
    {
      "action": "nav-8f9740570cca4591bf7733a400d1a857",
      "outcome": "done",
      "stage": "verify",
      "summary": "Synthetic local navigator result.",
      "workitem": "W1"
    },
    {
      "action": "nav-f223e0a29479482497f2c51076a9a2c5",
      "outcome": "done",
      "stage": "product-improve",
      "summary": "Synthetic local navigator result.",
      "workitem": "W1"
    },
    {
      "action": "nav-79c7c51a5acd40bb87e057653a325daa",
      "outcome": "done",
      "stage": "integrate",
      "summary": "Synthetic local navigator result.",
      "workitem": "W1"
    },
    {
      "action": "nav-5d9aaaf7761145bdbc38c7d21e878761",
      "outcome": "done",
      "stage": "carry-forward",
      "summary": "Synthetic local navigator result.",
      "workitem": "W1"
    },
    {
      "action": "nav-1406afd29e064c3392506f21d34ef8a5",
      "outcome": "done",
      "stage": "system-test",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-ef93abe1d9214423a7bdcda34008cbb1",
      "outcome": "done",
      "stage": "outer-improve",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-8db9cd2258404d9c95dcbc8523cc3897",
      "outcome": "done",
      "stage": "release-plan",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-16112a58686b457a9634d71cf5416ef1",
      "outcome": "done",
      "stage": "release",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-e55149632e554a2c92e2174b6ac35fef",
      "outcome": "blocked",
      "stage": "release-verify",
      "summary": "Synthetic private-page login blocks the visual drag check; the synthetic effect and identity records are retained.",
      "workitem": null
    }
  ],
  "inner_loops": {
    "W1": {
      "action": null,
      "stage": "done"
    }
  },
  "navigator_protocol_version": 2,
  "prompt": "Synthetic local guarded recovery fixture only. No product, credential, network, consumer, target, or deployment exists. It models an unchanged candidate with a later login boundary. Do not execute an operation from this fixture.",
  "repo": "synthetic://shiploop-consumer-delivery/no-live-target",
  "revision": 25,
  "run_id": "nav-8ed8047d3bb943ce8f71a3b03f1410e2",
  "stage": "release-verify",
  "status": "active",
  "version": 3,
  "work_index": 1,
  "work_items": [
    {
      "id": "W1",
      "title": "Synthetic local guarded recovery fixture only. No product, credential, network, consumer, target, or deployment exists. It models an unchanged candidate with a "
    }
  ]
}
```
