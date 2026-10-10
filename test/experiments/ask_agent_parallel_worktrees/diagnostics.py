"""Small stdlib helpers for evidence-bound Ask Agent experiment diagnostics."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Iterable, Mapping, NoReturn, TextIO


SCHEMA = "ask-agent-diagnostic/v1"
MAX_EVIDENCE_BYTES = 1_048_576
CONTRACT_REFS = frozenset(
    {
        "CONTRACT.md#phase-sequence",
        "CONTRACT.md#pass-gates",
        "CONTRACT.md#proof-precedence",
        "CONTRACT.md#retry-safety",
        "CONTRACT.md#evidence-references",
        "CONTRACT.md#portability-boundary",
        "CONTRACT.md#integration-boundary",
        "CONTRACT.md#compact-treatment",
        "CONTRACT.md#ambient-hooks",
        "CONTRACT.md#diagnostic-schema",
    }
)
_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
_DEFAULT_RETRY = (
    "Keep this run's evidence. Reconcile the cause before creating a new run; "
    "do not replay an action whose receipt says it was already attempted."
)


@dataclass(frozen=True)
class CheckRule:
    """Meaning assigned to one known verifier check key."""

    code: str
    expected: str
    rationale: str
    recovery: str
    rationale_ref: str = "CONTRACT.md#pass-gates"
    retry_safety: str = _DEFAULT_RETRY


def _rule(
    code: str,
    expected: str,
    rationale: str,
    recovery: str,
    *,
    rationale_ref: str = "CONTRACT.md#pass-gates",
    retry_safety: str = _DEFAULT_RETRY,
) -> CheckRule:
    return CheckRule(code, expected, rationale, recovery, rationale_ref, retry_safety)


DEFAULT_CHECK_RULES: dict[str, CheckRule] = {
    "frozen_package_hash_unchanged": _rule(
        "FROZEN_PACKAGE_CHANGED",
        "The copied ask-agent package tree hash equals the digest recorded in the manifest.",
        "A changed package means this report no longer describes the frozen candidate that was prepared.",
        "Compare the package and manifest digests, retain both, and prepare a new run from one chosen package.",
    ),
    "frozen_package_hash_verified": _rule(
        "FROZEN_PACKAGE_CHANGED",
        "The package hash matches the manifest and both preparation receipts.",
        "Integration must use the package identity that prepared every child workspace.",
        "Inspect setup-result.json and package hashes; do not continue integration on a mismatch.",
    ),
    "frozen_package_hash_unchanged_after_collection": _rule(
        "FROZEN_PACKAGE_CHANGED",
        "The package tree remains equal to the manifest digest after collection.",
        "A package change during collection breaks the binding between preparation and returned work.",
        "Retain collected receipts and patches, identify the changed bytes, and start a new run if needed.",
    ),
    "primary_pristine_fingerprint_preserved": _rule(
        "PRIMARY_STATE_CHANGED",
        "The primary repository's frozen HEAD, semantic index, status, and files remain unchanged.",
        "The primary snapshot is the source baseline used to derive the dirty caller and its children.",
        "Compare the expected and actual primary fingerprints; preserve the observed tree and do not reset it.",
    ),
    "caller_dirty_head_index_and_content_preserved": _rule(
        "CALLER_STATE_CHANGED",
        "The caller retains its frozen HEAD, semantic index, and inherited dirty inputs except for permitted task edits.",
        "The fixture begins with staged, unstaged, untracked, and deleted inputs that patch integration must preserve.",
        "Compare the caller snapshot and allowed task paths; preserve partial integration for manual reconciliation.",
    ),
    "exact_allowed_caller_source_changes": _rule(
        "CALLER_STATE_CHANGED",
        "Only the manifest's assigned task paths differ from the frozen caller snapshot.",
        "Unexpected caller changes cannot be attributed to the worker patches by this verifier.",
        "Inspect changed paths against the manifest and preserve all unrelated edits.",
    ),
    "worker_probe_completeness": _rule(
        "WORKER_PROBES_INCOMPLETE",
        "Each manifest worker has one valid start probe and one valid finish probe.",
        "The probes bind the worker's actual worktree and owned-path changes to the frozen run.",
        "Check per-worker probe records and their errors; do not infer a missing probe from a worker narrative.",
        rationale_ref="CONTRACT.md#evidence-references",
    ),
    "worker_roots_distinct_from_parent_and_each_other": _rule(
        "WORKTREE_ISOLATION_INVALID",
        "Every worker has a distinct Git root separate from the caller and primary checkout.",
        "Distinct roots are a fixture invariant for attributing each worker's file changes.",
        "Inspect the recorded roots and helper receipts; preserve all worktrees while resolving a mismatch.",
    ),
    "worker_index_paths_unique": _rule(
        "WORKTREE_ISOLATION_INVALID",
        "Each worker uses a distinct Git index path separate from the caller and primary indexes.",
        "A shared index would make independent staged-state observations ambiguous.",
        "Inspect each worktree's actual Git index path and helper receipt before another run.",
    ),
    "worker_common_dirs_match_fixture": _rule(
        "WORKTREE_ISOLATION_INVALID",
        "Each child worktree's Git common directory matches the fixture's recorded common directory.",
        "This confirms the tested helper-managed worktree relationship; it does not make the common Git store private.",
        "Compare recorded common directories and review the helper receipts; do not treat a worktree as a security boundary.",
        rationale_ref="CONTRACT.md#integration-boundary",
    ),
    "worker_snapshots_clean_and_exact_dirty_layers": _rule(
        "WORKER_SNAPSHOT_INVALID",
        "Each worker starts from the frozen caller state and changes only its assigned task path.",
        "The dirty input layers are deliberate and must survive child preparation and patch integration.",
        "Inspect the worker snapshot details and patch paths; retain staged and untracked caller inputs.",
    ),
    "collision_markers_use_same_path_and_unique_values": _rule(
        "WORKTREE_ISOLATION_INVALID",
        "Workers write the same relative marker path with distinct run-bound values in separate worktrees.",
        "This is a filesystem separation probe and does not test hostile cross-path access.",
        "Inspect the marker records and roots; do not describe this probe as a security test.",
        rationale_ref="CONTRACT.md#integration-boundary",
    ),
    "marker_intact_after_hold": _rule(
        "WORKER_MARKER_MISMATCH",
        "The worker's marker remains bound to its run and worker ID after the hold.",
        "The retained marker distinguishes each child probe in the deliberate path-collision fixture.",
        "Compare the marker and probe record for that worker; preserve the worktree for inspection.",
    ),
    "marker_intact_at_finish": _rule(
        "WORKER_MARKER_MISMATCH",
        "The worker's marker remains bound to its run and worker ID at finish.",
        "A changed marker weakens the recorded binding between the worker and its worktree.",
        "Compare the finish probe, start probe, and actual marker bytes for that worker.",
    ),
    "same_root_as_start": _rule(
        "WORKER_ROOT_CHANGED",
        "A worker's finish probe uses the same real Git root as its start probe.",
        "The start/finish pair is meaningful only when both observations refer to the same worktree.",
        "Compare both probe roots with the helper receipt and retain the worktree for review.",
    ),
    "hold_intervals_valid": _rule(
        "HOLD_INTERVAL_INVALID",
        "Each requested hold interval is finite, nonnegative, and bound to its probe record.",
        "Hold time is instrumentation; it is excluded from throughput comparisons.",
        "Compare manifest hold_seconds with the raw start-probe timestamps; do not use a bad interval as useful work time.",
    ),
    "parallel_hold_intervals_overlap": _rule(
        "PARALLEL_OVERLAP_NOT_OBSERVED",
        "When parallel mode requests a positive hold, all worker hold intervals overlap by at least 0.1 seconds.",
        "The overlap gate applies only to the explicit hold instrumentation and does not establish CPU parallelism.",
        "Inspect each interval and manifest mode; rerun a new controlled trial only after preserving this evidence.",
    ),
    "per_task_result_oracles_pass": _rule(
        "WORKER_ORACLE_FAILED",
        "Every worker module passes its independent integer-result oracle.",
        "A child completion event alone does not establish that its implementation is correct.",
        "Run the recorded per-task oracle against the retained worker output and preserve the failed result.",
    ),
    "task_result_oracle": _rule(
        "WORKER_ORACLE_FAILED",
        "This worker's transform matches its frozen task formula across the oracle inputs.",
        "The oracle is independent of the worker's self-reported completion text.",
        "Inspect the task ID, formula, inputs, and oracle output in the probe record.",
    ),
    "integrated_modules_match_worker_outputs": _rule(
        "INTEGRATED_OUTPUT_MISMATCH",
        "Each integrated module's bytes match the retained output for its worker.",
        "A correct result from a worker is not proof that the same bytes reached the caller.",
        "Compare worker module hashes, immutable patches, and caller bytes without overwriting either copy.",
    ),
    "integrated_per_task_result_oracles_pass": _rule(
        "INTEGRATED_ORACLE_FAILED",
        "Every integrated module passes its independent per-task oracle.",
        "The caller's integrated bytes must satisfy the same task contract as the worker output.",
        "Inspect the integrated module and oracle result while preserving the caller's current state.",
    ),
    "combined_pipeline_oracle_passes": _rule(
        "PIPELINE_ORACLE_FAILED",
        "The ascending-task pipeline matches the independent expected values for every fixture input.",
        "Per-module correctness does not by itself prove that pipeline composition and ordering are correct.",
        "Compare pipeline output with the independent expected values and retain the current integration state.",
    ),
    "prepared_setup_result_bound": _rule(
        "PREPARED_SETUP_INVALID",
        "Preparation is successful and bound to this caller, frozen HEAD, and exact manifest worker IDs.",
        "Integration is safe to inspect only after every helper-prepared workspace is bound to this run.",
        "Inspect setup-result.json and helper receipts; do not dispatch from a partial preparation.",
    ),
    "frozen_source_before_collection": _rule(
        "CALLER_STATE_CHANGED",
        "The caller's root, HEAD, semantic index, status, and files still match the frozen input before collection.",
        "Returned worker contributions must be compared against the original caller state.",
        "Compare caller snapshots and preserve the drifted state before deciding on another run.",
    ),
    "prepared_identity_records_match": _rule(
        "PACKAGE_IDENTITY_MISMATCH",
        "Every prepared worker record contains the same verified package identity.",
        "A worker's returned patch is interpreted against the package identity used at preparation.",
        "Compare package identity records and frozen package hashes; do not mix workers from different packages.",
    ),
    "source_unchanged_after_collection": _rule(
        "CALLER_STATE_CHANGED",
        "The caller remains at its frozen state until patch application begins.",
        "This binds collected contributions to a stable apply target.",
        "Inspect source snapshots and preserve any intervening caller edits.",
    ),
    "caller_state_before_patch_checks": _rule(
        "CALLER_STATE_CHANGED",
        "The caller still matches its frozen state before any patch is validated.",
        "Patch checks must run against the source state recorded by this trial.",
        "Compare the target state with the manifest and preserve unrelated changes.",
    ),
    "fixture_verify_passed": _rule(
        "FINAL_FIXTURE_VERIFICATION_FAILED",
        "The final fixture verifier returns passed=true after the expected worker patches are applied.",
        "Successful patch commands do not establish correct integrated output or preserved caller state.",
        "Inspect post-exit-verification.json and retain all applied patches and current caller bytes.",
    ),
    "fixture_scope": _rule(
        "FIXTURE_SCOPE_INVALID",
        "The manifest defines exactly three or five workers with IDs 1..N.",
        "Native lifecycle expectations are derived from the exact frozen worker assignment list.",
        "Inspect manifest.json and preserve it; use a fresh run for a corrected fixture.",
    ),
    "parent_binding": _rule(
        "NATIVE_PARENT_BINDING_INVALID",
        "The parent session ID and absolute cwd bind to the manifest's caller.",
        "Native events are attributed only through the launch-bound parent session and cwd.",
        "Compare launch.json, manifest.json, and the retained root updates log.",
        rationale_ref="CONTRACT.md#evidence-references",
    ),
    "parent_child_identity": _rule(
        "NATIVE_SPAWN_BINDING_INVALID",
        "Every child session ID maps to exactly one typed spawn call and manifest worker.",
        "Child identity is the join key for native launch, finish, collection, and probe evidence.",
        "Reconcile typed spawn receipts, child IDs, and manifest assignments in the retained root log.",
        rationale_ref="CONTRACT.md#evidence-references",
    ),
    "native_spawn_count": _rule(
        "NATIVE_SPAWN_COUNT_INVALID",
        "The parent records exactly one typed native spawn and spawned receipt per manifest worker.",
        "A child count is accepted only when spawn calls and host receipts join to the frozen assignments.",
        "Inspect the launch-bound updates log and process result; never replace a missing child silently.",
        rationale_ref="CONTRACT.md#phase-sequence",
    ),
    "sequential_dispatch_order": _rule(
        "NATIVE_SEQUENTIAL_ORDER_INVALID",
        "Each previous native child has an actual terminal collection result before the next child is launched.",
        "The sequential control must remove child overlap while retaining the same preparation and integration gates.",
        "Compare adjacent launch lines and the previous child's typed terminal collection line; a wait call alone is insufficient.",
        rationale_ref="CONTRACT.md#phase-sequence",
    ),
    "dispatch_mode": _rule(
        "NATIVE_DISPATCH_MODE_INVALID",
        "Manifest mode is exactly parallel or sequential.",
        "Unknown modes cannot select a meaningful launch-order qualification gate.",
        "Inspect the frozen manifest mode and use a fresh correctly prepared fixture.",
        rationale_ref="CONTRACT.md#phase-sequence",
    ),
    "parallel_dispatch_order": _rule(
        "NATIVE_DISPATCH_ORDER_INVALID",
        "Native launch and collection ordering matches the mode recorded in the manifest.",
        "Parallel and sequential cases use different collection order gates.",
        "Compare typed spawn and terminal collection events with manifest.mode.",
        rationale_ref="CONTRACT.md#phase-sequence",
    ),
    "fresh_context": _rule(
        "NATIVE_CONTEXT_NOT_FRESH",
        "Each worker is launched as a fresh native context without a resume source.",
        "A resumed context would carry state beyond the trial's frozen launch inputs.",
        "Inspect typed spawn arguments and retain the exact parent updates log.",
        rationale_ref="CONTRACT.md#phase-sequence",
    ),
    "general_purpose_background": _rule(
        "NATIVE_SPAWN_ARGUMENTS_INVALID",
        "Every typed spawn uses a general-purpose background worker.",
        "The trial's worker type and background mode are part of the compared launch contract.",
        "Inspect each typed spawn call and report unavailable fields as unknown, not as a pass.",
        rationale_ref="CONTRACT.md#phase-sequence",
    ),
    "spawn_argument_bindings": _rule(
        "NATIVE_SPAWN_BINDING_INVALID",
        "Each typed spawn binds one manifest assignment and a distinct prepared cwd.",
        "Assignment and cwd bindings connect each native child to its helper-prepared worktree.",
        "Compare spawn arguments, prepared receipts, and start probes for each worker.",
        rationale_ref="CONTRACT.md#evidence-references",
    ),
    "cwd_probe_binding": _rule(
        "NATIVE_CWD_BINDING_INVALID",
        "Each native spawn cwd equals the real Git root in that worker's start probe.",
        "The host's prepared cwd must identify the worktree where the child performed its task.",
        "Compare typed spawn arguments with the exact start-probe paths and helper receipts.",
        rationale_ref="CONTRACT.md#evidence-references",
    ),
    "parent_collected_all_children": _rule(
        "NATIVE_COLLECTION_INCOMPLETE",
        "The launch-bound parent obtains one terminal typed result for every native child.",
        "A spawn or finish event does not establish that the parent received the worker's result.",
        "Inspect each child-bound collection call; preserve missing or failed receipts and do not retry in place.",
        rationale_ref="CONTRACT.md#phase-sequence",
    ),
    "collection_parent_identity": _rule(
        "NATIVE_COLLECTION_BINDING_INVALID",
        "Collection calls are present in the exact launch-session updates log.",
        "Collection claims must be bound to the same parent session that launched the children.",
        "Compare the collection tool calls and session IDs in the retained root updates log.",
        rationale_ref="CONTRACT.md#evidence-references",
    ),
    "child_return_success": _rule(
        "NATIVE_CHILD_RETURN_FAILED",
        "Every terminal child collection reports completed status and exit_code 0.",
        "Terminal return status is separate from child finish-event status.",
        "Inspect the typed collection output for each child and preserve nonzero or missing returns.",
        rationale_ref="CONTRACT.md#pass-gates",
    ),
    "no_extra_or_missing_children": _rule(
        "NATIVE_CHILD_SET_INVALID",
        "The run contains exactly the distinct native children named by the manifest.",
        "Extra, duplicate, or missing child identities break one-to-one assignment accounting.",
        "Reconcile child IDs against manifest assignments and retained native receipts.",
        rationale_ref="CONTRACT.md#pass-gates",
    ),
    "child_transcript_retention": _rule(
        "NATIVE_TRANSCRIPT_INCOMPLETE",
        "Each bound child has a retained session-scoped updates transcript that passes schema checks.",
        "The audit needs the native child events to establish finish and work evidence.",
        "Inspect the specific retained child transcript and its source locator; keep the run intact.",
        rationale_ref="CONTRACT.md#evidence-references",
    ),
    "native_child_finished": _rule(
        "NATIVE_CHILD_FINISH_INVALID",
        "Every bound native child has exactly one completed finish event.",
        "A missing or non-completed finish event cannot be replaced by narrative text.",
        "Inspect child finish events and process status; classify missing live evidence as incomplete.",
        rationale_ref="CONTRACT.md#pass-gates",
    ),
    "independent_child_source_changes": _rule(
        "WORKER_SOURCE_SCOPE_INVALID",
        "Each worker changes only its single manifest-owned task file in its own worktree.",
        "Source attribution depends on the child transcript and start/finish snapshots agreeing.",
        "Inspect the worker's source-write evidence, probe snapshots, and returned patch paths.",
        rationale_ref="CONTRACT.md#integration-boundary",
    ),
    "packet_spawn_arguments": _rule(
        "NATIVE_PACKET_ARGUMENTS_INVALID",
        "Every packet-arm native spawn uses the exact emitted description, prompt, cwd, and background fields for its manifest worker.",
        "A timing claim about deterministic briefs requires proof that those briefs reached the native tool unchanged.",
        "Compare dispatch-packet.json with the cited native spawn and packet-emission events; preserve mismatches and use a new run after reconciliation.",
        rationale_ref="CONTRACT.md#phase-sequence",
    ),
    "compact_spawn_arguments": _rule(
        "NATIVE_COMPACT_ARGUMENTS_INVALID",
        "Every compact native spawn uses the exact one-worker assignment emitted from its retained binding and run files.",
        "The parent must pass each bounded assignment unchanged, with its worktree cwd, to preserve worker identity.",
        "Compare compact-dispatch/index.json, each emitted worker record, the typed parent command result, and native spawn fields.",
        rationale_ref="CONTRACT.md#compact-treatment",
    ),
    "compact_worker_phases": _rule(
        "NATIVE_COMPACT_WORKER_PHASE_INVALID",
        "Each native child invokes one bound start and finish wrapper, and each wrapper retains a successful production worker command result.",
        "Filesystem probes alone cannot prove that the production compact worker interface ran in the native child.",
        "Compare the retained child transcript commands with worker-phase attempt and raw production command records.",
        rationale_ref="CONTRACT.md#compact-treatment",
    ),
    "compact_parent_return_order": _rule(
        "NATIVE_COMPACT_RETURN_ORDER_INVALID",
        "The parent completes actual child collection before every compact verify-return and completes all verify-return checks before integration.",
        "The return gate must follow the native handoff and precede the existing guarded integration operation.",
        "Compare terminal collection, verify-return, and integrate-batch tool events with their retained command records.",
        rationale_ref="CONTRACT.md#compact-treatment",
    ),
    "parent_independent_source_work": _rule(
        "PARENT_SOURCE_WRITE_BEFORE_COLLECTION",
        "The parent performs no source write before terminal results are collected from every child.",
        "Early parent edits would make worker output and caller integration order ambiguous.",
        "Inspect the typed parent tool events; unresolved shell effects remain unknown, not clean.",
        rationale_ref="CONTRACT.md#phase-sequence",
    ),
    "parent_terminal": _rule(
        "NATIVE_PARENT_TERMINAL_INVALID",
        "The parent process exits zero after exactly one typed end_turn event.",
        "A process exit alone does not establish a valid native terminal event.",
        "Compare process-result.json and the observed stream's end event.",
        rationale_ref="CONTRACT.md#pass-gates",
    ),
    "no_parent_tool_activity_after_end": _rule(
        "NATIVE_PARENT_TERMINAL_INVALID",
        "No typed parent tool activity follows its end_turn event.",
        "A post-terminal tool call contradicts the recorded terminal boundary.",
        "Inspect the observed stream after the end event and retain the original event order.",
        rationale_ref="CONTRACT.md#evidence-references",
    ),
    "no_shell_child_launch": _rule(
        "NATIVE_SHELL_CHILD_LAUNCH_FOUND",
        "No parent shell command invokes a recognized child-agent launcher.",
        "Child lifecycle proof must come from the host's typed native spawn and collection events.",
        "Inspect the cited shell event and preserve the transcript for audit.",
        rationale_ref="CONTRACT.md#phase-sequence",
    ),
    "evidence_available": _rule(
        "NATIVE_EVIDENCE_MISSING",
        "Every required native evidence file is available for this audit phase.",
        "Unavailable evidence cannot support a pass even when the output files appear correct.",
        "Retain the missing-file error and determine whether the source event log is still available.",
        rationale_ref="CONTRACT.md#evidence-references",
    ),
    "evidence_valid": _rule(
        "NATIVE_EVIDENCE_INVALID",
        "Native evidence parses and matches the supported schema.",
        "Malformed or unsupported evidence cannot be interpreted as a successful lifecycle.",
        "Preserve the raw file and parser error; do not rewrite the evidence to fit the current schema.",
        rationale_ref="CONTRACT.md#evidence-references",
    ),
}

_DYNAMIC_CHECK_RULES = (
    (
        re.compile(r"^worker_(\d+)_identity_reverified$"),
        _rule(
            "PACKAGE_IDENTITY_MISMATCH",
            "Worker {worker}'s returned identity matches its prepared package and recorded helper/card hashes.",
            "The worker's delivered change must remain bound to the package used for its assignment.",
            "Compare the returned identity, setup receipt, helper hash, and skill-card hash.",
        ),
    ),
    (
        re.compile(r"^worker_(\d+)_returned_inspection_valid$"),
        _rule(
            "RETURNED_INSPECTION_INVALID",
            "Worker {worker}'s returned inspection binds its receipt and only its assigned patch path.",
            "Returned patch scope and receipt identity determine which bytes may be considered for integration.",
            "Inspect the returned helper report, receipt, artifact list, and contribution paths.",
        ),
    ),
    (
        re.compile(r"^worker_(\d+)_finish_snapshot_valid$"),
        _rule(
            "WORKER_SNAPSHOT_INVALID",
            "Worker {worker}'s finish snapshot differs from baseline only at its assigned task file.",
            "The finish snapshot binds a worker's output to its isolated worktree and inherited dirty inputs.",
            "Compare the finish checks, owned path, and worktree receipt; preserve the child tree.",
        ),
    ),
    (
        re.compile(r"^worker_(\d+)_module_bytes_bound$"),
        _rule(
            "WORKER_MODULE_BINDING_INVALID",
            "Worker {worker}'s module bytes match the digest in its finish snapshot.",
            "A patch must be derived from the same worker bytes that passed the task oracle.",
            "Compare the module digest and finish snapshot without replacing either artifact.",
        ),
    ),
    (
        re.compile(r"^worker_(\d+)_task_oracle_passed$"),
        _rule(
            "WORKER_ORACLE_FAILED",
            "Worker {worker}'s module passes its independent formula oracle.",
            "Native completion does not establish that the worker's formula is correct.",
            "Inspect the task oracle inputs and output for this worker.",
        ),
    ),
    (
        re.compile(r"^worker_(\d+)_patch_paths_exact$"),
        _rule(
            "PATCH_PATHS_INVALID",
            "Worker {worker}'s immutable patch changes exactly its assigned task path.",
            "A patch with additional paths could overwrite inherited or unrelated caller state.",
            "Inspect patch numstat and preserve the immutable patch before any apply attempt.",
        ),
    ),
    (
        re.compile(r"^worker_(\d+)_patch_hash_(?:after_check|before_apply|after_apply)$"),
        _rule(
            "PATCH_HASH_CHANGED",
            "Worker {worker}'s immutable patch retains its recorded SHA-256 at this integration phase.",
            "The apply decision is tied to the exact retained patch bytes.",
            "Compare patch copies and hashes; do not regenerate or overwrite a patch in this run.",
        ),
    ),
    (
        re.compile(r"^caller_state_(?:before_apply|after_apply)_(\d+)$"),
        _rule(
            "CALLER_STATE_CHANGED",
            "Caller state before or after worker {worker}'s patch matches baseline plus only already accepted task files.",
            "Each serial apply is accepted only when the cumulative caller delta is exactly accounted for.",
            "Preserve already applied modules and compare the cumulative state with accepted worker IDs.",
        ),
    ),
)


def _rule_for_check(name: str, rules: Mapping[str, CheckRule]) -> CheckRule | None:
    if name in rules:
        return rules[name]
    for pattern, rule in _DYNAMIC_CHECK_RULES:
        match = pattern.fullmatch(name)
        if match is not None:
            worker = match.group(1)
            if worker is None:
                return rule
            return CheckRule(
                code=rule.code,
                expected=rule.expected.format(worker=worker),
                rationale=rule.rationale,
                recovery=rule.recovery,
                rationale_ref=rule.rationale_ref,
                retry_safety=rule.retry_safety,
            )
    return None


_OPERATION_FAILURE_DETAILS: dict[str, tuple[str, str]] = {
    "PATCH_CONFLICT": (
        "The immutable patch does not apply cleanly to the current caller state.",
        "Keep prior applied modules and inspect the conflict record and patch; do not rerun integration.",
    ),
    "PATCH_APPLY_FAILED": (
        "The patch apply command failed after its recorded preflight.",
        "Preserve the current caller and patch bytes, then reconcile the partial apply before another run.",
    ),
    "PATCH_PATHS_INVALID": (
        "The patch includes a path outside its worker's assigned module.",
        "Keep the immutable patch and inspect its path list; do not apply it to the caller.",
    ),
    "PATCH_HASH_CHANGED": (
        "The patch bytes differ from the digest recorded for this integration attempt.",
        "Preserve both byte versions and do not regenerate or apply the changed patch in this run.",
    ),
    "HELPER_ACTION_FAILED": (
        "A selected helper identity or returned-inspection command failed.",
        "Inspect the exact helper call record and receipt; do not repeat an attempted integration action.",
    ),
    "INTEGRATION_ACTION_FAILED": (
        "A recorded integration command failed before its expected zero exit status.",
        "Inspect the action argv, exit code, stdout, stderr, and retained caller state before another run.",
    ),
    "INTEGRITY_CHECK_FAILED": (
        "A named integration invariant evaluated false.",
        "Inspect the exact failed check and preserve all receipts, patches, logs, and applied files.",
    ),
    "FROZEN_SOURCE_DRIFT": (
        "The caller no longer matches the frozen source snapshot before collection or patch checks.",
        "Preserve the changed caller and compare its HEAD, semantic index, status, and files with the manifest.",
    ),
    "SOURCE_DRIFT_BEFORE_APPLY": (
        "The caller changed outside the accepted worker patches before the next serial apply.",
        "Preserve already applied modules and reconcile the current caller state before using a fresh run.",
    ),
    "PACKAGE_IDENTITY_MISMATCH": (
        "A worker's returned package identity does not match the frozen prepared package.",
        "Compare identity records and package hashes; do not mix outputs from different package revisions.",
    ),
    "RETURNED_INSPECTION_INVALID": (
        "Returned inspection does not bind the receipt, owned path, artifact, or patch delivery mode.",
        "Inspect the helper receipt and returned report; keep the contribution out of integration.",
    ),
    "WORKER_FINISH_STATE_INVALID": (
        "A worker's finish snapshot includes unexpected state or misses its assigned edit.",
        "Inspect the child snapshot, probe, and receipt; retain the worktree for review.",
    ),
    "WORKER_ORACLE_FAILED": (
        "A worker output failed its independent task formula oracle.",
        "Inspect the task oracle and returned bytes; do not apply a failing contribution.",
    ),
    "FINAL_FIXTURE_VERIFICATION_FAILED": (
        "The final fixture verifier did not confirm the integrated caller state.",
        "Preserve the verification report and partial integration; do not auto-rollback or retry.",
    ),
    "INTEGRATION_FAILED": (
        "The integration attempt failed without a more specific recorded failure category.",
        "Use the failure message and preceding action records to identify the cause; retain partial state.",
    ),
}


def operation_failure_diagnostic(
    report: Mapping[str, Any],
    report_path: os.PathLike[str] | str,
    *,
    max_evidence_bytes: int = MAX_EVIDENCE_BYTES,
) -> dict[str, Any] | None:
    """Map one known structured operations.py failure, without guessing its cause."""
    failure = report.get("failure")
    if not isinstance(failure, Mapping):
        return None
    code = failure.get("code")
    details = _OPERATION_FAILURE_DETAILS.get(code) if isinstance(code, str) else None
    phase = failure.get("phase")
    expected = failure.get("expected")
    if details is None or not isinstance(phase, str) or not phase or expected is None:
        return None
    integrity_checks = report.get("integrity_checks")
    if isinstance(integrity_checks, Mapping):
        failed_check = integrity_checks.get(phase)
        if isinstance(failed_check, Mapping) and failed_check.get("passed") is False:
            return None

    rationale, recovery = details
    citations = [
        evidence_reference(
            report_path,
            json_pointer="/failure",
            max_bytes=max_evidence_bytes,
        )
    ]
    evidence_path = failure.get("evidence_path")
    if isinstance(evidence_path, str) and evidence_path:
        citations.append(
            evidence_reference(
                evidence_path,
                report_pointer="/failure/evidence_path",
                max_bytes=max_evidence_bytes,
            )
        )
    retry_safety = failure.get("retry_semantics")
    if not isinstance(retry_safety, str) or not retry_safety.strip():
        retry_safety = _DEFAULT_RETRY
    return make_diagnostic(
        code=code,
        severity="error",
        phase=phase,
        expected=expected,
        observed=failure.get("observed", failure),
        rationale=rationale,
        rationale_ref="CONTRACT.md#retry-safety",
        evidence=citations,
        recovery=recovery,
        retry_safety=retry_safety,
    )


def json_pointer(*segments: object) -> str:
    """Return an RFC 6901 JSON Pointer for the supplied path segments."""
    if not segments:
        return ""
    escaped = (str(segment).replace("~", "~0").replace("/", "~1") for segment in segments)
    return "/" + "/".join(escaped)


def _absolute_path(path: os.PathLike[str] | str) -> str:
    if not isinstance(path, (str, os.PathLike)):
        raise TypeError("evidence path must be path-like")
    return os.path.abspath(os.fsdecode(os.fspath(path)))


def evidence_reference(
    path: os.PathLike[str] | str,
    *,
    json_pointer: str | None = None,
    report_pointer: str | None = None,
    line: int | None = None,
    max_bytes: int = MAX_EVIDENCE_BYTES,
) -> dict[str, Any]:
    """Cite a path without inventing it; hash only bounded regular files."""
    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")
    for name, pointer in (("json_pointer", json_pointer), ("report_pointer", report_pointer)):
        if pointer is not None and (not isinstance(pointer, str) or (pointer and not pointer.startswith("/"))):
            raise ValueError(f"{name} must be an RFC 6901 pointer or the empty root pointer")
    if line is not None and (type(line) is not int or line < 1):
        raise ValueError("line must be a positive integer")

    absolute = _absolute_path(path)
    reference: dict[str, Any] = {"path": absolute}
    if json_pointer is not None:
        reference["json_pointer"] = json_pointer
    if report_pointer is not None:
        reference["report_pointer"] = report_pointer
    if line is not None:
        reference["line"] = line

    try:
        before = os.lstat(absolute)
    except FileNotFoundError:
        reference["hash_status"] = "missing"
        return reference
    except OSError as exc:
        reference["hash_status"] = "unavailable"
        reference["hash_error"] = type(exc).__name__
        return reference
    if not stat.S_ISREG(before.st_mode):
        reference["hash_status"] = "not_regular_file"
        return reference
    if before.st_size > max_bytes:
        reference["hash_status"] = "over_limit"
        return reference

    descriptor = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(absolute, flags)
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
        ):
            reference["hash_status"] = "changed_during_open"
            return reference
        digest = hashlib.sha256()
        size = 0
        with os.fdopen(descriptor, "rb") as source:
            descriptor = None
            while True:
                chunk = source.read(min(64 * 1024, max_bytes + 1 - size))
                if not chunk:
                    break
                digest.update(chunk)
                size += len(chunk)
                if size > max_bytes:
                    reference["hash_status"] = "over_limit"
                    return reference
            after = os.fstat(source.fileno())
            if size != opened.st_size or (after.st_dev, after.st_ino) != (opened.st_dev, opened.st_ino):
                reference["hash_status"] = "changed_during_read"
                return reference
        reference["sha256"] = digest.hexdigest()
        reference["hash_status"] = "hashed"
    except OSError as exc:
        reference["hash_status"] = "unavailable"
        reference["hash_error"] = type(exc).__name__
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return reference


def make_diagnostic(
    *,
    code: str,
    severity: str,
    phase: str,
    expected: Any,
    observed: Any,
    rationale: str,
    rationale_ref: str,
    evidence: Iterable[Mapping[str, Any]],
    recovery: str,
    retry_safety: str,
) -> dict[str, Any]:
    """Build one validated diagnostic record."""
    if not isinstance(code, str) or _CODE_RE.fullmatch(code) is None:
        raise ValueError("code must be a stable uppercase identifier")
    if severity not in {"warning", "error"}:
        raise ValueError("severity must be 'warning' or 'error'")
    for name, value in (
        ("phase", phase),
        ("rationale", rationale),
        ("recovery", recovery),
        ("retry_safety", retry_safety),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
    if rationale_ref not in CONTRACT_REFS:
        raise ValueError("rationale_ref must name a frozen anchor in CONTRACT.md")
    evidence_rows = [dict(row) for row in evidence]
    if any(not isinstance(row.get("path"), str) or not row["path"] for row in evidence_rows):
        raise ValueError("each evidence reference must contain a path")
    diagnostic = {
        "schema": SCHEMA,
        "code": code,
        "severity": severity,
        "phase": phase,
        "expected": expected,
        "observed": observed,
        "rationale": rationale,
        "rationale_ref": rationale_ref,
        "evidence": evidence_rows,
        "recovery": recovery,
        "retry_safety": retry_safety,
    }
    json.dumps(diagnostic, allow_nan=False)
    return diagnostic


def _failure_severity(value: Any) -> str | None:
    if value is False:
        return "error"
    if isinstance(value, Mapping):
        if value.get("passed") is False:
            return "error"
        status = value.get("status")
        if not isinstance(status, str):
            return None
        if status == "FAIL":
            return "error"
        if status in {"INCOMPLETE", "UNKNOWN"}:
            return "warning"
    return None


def _reported_evidence(
    check_value: Any,
    container_name: str,
    check_name: str,
    max_bytes: int,
) -> list[dict[str, Any]]:
    if not isinstance(check_value, Mapping):
        return []
    rows = check_value.get("evidence")
    if not isinstance(rows, list):
        return []
    references: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
            continue
        line = row.get("line")
        references.append(
            evidence_reference(
                row["path"],
                report_pointer=json_pointer(container_name, check_name, "evidence", index),
                line=line if type(line) is int and line > 0 else None,
                max_bytes=max_bytes,
            )
        )
    return references


def report_check_diagnostics(
    report: Mapping[str, Any],
    report_path: os.PathLike[str] | str,
    *,
    phase: str,
    rules: Mapping[str, CheckRule] = DEFAULT_CHECK_RULES,
    max_evidence_bytes: int = MAX_EVIDENCE_BYTES,
) -> list[dict[str, Any]]:
    """Map known fixture, native, or integration checks; ignore unknown meanings."""
    checks = report.get("checks")
    container_name = "checks"
    if not isinstance(checks, Mapping):
        checks = report.get("integrity_checks")
        container_name = "integrity_checks"
    if not isinstance(checks, Mapping):
        raise ValueError("report checks or integrity_checks must be a JSON object")
    if any(not isinstance(name, str) for name in checks):
        raise ValueError("report check names must be strings")
    output: list[dict[str, Any]] = []
    for name in sorted(checks):
        rule = _rule_for_check(name, rules)
        value = checks[name]
        severity = _failure_severity(value)
        if rule is None or severity is None:
            continue
        pointer = json_pointer(container_name, name)
        citations = [
            evidence_reference(
                report_path,
                json_pointer=pointer,
                max_bytes=max_evidence_bytes,
            ),
            *_reported_evidence(value, container_name, name, max_evidence_bytes),
        ]
        failure = report.get("failure")
        if (
            container_name == "integrity_checks"
            and isinstance(failure, Mapping)
            and failure.get("phase") == name
            and isinstance(failure.get("evidence_path"), str)
        ):
            citations.append(
                evidence_reference(
                    failure["evidence_path"],
                    report_pointer="/failure/evidence_path",
                    max_bytes=max_evidence_bytes,
                )
            )
        output.append(
            make_diagnostic(
                code=rule.code,
                severity=severity,
                phase=phase,
                expected=rule.expected,
                observed=value,
                rationale=rule.rationale,
                rationale_ref=rule.rationale_ref,
                evidence=citations,
                recovery=rule.recovery,
                retry_safety=rule.retry_safety,
            )
        )
    return output


def emit_diagnostics(
    diagnostics: Iterable[Mapping[str, Any]],
    *,
    jsonl_path: os.PathLike[str] | str | None = None,
    stream: TextIO | None = None,
) -> None:
    """Write compact JSON lines to stderr and optionally append a run log.

    The JSONL target is intended to have one process writer per run. Each record
    is encoded as one append write and fsynced; this is not a multi-writer log.
    """
    rows = [dict(row) for row in diagnostics]
    lines = [
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        for row in rows
    ]
    append_error: OSError | None = None
    if jsonl_path is not None and lines:
        descriptor = None
        try:
            descriptor = os.open(
                os.fspath(jsonl_path),
                os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                0o600,
            )
            payload = ("\n".join(lines) + "\n").encode("utf-8")
            written = os.write(descriptor, payload)
            if written != len(payload):
                raise OSError("diagnostics JSONL append was incomplete")
            os.fsync(descriptor)
        except OSError as exc:
            append_error = exc
        finally:
            if descriptor is not None:
                os.close(descriptor)
    output = stream if stream is not None else sys.stderr
    for line in lines:
        output.write(line + "\n")
    if lines:
        output.flush()
    if append_error is not None:
        raise append_error


def exit_with_diagnostic(
    diagnostic: Mapping[str, Any],
    *,
    jsonl_path: os.PathLike[str] | str | None = None,
    stream: TextIO | None = None,
) -> NoReturn:
    """Emit one operational failure and exit with the CLI error status 2."""
    if diagnostic.get("severity") != "error":
        raise ValueError("exit_with_diagnostic requires severity='error'")
    emit_diagnostics([diagnostic], jsonl_path=jsonl_path, stream=stream)
    raise SystemExit(2)
