# ShipLoop navigator state

```shiploop-state
{
  "accepted": {
    "nav-0aa2a039d68b463e89ad6493af1c3676": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-0dbd72d1183640d2ad5c7a2788b8d8d2": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-1d7b75d1cda34ab88be98bfc40b00972": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-27b4a45e45da415cbf828fba21808ecf": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-3fa72e971aa1482284c4ef8a1dff6551": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-507e4c2054b04b2ea3bbbc5a69e0d079": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-598c6871f9ab4900b799c7fba8542518": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-5ec24dba11144690a4229b310a204dbd": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-616d86e27a974b8eb8f1e1bc689942cd": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-6f82c0d4330146e78002bd37f4e70e87": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-7ee92a63b8534dfe90680edcf97a1275": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-8b32f2c3834440819aeff43759cc76f7": {
      "delivery_assessment": {
        "contract_anchor": "nav-9f24f0dd56d045a3a6b69df6058ed71a",
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
    "nav-9b0dce36f7974b10b6fa27aeb079812e": {
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
          "candidate": "candidate-v2",
          "consumer": "synthetic private game page",
          "exclusions": [
            "public access",
            "versioned deployment"
          ],
          "necessity": "required",
          "obligations": [
            {
              "consumer": "synthetic private game page",
              "expected": "existing move checks pass for candidate-v2",
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
              "expected": "the synthetic target identifies candidate-v2",
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
        "correction": {
          "kind": "user-decision",
          "reference": "Synthetic fixture user selects candidate-v2 for the existing private delivery scope."
        },
        "kind": "contract",
        "supersedes": "nav-9f24f0dd56d045a3a6b69df6058ed71a"
      },
      "evidence_refs": [],
      "outcome": "blocked",
      "summary": "Synthetic candidate-v2 was declared after release planning; the current effectful action must remain blocked for a new planning run."
    },
    "nav-9f24f0dd56d045a3a6b69df6058ed71a": {
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
    "nav-a57ea5a438e949459a5b16434b29762b": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-a60cec38236f4b858a75376b203d6e87": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-bc6a14f78be049b3acafa90060dedaac": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-df1be4141e5a448a982e39dbcac1f1f8": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-e9025fbd0feb40a29687bd5443cb1e59": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-f37b12131837448eb89b1170e9b60275": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-f4a74e7fd32f4ad2b8ce29d1e20f0bf8": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-f57da3804ba74204b02cdb5e090fc1db": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    },
    "nav-f69f473ce027427bb9212e144b339b30": {
      "evidence_refs": [],
      "outcome": "done",
      "summary": "Synthetic local navigator result."
    }
  },
  "action": {
    "id": "nav-e147aeec1860436cb110c43e10654ad6",
    "stage": "release"
  },
  "bound_plan": "",
  "completed_work_items": [
    "W1"
  ],
  "delivery_contract_version": 1,
  "execution_mode": "navigator",
  "history": [
    {
      "action": "nav-3fa72e971aa1482284c4ef8a1dff6551",
      "outcome": "done",
      "stage": "intake",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-616d86e27a974b8eb8f1e1bc689942cd",
      "outcome": "done",
      "stage": "discovery",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-f57da3804ba74204b02cdb5e090fc1db",
      "outcome": "done",
      "stage": "research",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-a57ea5a438e949459a5b16434b29762b",
      "outcome": "done",
      "stage": "research-improve",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-df1be4141e5a448a982e39dbcac1f1f8",
      "outcome": "done",
      "stage": "spec",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-1d7b75d1cda34ab88be98bfc40b00972",
      "outcome": "done",
      "stage": "spec-improve",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-6f82c0d4330146e78002bd37f4e70e87",
      "outcome": "done",
      "stage": "test-strategy",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-7ee92a63b8534dfe90680edcf97a1275",
      "outcome": "done",
      "stage": "plan",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-9f24f0dd56d045a3a6b69df6058ed71a",
      "outcome": "done",
      "stage": "plan-improve",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-5ec24dba11144690a4229b310a204dbd",
      "outcome": "done",
      "stage": "step-plan",
      "summary": "Synthetic local navigator result.",
      "workitem": "W1"
    },
    {
      "action": "nav-f4a74e7fd32f4ad2b8ce29d1e20f0bf8",
      "outcome": "done",
      "stage": "step-plan-improve",
      "summary": "Synthetic local navigator result.",
      "workitem": "W1"
    },
    {
      "action": "nav-e9025fbd0feb40a29687bd5443cb1e59",
      "outcome": "done",
      "stage": "implement",
      "summary": "Synthetic local navigator result.",
      "workitem": "W1"
    },
    {
      "action": "nav-a60cec38236f4b858a75376b203d6e87",
      "outcome": "done",
      "stage": "test-refine",
      "summary": "Synthetic local navigator result.",
      "workitem": "W1"
    },
    {
      "action": "nav-598c6871f9ab4900b799c7fba8542518",
      "outcome": "done",
      "stage": "test-author",
      "summary": "Synthetic local navigator result.",
      "workitem": "W1"
    },
    {
      "action": "nav-0aa2a039d68b463e89ad6493af1c3676",
      "outcome": "done",
      "stage": "document",
      "summary": "Synthetic local navigator result.",
      "workitem": "W1"
    },
    {
      "action": "nav-bc6a14f78be049b3acafa90060dedaac",
      "outcome": "done",
      "stage": "verify",
      "summary": "Synthetic local navigator result.",
      "workitem": "W1"
    },
    {
      "action": "nav-27b4a45e45da415cbf828fba21808ecf",
      "outcome": "done",
      "stage": "product-improve",
      "summary": "Synthetic local navigator result.",
      "workitem": "W1"
    },
    {
      "action": "nav-0dbd72d1183640d2ad5c7a2788b8d8d2",
      "outcome": "done",
      "stage": "integrate",
      "summary": "Synthetic local navigator result.",
      "workitem": "W1"
    },
    {
      "action": "nav-f69f473ce027427bb9212e144b339b30",
      "outcome": "done",
      "stage": "carry-forward",
      "summary": "Synthetic local navigator result.",
      "workitem": "W1"
    },
    {
      "action": "nav-8b32f2c3834440819aeff43759cc76f7",
      "outcome": "done",
      "stage": "system-test",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-507e4c2054b04b2ea3bbbc5a69e0d079",
      "outcome": "done",
      "stage": "outer-improve",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-f37b12131837448eb89b1170e9b60275",
      "outcome": "done",
      "stage": "release-plan",
      "summary": "Synthetic local navigator result.",
      "workitem": null
    },
    {
      "action": "nav-9b0dce36f7974b10b6fa27aeb079812e",
      "outcome": "blocked",
      "stage": "release",
      "summary": "Synthetic candidate-v2 was declared after release planning; the current effectful action must remain blocked for a new planning run.",
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
  "prompt": "Synthetic local guarded recovery fixture only. No product, credential, network, consumer, target, or deployment exists. It models a material candidate change after release planning. Do not execute an operation from this fixture.",
  "repo": "synthetic://shiploop-consumer-delivery/no-live-target",
  "revision": 24,
  "run_id": "nav-72867728cd75414f99586cc05e3c1ca4",
  "stage": "release",
  "status": "active",
  "version": 3,
  "work_index": 1,
  "work_items": [
    {
      "id": "W1",
      "title": "Synthetic local guarded recovery fixture only. No product, credential, network, consumer, target, or deployment exists. It models a material candidate change af"
    }
  ]
}
```
