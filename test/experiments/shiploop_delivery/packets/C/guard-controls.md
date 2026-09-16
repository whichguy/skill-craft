# Synthetic ShipLoop delivery-guard controls

```shiploop-state
{
  "authoring_observations": [
    {
      "id": "release-plan-phase-order",
      "observed": "Original A/B release-plan teachbacks conflated a non-executing plan with later release and consumer-verification work; the frozen B2 follow-up records the corrected phase-order criterion.",
      "source": "test/experiments/shiploop_delivery/README.md#exploratory-b2-phase-order-follow-up"
    },
    {
      "id": "candidate-specific-contract-correction",
      "observed": "During C fixture authoring, changing candidate-specific expected fields with candidate-v2 required a declared synthetic user-decision correction. The post-plan recovery fixture therefore carries that correction rather than a hand-edited anchor.",
      "source": "prepare_guard_packets.py#candidate-replan-recovery"
    },
    {
      "id": "source-only-optional-activation",
      "observed": "Review found that a source-only declaration could previously retain optional effect or identity rows. This schema control records the current rejection and a behavior-retaining source-only counterpart.",
      "source": "test/shiploop-consumer-delivery.test.py#test-not-required-contract-rejects-optional-activation-rows-for-any-authority-state"
    }
  ],
  "controls": [
    {
      "id": "missing-plan-contract",
      "normal_public_api": {
        "apply": "rejected",
        "error": "delivery contract is required before successful plan-improve",
        "stage": "plan-improve",
        "state_unchanged": true
      },
      "test_only_guard_mutation": {
        "apply": "advanced",
        "limitation": "This is an in-process test mutation, not a supported production route.",
        "patched_entry_points": [
          "validate_transition"
        ],
        "revalidates_after_patch": true,
        "stage_after": "step-plan",
        "status_after": "active"
      },
      "valid_counterpart": {
        "apply": "advanced",
        "stage_after": "step-plan",
        "status_after": "active"
      }
    },
    {
      "id": "source-only-optional-activation-contradiction",
      "normal_public_api": {
        "apply": "rejected",
        "error": "not-required delivery contract cannot retain effect or identity obligations",
        "stage": "plan-improve",
        "state_unchanged": true
      },
      "test_only_guard_mutation": {
        "apply": "not-representable",
        "limitation": "This is intentionally recorded as a schema gate, not inflated into a synthetic production-bypass claim.",
        "reason": "The malformed contract is rejected by canonicalization before the shared transition guard. Patching validate_transition alone cannot produce a safely valid accepted state."
      },
      "valid_counterpart": {
        "apply": "advanced",
        "stage_after": "step-plan",
        "status_after": "active"
      }
    },
    {
      "id": "missing-pre-update-check",
      "normal_public_api": {
        "apply": "rejected",
        "error": "required pre-update obligations are not current",
        "stage": "system-test",
        "state_unchanged": true
      },
      "test_only_guard_mutation": {
        "apply": "advanced",
        "limitation": "This is an in-process test mutation, not a supported production route.",
        "patched_entry_points": [
          "validate_transition"
        ],
        "revalidates_after_patch": true,
        "stage_after": "outer-improve",
        "status_after": "active"
      },
      "valid_counterpart": {
        "apply": "advanced",
        "stage_after": "outer-improve",
        "status_after": "active"
      }
    },
    {
      "id": "unresolved-release-authority",
      "normal_public_api": {
        "apply": "rejected",
        "error": "delivery authority is unresolved; submit blocked with the needed approval",
        "stage": "release-plan",
        "state_unchanged": true
      },
      "test_only_guard_mutation": {
        "apply": "advanced",
        "limitation": "This is an in-process test mutation, not a supported production route.",
        "patched_entry_points": [
          "validate_transition"
        ],
        "revalidates_after_patch": true,
        "stage_after": "release",
        "status_after": "active"
      },
      "valid_counterpart": {
        "apply": "advanced",
        "stage_after": "release",
        "status_after": "active"
      }
    },
    {
      "id": "missing-release-effect-and-identity",
      "normal_public_api": {
        "apply": "rejected",
        "error": "required release obligations need effect and identity observations",
        "stage": "release",
        "state_unchanged": true
      },
      "test_only_guard_mutation": {
        "apply": "advanced",
        "limitation": "This is an in-process test mutation, not a supported production route.",
        "patched_entry_points": [
          "validate_transition"
        ],
        "revalidates_after_patch": true,
        "stage_after": "release-verify",
        "status_after": "active"
      },
      "valid_counterpart": {
        "apply": "advanced",
        "stage_after": "release-verify",
        "status_after": "active"
      }
    },
    {
      "id": "missing-release-verify-behavior",
      "normal_public_api": {
        "apply": "rejected",
        "error": "required release-verify behavior obligations are not current",
        "stage": "release-verify",
        "state_unchanged": true
      },
      "test_only_guard_mutation": {
        "apply": "advanced",
        "limitation": "This is an in-process test mutation, not a supported production route.",
        "patched_entry_points": [
          "validate_transition"
        ],
        "revalidates_after_patch": true,
        "stage_after": "handoff",
        "status_after": "active"
      },
      "valid_counterpart": {
        "apply": "advanced",
        "stage_after": "handoff",
        "status_after": "active"
      }
    },
    {
      "id": "post-plan-candidate-change-requires-replanning",
      "normal_public_api": {
        "apply": "rejected",
        "error": "The required delivery contract changed after release planning and requires replanning; start a new planning run before another completion.",
        "stage": "release",
        "state_unchanged": true
      },
      "test_only_guard_mutation": {
        "apply": "advanced",
        "limitation": "This is an in-process test mutation, not a supported production route.",
        "patched_entry_points": [
          "validate_transition"
        ],
        "revalidates_after_patch": true,
        "stage_after": "release-verify",
        "status_after": "active"
      },
      "valid_counterpart": {
        "apply": "advanced",
        "stage_after": "release-verify",
        "status_after": "active"
      }
    },
    {
      "id": "handoff-outstanding-required-obligation",
      "normal_public_api": {
        "apply": "rejected",
        "error": "required consumer-delivery obligations remain unfinished",
        "stage": "handoff",
        "state_unchanged": true
      },
      "test_only_guard_mutation": {
        "apply": "advanced",
        "limitation": "This is an in-process test mutation, not a supported production route.",
        "patched_entry_points": [
          "validate_transition",
          "validate_terminal"
        ],
        "revalidates_after_patch": false,
        "stage_after": "done",
        "status_after": "done"
      },
      "valid_counterpart": {
        "apply": "advanced",
        "stage_after": "done",
        "status_after": "done"
      }
    }
  ],
  "measurements": {
    "packet_bytes": {
      "measurement": "UTF-8 byte length of each frozen renderer packet; not tokens or time.",
      "samples": [
        {
          "packet": "login-after-upload-recovery.md",
          "utf8_bytes": 9748
        },
        {
          "packet": "post-plan-candidate-change-recovery.md",
          "utf8_bytes": 9783
        },
        {
          "packet": "../C2/post-plan-candidate-change-current-renderer.md",
          "utf8_bytes": 10073
        }
      ]
    },
    "result_template_host_field_overhead": {
      "measurement": "UTF-8 bytes added by the script-provided delivery_assessment field in sorted, indented json.dumps result data; not tokens or time.",
      "samples": [
        {
          "base_result_json_utf8_bytes": 73,
          "delivery_assessment_added_utf8_bytes": 367,
          "guarded_result_json_utf8_bytes": 440,
          "packet": "login-after-upload-recovery.md",
          "stage": "release-verify"
        },
        {
          "base_result_json_utf8_bytes": 73,
          "delivery_assessment_added_utf8_bytes": 591,
          "guarded_result_json_utf8_bytes": 664,
          "packet": "post-plan-candidate-change-recovery.md",
          "stage": "release"
        },
        {
          "base_result_json_utf8_bytes": 73,
          "delivery_assessment_added_utf8_bytes": 591,
          "guarded_result_json_utf8_bytes": 664,
          "packet": "../C2/post-plan-candidate-change-current-renderer.md",
          "stage": "release"
        }
      ]
    }
  },
  "model_scores": "not measured by this deterministic control",
  "synthetic": true,
  "unmarked_backward_compatibility": {
    "configuration": "delivery guard not opted in",
    "id": "unmarked-generic-missing-evidence",
    "public_apply": "accepted",
    "stage_after": "handoff"
  }
}
```
