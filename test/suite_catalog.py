#!/usr/bin/env python3
"""The one declarative inventory for the repository's hermetic checks.

The shell entrypoints deliberately contain no test membership.  Keeping that
membership here lets local component runs, quick, full qualification and CI
shards answer the same question without maintaining parallel lists.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
import json
import math
from pathlib import Path, PurePosixPath
import re
from typing import Iterable


DEFAULT_TIMEOUT_SECONDS = 1_800
SHIPLOOP_SHARD_COUNT = 3


@dataclass(frozen=True)
class Suite:
    """One fixed, hermetic process invocation owned by this catalog."""

    id: str
    family: str
    path: str
    argv: tuple[str, ...]
    groups: frozenset[str]
    timeout_seconds: int
    hermetic: bool


def _suite(
    identifier: str,
    family: str,
    path: str,
    *argv: str,
    groups: Iterable[str] = (),
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> Suite:
    """Build a catalog entry while making the hermetic classification explicit."""

    return Suite(
        id=identifier,
        family=family,
        path=path,
        argv=tuple(argv),
        groups=frozenset(groups),
        timeout_seconds=timeout_seconds,
        hermetic=True,
    )


def _identifier(path: str) -> str:
    """Derive a stable, readable id for a ShipLoop test path."""

    name = path.removeprefix("test/")
    for suffix in (".test.py", ".test.cjs", ".test.js", ".test.sh"):
        if name.endswith(suffix):
            name = name.removesuffix(suffix)
            break
    else:
        # Nested experiment modules use the normal unittest ``test_*.py``
        # spelling instead of the repository's ``*.test.py`` spelling.
        name = name.removesuffix(".py")
    name = name.replace("test_", "")
    return name.replace("/", "-").replace("_", "-")


# The ordered ShipLoop inventory.  Order remains meaningful for full local
# output and for deterministic component unions.
_E2E_SPLIT_IDS = ("shiploop-e2e-analysis", "shiploop-e2e-hosts", "shiploop-e2e-resources")
_E2E_SPLIT_PATHS = tuple(f"test/{identifier}.test.py" for identifier in _E2E_SPLIT_IDS)
_E2E_TEST_PATHS = frozenset({"test/shiploop-e2e.test.py", "test/shiploop-e2e-support.py", *_E2E_SPLIT_PATHS})

_SHIPLOOP_PATHS = (
    "test/shiploop-no-model-launch.test.py",
    "test/shiploop-navigator-contract.test.py",
    "test/shiploop-navigator-v4.test.py",
    "test/shiploop-stopped-improve.test.py",
    "test/shiploop-standalone-improve.test.py",
    "test/shiploop-actual-improve-cli.test.py",
    "test/shiploop-packet-bounds.test.py",
    "test/shiploop-packet-completeness.test.py",
    "test/shiploop-step-packets.test.py",
    "test/shiploop-packet-recut.test.py",
    "test/shiploop-head-order.test.py",
    "test/shiploop-reference.test.py",
    "test/shiploop-guidance.test.py",
    "test/shiploop-local-skills.test.py",
    "test/experiments/shiploop_ui_allocation/test_evidence.py",
    "test/shiploop-full-runtime.test.py",
    "test/shiploop-navigator-dry-run.test.py",
    "test/shiploop-status-display.test.py",
    "test/shiploop-narrative.test.py",
    "test/shiploop-progress.test.py",
    "test/shiploop-progress-data.test.py",
    "test/shiploop-progress-render.test.py",
    "test/shiploop-stage-spec.test.py",
    "test/shiploop-send-back.test.py",
    "test/shiploop-step-edges.test.py",
    "test/shiploop-rehydration.test.py",
    "test/shiploop-confirmation.test.py",
    "test/shiploop-auth-readiness.test.py",
    "test/shiploop-cross-run.test.py",
    "test/shiploop-workspace.test.py",
    "test/shiploop-return-review.test.py",
    "test/shiploop-consumer-delivery.test.py",
    "test/shiploop-consumer-delivery-cli.test.py",
    "test/shiploop-delegation.test.py",
    "test/shiploop-improve-schedule.test.py",
    "test/shiploop-lint.test.py",
    "test/shiploop-quality.test.py",
    "test/shiploop-loops.test.py",
    "test/shiploop-iteration.test.py",
    "test/shiploop-seed-seam.test.py",
    "test/shiploop-test-loop.test.py",
    "test/shiploop-test-counts.test.py",
    "test/shiploop-backchain-check.test.py",
    "test/shiploop-improve-changes.test.py",
    "test/shiploop-knowledge.test.py",
    "test/shiploop-handoff.test.py",
    "test/shiploop-follow-on.test.py",
    "test/shiploop-assumptions.test.py",
    "test/experiments/shiploop_delivery/fake_deployment.test.py",
    "test/experiments/shiploop_delivery/browser_consumer/serve_fixture.test.py",
    "test/shiploop-store.test.py",
    "test/shiploop-literal-transport.test.py",
    "test/shiploop-discovery.test.py",
    "test/shiploop-capability-fixture.test.py",
    "test/shiploop-capability-runtime.test.py",
    "test/shiploop-generalized-discovery.test.py",
    "test/shiploop-probe-decisions.test.py",
    "test/shiploop-capability-async.test.cjs",
    "test/shiploop-repeatable-experiments.test.py",
    "test/shiploop-privacy.test.py",
    "test/shiploop-reference-routing.test.py",
    "test/shiploop-domain-words.test.py",
    "test/shiploop-retired-terms.test.py",
    "test/shiploop-keepalive.test.py",
    "test/shiploop-skill-calls.test.py",
    "test/shiploop-trace.test.py",
    "test/shiploop-owner-notes.test.py",
    "test/shiploop-planning-handoff.test.py",
    "test/shiploop-package-integrity.test.py",
    "test/shiploop-python-floor.test.py",
    "test/shiploop-clean-consumer.test.py",
    *_E2E_SPLIT_PATHS,
    "test/shiploop-e2e-discovery.test.py",
    "test/shiploop-e2e-qualification.test.py",
    "test/shiploop-e2e-roles.test.py",
    "test/shiploop-e2e-roundtable.test.py",
    "test/shiploop-e2e-epoch.test.py",
    "test/shiploop-e2e-predecessor.test.py",
    "test/shiploop-e2e-predecessor-wiring.test.py",
    "test/shiploop-e2e-intent-continuity.test.py",
    "test/shiploop-e2e-learning-records.test.py",
    "test/shiploop-e2e-cycle.test.py",
    "test/shiploop-e2e-runrecord.test.py",
    "test/shiploop-e2e-slice.test.py",
    "test/shiploop-e2e-fidelity.test.py",
    "test/shiploop-e2e-reorientation.test.py",
    "test/shiploop-e2e-environment.test.py",
    "test/shiploop-e2e-baseline.test.py",
    "test/shiploop-e2e-quality.test.py",
    "test/shiploop-e2e-packet-anatomy.test.py",
    "test/shiploop-e2e-render-diff.test.py",
    "test/shiploop-e2e-commit-counters.test.py",
    "test/shiploop-e2e-chess-salesforce.test.py",
    "test/shiploop-e2e-battleship-salesforce.test.py",
    "test/shiploop-e2e-battleship-ui.test.py",
    "test/shiploop-e2e-grok-chat-salesforce.test.py",
    "test/shiploop-e2e-grok-chat-full.test.py",
    "test/shiploop-e2e-grok-chat-full-ui.test.py",
    "test/shiploop-e2e-grok-chat-full-oracle.test.py",
    "test/shiploop-e2e-grok-chat-full-quality.test.py",
    "test/shiploop-e2e-gym-membership-salesforce.test.py",
    "test/shiploop-e2e-gym-ui.test.py",
    "test/shiploop-e2e-release-slice.test.py",
    "test/shiploop-e2e-platform.test.py",
    "test/shiploop-e2e-sf-guard.test.py",
    "test/shiploop-e2e-status-card.test.py",
    "test/shiploop-e2e-efficiency.test.py",
    "test/shiploop-e2e-dodges.test.py",
    "test/shiploop-e2e-owner-page.test.py",
    "test/shiploop-e2e-experiments.test.py",
    "test/shiploop-e2e-sdlc-probes.test.py",
    "test/shiploop-e2e-review-attribution.test.py",
    "test/shiploop-e2e-ticket-semantics.test.py",
    "test/shiploop-e2e-scope-discovery.test.py",
    "test/shiploop-e2e-stage-oracle.test.py",
    "test/shiploop-e2e-stage-build.test.py",
    "test/shiploop-e2e-stages.test.py",
    "test/shiploop-e2e-stage-live.test.py",
    "test/shiploop-e2e-stage-report.test.py",
    "test/shiploop-e2e-run-trace.test.py",
    "test/shiploop-e2e-brownfield.test.py",
    "test/shiploop-e2e-brownfield-tickets.test.py",
    "test/shiploop-e2e-test-adequacy.test.py",
    "test/shiploop-e2e-delta.test.py",
    "test/shiploop-e2e-corpus.test.py",
    "test/shiploop-e2e-incremental-pilot.test.py",
    "test/shiploop-e2e-ticket-comments.test.py",
    "test/shiploop-e2e-ticket-sla.test.py",
    "test/shiploop-e2e-user-chain.test.py",
    "test/shiploop-e2e-user-directory.test.py",
    "test/shiploop-e2e-lifecycle.test.py",
    "test/shiploop-packet-obligations.test.py",
    "test/shiploop-efficiency-journal.test.py",
    "test/shiploop-run-review.test.py",
    "test/shiploop-callback-contract.test.py",
    "test/shiploop-loophole-gates.test.py",
)

# Scheduling costs and their measured provenance live separately from selection policy.
# Refreshing these observations must never silently remove quick coverage.
_DURATION_SECONDS = json.loads(Path(__file__).with_name("suite_durations.json").read_text())["seconds"]
_FALLBACK_DURATION_SECONDS = 60.0

# The quick tier's fixed ShipLoop baseline: fast graph, packet and boundary checks.
_QUICK_PATHS = frozenset({
    "test/shiploop-stage-spec.test.py",
    "test/shiploop-no-model-launch.test.py",
    "test/shiploop-navigator-contract.test.py",
    "test/shiploop-navigator-v4.test.py",
    "test/shiploop-stopped-improve.test.py",
    "test/shiploop-packet-bounds.test.py",
    "test/shiploop-navigator-dry-run.test.py",
    "test/shiploop-status-display.test.py",
    "test/shiploop-narrative.test.py",
    "test/shiploop-planning-handoff.test.py",
})

# Current Ask-Agent checks.  The adapter rows exercise the ShipLoop consumers
# that make the current helper contract material.
_ASK_AGENT_PATHS = frozenset({
    "test/shiploop-consumer-delivery.test.py",
    "test/shiploop-consumer-delivery-cli.test.py",
})

_COMPOSITION_PATHS = frozenset({
    "test/shiploop-actual-improve-cli.test.py",
    "test/shiploop-consumer-delivery-cli.test.py",
    "test/shiploop-consumer-delivery.test.py",
    "test/shiploop-delegation.test.py",
    "test/shiploop-full-runtime.test.py",
    "test/shiploop-improve-schedule.test.py",
    "test/shiploop-standalone-improve.test.py",
    "test/shiploop-stopped-improve.test.py",
})


# The python-floor group is every ShipLoop suite except the E2E apparatus's (shiploop-e2e*): the CI job that runs it uses the
# oldest Python ShipLoop declares (shiploop_pyfloor.FLOOR), so a change that needs a newer one fails there.  The apparatus is
# developer tooling for live model runs and needs 3.10+ (os.waitid, sys.stdlib_module_names).
def _shiploop(path: str) -> Suite:
    groups: set[str] = set()
    if path in _QUICK_PATHS:
        groups.add("quick")
    if path in _ASK_AGENT_PATHS:
        groups.add("ask-agent")
    if path in _COMPOSITION_PATHS:
        groups.add("shiploop-composition")
    if not _identifier(path).startswith("shiploop-e2e"):
        groups.add("python-floor")
    interpreter = "node" if path.endswith(".cjs") else "python3"
    return _suite(_identifier(path), "shiploop", path, interpreter, path, groups=groups)


_CORE_SUITES = (
    _suite("backchain-chunks", "core", "test/backchain-chunks.test.py", "python3", "-B", "test/backchain-chunks.test.py"),
    _suite("backchain-graph", "core", "test/backchain-graph.test.py", "python3", "-B", "test/backchain-graph.test.py"),
    _suite("backchain-toolkit", "core", "test/backchain-toolkit.test.py", "python3", "-B", "test/backchain-toolkit.test.py"),
    _suite("test-groups", "core", "test/test-groups.test.py", "python3", "test/test-groups.test.py"),
    _suite("ci-policy", "core", "test/ci-policy.test.py", "python3", "test/ci-policy.test.py"),
    _suite("integration-boundaries", "core", "test/integration-boundaries.test.py", "python3", "test/integration-boundaries.test.py"),
    _suite("release-push", "core", "test/release-push.test.py", "python3", "test/release-push.test.py"),
    _suite("ask-agent-workspace", "core", "test/ask-agent-workspace.test.py", "python3", "test/ask-agent-workspace.test.py", groups=("ask-agent",)),
    _suite("ask-agent-delivery", "core", "test/ask-agent-delivery.test.py", "python3", "test/ask-agent-delivery.test.py", groups=("ask-agent",)),
    _suite("ask-agent-managed-harness", "core", "test/ask-agent-managed-harness.test.py", "python3", "test/ask-agent-managed-harness.test.py", groups=("ask-agent",)),
    _suite("ask-agent-parallel", "core", "test/ask-agent-parallel.test.py", "python3", "test/ask-agent-parallel.test.py", groups=("ask-agent",)),
    _suite("ask-agent-current-workspace", "core", "test/ask-agent-current-workspace.test.py", "python3", "test/ask-agent-current-workspace.test.py", groups=("ask-agent",)),
    _suite("ask-agent-task", "core", "test/ask-agent-task.test.py", "python3", "test/ask-agent-task.test.py", groups=("ask-agent",)),
    _suite("in-parallel-queue-audit", "core", "test/experiments/in_parallel_queue/test_experiment.py", "python3", "-B", "test/experiments/in_parallel_queue/test_experiment.py", groups=("agent-harness", "in-parallel")),
    _suite("in-parallel-queue", "core", "test/in-parallel-queue.test.py", "python3", "-B", "test/in-parallel-queue.test.py", groups=("agent-harness", "in-parallel")),
    _suite("in-parallel-composition", "core", "test/in-parallel-composition.test.py", "python3", "-B", "test/in-parallel-composition.test.py", groups=("agent-harness", "in-parallel")),
    _suite("agent-harness", "core", "test/agent-harness.test.py", "python3", "-B", "test/agent-harness.test.py", groups=("agent-harness", "in-parallel")),
    _suite("agent-harness-delivery", "core", "test/agent-harness-delivery.test.py", "python3", "-B", "test/agent-harness-delivery.test.py", groups=("agent-harness", "in-parallel")),
    _suite("agent-harness-boundaries", "core", "test/agent-harness-boundaries.test.py", "python3", "-B", "test/agent-harness-boundaries.test.py", groups=("agent-harness", "in-parallel")),
    _suite("agent-harness-audit", "core", "test/experiments/agent_harness/test_audit.py", "python3", "-B", "test/experiments/agent_harness/test_audit.py", groups=("agent-harness", "in-parallel")),
    _suite("skill-interop-hygiene", "core", "test/skill-interop-hygiene.test.sh", "bash", "test/skill-interop-hygiene.test.sh"),
    _suite("sync-plugin-views", "core", "test/sync-plugin-views.test.sh", "bash", "test/sync-plugin-views.test.sh"),
    _suite("release-flow", "core", "test/release-flow.test.sh", "bash", "test/release-flow.test.sh"),
    _suite("release-boundary", "core", "test/release-boundary.test.sh", "bash", "test/release-boundary.test.sh"),
    _suite("release-preflight", "core", "test/release-preflight.test.py", "python3", "test/release-preflight.test.py"),
    _suite("native-marketplace-adapters", "core", "test/native-marketplace-adapters.test.sh", "bash", "test/native-marketplace-adapters.test.sh"),
    _suite("marketplace-package", "core", "test/marketplace-package.test.py", "python3", "test/marketplace-package.test.py"),
    _suite("marketplace-host-isolation", "core", "test/marketplace-host-isolation.test.py", "python3", "test/marketplace-host-isolation.test.py"),
    _suite("installed-skill-invocation", "core", "test/installed-skill-invocation.test.py", "python3", "test/installed-skill-invocation.test.py"),
    _suite("prompt-marketplace-contract", "core", "test/prompt-marketplace-contract.test.py", "python3", "test/prompt-marketplace-contract.test.py"),
    _suite("skill-frontmatter", "core", "test/skill-frontmatter.test.js", "node", "test/skill-frontmatter.test.js"),
    _suite("scaffold-skill", "core", "test/scaffold-skill.test.sh", "bash", "test/scaffold-skill.test.sh"),
    _suite("marketplace-run", "core", "test/marketplace-run.test.sh", "bash", "test/marketplace-run.test.sh"),
    _suite("install-targets", "core", "test/install-targets.test.sh", "bash", "test/install-targets.test.sh"),
    _suite("install-arbitrary-skill", "core", "test/install-arbitrary-skill.test.sh", "bash", "test/install-arbitrary-skill.test.sh"),
    _suite("install-status-uninstall", "core", "test/install-status-uninstall.test.sh", "bash", "test/install-status-uninstall.test.sh"),
    _suite("improve", "core", "test/improve.test.sh", "bash", "test/improve.test.sh"),
    _suite("improve-plugin", "core", "test/improve-plugin.test.py", "python3", "test/improve-plugin.test.py"),
    _suite("improve-agent", "core", "test/improve-agent.test.py", "python3", "test/improve-agent.test.py"),
    _suite("improve-runtime", "core", "test/improve-runtime.test.py", "python3", "test/improve-runtime.test.py"),
    _suite("improve-route", "core", "test/improve-route.test.py", "python3", "-B", "test/improve-route.test.py"),
    _suite("until-loop-vendor", "core", "test/until-loop-vendor.test.py", "python3", "test/until-loop-vendor.test.py"),
    _suite("review-coverage", "core", "test/review-coverage.test.sh", "bash", "test/review-coverage.test.sh"),
    _suite("rubric-eval", "core", "test/rubric-eval.test.py", "python3", "test/rubric-eval.test.py"),
    _suite("dual-body-guard", "core", "test/dual-body-guard.test.sh", "bash", "test/dual-body-guard.test.sh"),
    _suite("plan-dispatcher-state", "core", "test/plan-dispatcher-state.test.js", "node", "test/plan-dispatcher-state.test.js"),
    _suite("plan-dispatcher-harness", "core", "test/plan-dispatcher-harness.test.js", "node", "--test", "test/plan-dispatcher-harness.test.js", groups=("agent-harness", "in-parallel")),
    _suite("plan-dispatcher-cli", "core", "test/plan-dispatcher-cli.test.js", "node", "test/plan-dispatcher-cli.test.js"),
    _suite("plan-dispatcher-progress", "core", "test/plan-dispatcher-progress.test.js", "node", "test/plan-dispatcher-progress.test.js"),
    _suite("plan-dispatcher-planning-context", "core", "test/plan-dispatcher-planning-context.test.js", "node", "test/plan-dispatcher-planning-context.test.js"),
    _suite("plan-dispatcher-compound", "core", "test/plan-dispatcher-compound.test.js", "node", "test/plan-dispatcher-compound.test.js"),
    _suite("plan-dispatcher-decisions", "core", "test/plan-dispatcher-decisions.test.js", "node", "test/plan-dispatcher-decisions.test.js"),
    _suite("plan-dispatcher-exact-calls", "core", "test/plan-dispatcher-exact-calls.test.js", "node", "test/plan-dispatcher-exact-calls.test.js"),
    _suite("plan-dispatcher-scenarios", "core", "test/plan-dispatcher-scenarios.test.js", "node", "test/plan-dispatcher-scenarios.test.js"),
    _suite("plan-dispatcher-mutants", "core", "test/plan-dispatcher-mutants.test.py", "python3", "test/plan-dispatcher-mutants.test.py"),
    _suite("native-setup-pilot", "core", "test/native-setup-pilot.test.py", "python3", "-B", "test/native-setup-pilot.test.py"),
)

SHIPLOOP_SUITES = tuple(_shiploop(path) for path in _SHIPLOOP_PATHS)

_APPARATUS_SUITE = _suite(
    "shiploop-e2e-apparatus",
    "e2e-apparatus",
    "skills/shiploop-e2e-audit/harness/check_suite.py",
    "python3",
    "-B",
    "skills/shiploop-e2e-audit/harness/check_suite.py",
    "--suite",
    "all",
    "--skill-root",
    "skills/shiploop",
    # Release runs took 14:49 to 18:19 on the CI runner and one hit 1,200 s on 2026-10-10 (a slow runner, same code: its rerun passed in
    # 20 min including setup). A ceiling, not a tuning value: the job's own limit is 60 minutes.
    timeout_seconds=1_800,
)

# The apparatus's no-model replay slice: captured agent results drive the real
# navigator, and each stage, action, owner and status must match its fixture.
# It takes seconds, so quick runs it for every change; full also runs it
# inside the apparatus's ``--suite all``.
_MOCK_REPLAY_SUITE = _suite(
    "shiploop-mock-replay",
    "e2e-apparatus",
    "skills/shiploop-e2e-audit/harness/check_suite.py",
    "python3",
    "-B",
    "skills/shiploop-e2e-audit/harness/check_suite.py",
    "--suite",
    "mock",
    "--skill-root",
    "skills/shiploop",
    timeout_seconds=300,
)

SUITES = (*_CORE_SUITES, *SHIPLOOP_SUITES, _MOCK_REPLAY_SUITE, _APPARATUS_SUITE)

GROUPS = (
    "all",
    "quick",
    "prompt",
    "core",
    "shiploop",
    "shiploop-1",
    "shiploop-2",
    "shiploop-3",
    "ask-agent",
    "agent-harness",
    "in-parallel",
    "shiploop-composition",
    "python-floor",
    "e2e-apparatus",
)

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _lpt_shards(suites: tuple[Suite, ...]) -> tuple[tuple[Suite, ...], ...]:
    """Use a deterministic longest-processing-time partition, then re-order.

    LPT decides ownership using descending committed timing estimates.  Each
    returned shard is subsequently filtered through the source inventory, so
    logs stay in the familiar catalog order while the shards remain balanced.
    """

    indexed = list(enumerate(suites))
    indexed.sort(key=lambda item: (-_DURATION_SECONDS.get(item[1].path, _FALLBACK_DURATION_SECONDS), item[0]))
    loads = [0.0] * SHIPLOOP_SHARD_COUNT
    members: list[set[str]] = [set() for _ in range(SHIPLOOP_SHARD_COUNT)]
    for original_index, suite in indexed:
        del original_index
        shard = min(range(SHIPLOOP_SHARD_COUNT), key=lambda index: (loads[index], index))
        members[shard].add(suite.id)
        loads[shard] += _DURATION_SECONDS.get(suite.path, _FALLBACK_DURATION_SECONDS)
    return tuple(tuple(suite for suite in suites if suite.id in member) for member in members)


SHIPLOOP_SHARDS = _lpt_shards(SHIPLOOP_SUITES)


def validate_catalog() -> None:
    """Reject accidental ambiguity before a runner can execute a suite."""

    identifiers = [suite.id for suite in SUITES]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("catalog contains duplicate suite ids")
    commands = [(suite.path, suite.argv) for suite in SUITES]
    if len(commands) != len(set(commands)):
        raise ValueError("catalog contains duplicate suite commands")
    if not all(suite.hermetic for suite in SUITES):
        raise ValueError("every catalog entry must be explicitly hermetic")
    for suite in SUITES:
        if not _ID_RE.fullmatch(suite.id):
            raise ValueError(f"invalid suite id: {suite.id}")
        if suite.family not in {"core", "shiploop", "e2e-apparatus"}:
            raise ValueError(f"invalid suite family: {suite.family}")
        if not suite.argv or suite.argv[0] not in {"python3", "node", "bash"}:
            raise ValueError(f"unsupported fixed command for {suite.id}")
        if suite.path not in suite.argv or not suite.path.startswith(("test/", "skills/")):
            raise ValueError(f"catalog path is not fixed in command for {suite.id}")
        if suite.timeout_seconds <= 0:
            raise ValueError(f"non-positive timeout for {suite.id}")
    shard_ids = [suite.id for shard in SHIPLOOP_SHARDS for suite in shard]
    if len(shard_ids) != len(SHIPLOOP_SUITES) or set(shard_ids) != {suite.id for suite in SHIPLOOP_SUITES}:
        raise ValueError("ShipLoop shard partition is not exhaustive and disjoint")
    missing_costs = {suite.path for suite in SHIPLOOP_SUITES} - _DURATION_SECONDS.keys()
    if missing_costs:
        raise ValueError("ShipLoop suites need explicit scheduling costs: " + ", ".join(sorted(missing_costs)))
    if any(not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0
           for value in _DURATION_SECONDS.values()):
        raise ValueError("suite scheduling costs must be finite non-negative seconds")
    over_budget = {suite.id for suite in SUITES if _light(suite)
                   and _DURATION_SECONDS.get(suite.path, 0.0) > QUICK_MAX_SECONDS}
    if over_budget - _QUICK_OVER_BUDGET_IDS:
        raise ValueError("quick costs need an explicit coverage decision: " +
                         ", ".join(sorted(over_budget - _QUICK_OVER_BUDGET_IDS)))
    # A renamed suite would otherwise drop out of a selection rule without a word.
    named = {*_QUICK_CORE_IDS, *_HUB_SUITE_IDS, *_SHIPLOOP_PROMPT_IDS, *_SHIPLOOP_PACKET_IDS,
             *_FULL_ONLY_IDS, *_QUICK_OVER_BUDGET_IDS,
             *(i for ids in _PATH_SUITE_IDS.values() for i in ids),
             *(i for ids in _PREFIX_SUITE_IDS.values() for i in ids)}
    unknown = named - set(identifiers)
    if unknown:
        raise ValueError("selection rules name unknown suites: " + ", ".join(sorted(unknown)))


# ---------------------------------------------------------------- quick tier
#
# The quick tier is what an ordinary push or pull request runs: a small fixed
# baseline plus the suites that match the changed files. Eligibility is explicit:
# the seven existing full-only suites stay full-only when timings are refreshed.
# QUICK_MAX_SECONDS audits new costs; it does not silently change selection.

QUICK_MAX_SECONDS = 120.0
_FULL_ONLY_IDS = frozenset({
    "plan-dispatcher-mutants", "shiploop-full-runtime", "shiploop-workspace",
    "shiploop-e2e-test-adequacy", "shiploop-e2e-ticket-sla", "shiploop-e2e-user-directory",
    "shiploop-e2e-apparatus",
})
# These previously eligible suites exceeded the old two-minute estimate in the
# full CI receipt recorded in suite_durations.json. Keep their coverage, explicitly.
# A new over-budget suite requires a full-only decision or a documented exception.
_QUICK_OVER_BUDGET_IDS = frozenset({
    "shiploop-navigator-contract", "shiploop-actual-improve-cli", "shiploop-loops",
    "shiploop-test-loop", "shiploop-keepalive", "shiploop-skill-calls",
    "shiploop-e2e-slice", "shiploop-e2e-chess-salesforce", "shiploop-e2e-platform",
    "shiploop-e2e-stages", "shiploop-e2e-stage-live", "shiploop-e2e-brownfield-tickets",
    "shiploop-callback-contract",
})
_QUICK_CORE_IDS = frozenset({"test-groups", "ci-policy", "skill-frontmatter", "shiploop-mock-replay"})

# Repository files whose suites a name match would not find.
_PATH_SUITE_IDS = {
    "test/suite_durations.json": ("test-groups", "ci-policy"),
    "install.sh": ("install-targets", "install-arbitrary-skill", "install-status-uninstall"),
    "scripts/build-packages.py": ("marketplace-package",),
    "scripts/check-release-boundary.py": ("release-boundary",),
    "scripts/release-push.py": ("release-push",),
    "catalog/external-plugins.json": ("marketplace-package", "native-marketplace-adapters"),
    "catalog/skill-craft-plugin.json": ("marketplace-package", "native-marketplace-adapters", "release-flow"),
    # The E2E spec has three logical readers; the original harness suite is now three components.
    "test/shiploop_e2e/SPEC.md": (*_E2E_SPLIT_IDS, "shiploop-navigator-contract", "shiploop-run-review"),
    # The packet obligation ledger and its checker; the code that writes the text its anchors live in is in
    # _SHIPLOOP_PACKET_SOURCES.
    "test/shiploop_e2e/packet_obligations.json": ("shiploop-packet-obligations",),
    "test/shiploop_e2e/obligations.py": ("shiploop-packet-obligations",),
    # Conservative named readers, including fixtures (test-economy review 2026-10-17, row 1).
    "test/shiploop_e2e/LEARNINGS.md": (*_E2E_SPLIT_IDS, "release-preflight", "shiploop-actual-improve-cli"),
    "test/shiploop_e2e/baselines.jsonl": ("shiploop-e2e-baseline", "shiploop-e2e-platform", *_E2E_SPLIT_IDS,
                                      "shiploop-e2e-epoch"),
    # The workspace module is driven through the CLI by the return-review, handoff and knowledge suites (row 3).
    "skills/shiploop/scripts/shiploop_workspace.py": ("shiploop-return-review", "shiploop-handoff", "shiploop-knowledge"),
    # The navigator is a hub, so its edit selects the hub consumers; the seam's equivalence with complete is pinned by one
    # suite that no hub rule finds.
    "skills/shiploop/scripts/shiploop_navigator.py": ("shiploop-seed-seam",),
    # The prompt module is a hub too; which stages print the Backchain check line or the audit line is pinned by one light
    # suite no hub rule finds (release 2.26.2: a prompts edit passed quick and failed CI there).
    "skills/shiploop/scripts/shiploop_prompts.py": ("shiploop-backchain-check",),
}

# Paths whose row above is their whole selection, beside the suite that carries their own name: the wider rule that
# would otherwise run is skipped, because it only adds suites that do not read them.  For the two data files that rule
# is the E2E prefix (the whole family, about 616 s of catalog estimate, for a journal or a data push); for the workspace
# module it is the hub fallback (nine consumers, one more than HUB_REFERENCE_LIMIT, so the hub set ran in their place
# and none of the suites that drive the module).  A new suite that reads one of these files is added to its row; the
# E2E README.md, cases.json, suites.json and packet_changes.json stay on the prefix, because the family reads them
# through a path helper, run.py and render_diff.py, which no file-name search sees.
_ROW_ONLY_PATHS = frozenset({
    *_E2E_TEST_PATHS,
    "test/shiploop_e2e/LEARNINGS.md",
    "test/shiploop_e2e/baselines.jsonl",
    "skills/shiploop/scripts/shiploop_workspace.py",
})

# Every E2E harness component that the catalog holds (shiploop-e2e-<topic> files; the
# apparatus is another family and not a ShipLoop suite).  Read from the catalog, so a group that adds a family suite is
# selected without a second list here; test-groups pins the family as it stands.
_E2E_FAMILY_IDS = tuple(suite.id for suite in SHIPLOOP_SUITES
                        if suite.id.startswith("shiploop-e2e-"))
# Shared fixtures and compatibility exports are consumed across this family.
# The old aggregate stem also targeted the full-only apparatus; preserve that mapping.
_PATH_SUITE_IDS.update({path: (*_E2E_FAMILY_IDS, _APPARATUS_SUITE.id) for path in _E2E_TEST_PATHS})

# The public skill composes the existing adapter suites without renaming persisted schemas.
_IN_PARALLEL_IDS = tuple(suite.id for suite in SUITES if "in-parallel" in suite.groups)

# Directories whose files have names too common to select by (run.py, hosts.py), and the leaf whose
# ShipLoop-family suite its name does not select (the leaf-name rule skips that family).  A new leaf's
# package build is its release gate, so the Run Review leaf also selects marketplace-package.  Each family
# suite reads the harness's modules (run.py, metrics.py) itself, so an edit of one runs them all: the 18 family suites
# sum to about 668 s of the estimates in _DURATION_SECONDS on 2026-10-18 (shiploop-e2e 100, -chess-salesforce 115,
# -slice 81, -platform 75, -environment 65, -battleship-salesforce 45, -quality 43, -release-slice 37, -baseline 25,
# -commit-counters 24.5, -sf-guard 20, the other seven 38 together); it was about 182 s for five suites on 2026-10-09.  Two data files are the exception, see _ROW_ONLY_PATHS.
_PREFIX_SUITE_IDS = {
    "test/fixtures/backchain-chunks/": ("backchain-chunks",),
    "test/fixtures/native-setup-pilot/": ("native-setup-pilot",),
    "skills/in-parallel/": (*_IN_PARALLEL_IDS, "marketplace-package"),
    "test/experiments/in_parallel_queue/": ("in-parallel-queue-audit",),
    "agents/in-parallel.md": (*_IN_PARALLEL_IDS, "marketplace-package"),
    "test/shiploop_e2e/": _E2E_FAMILY_IDS,
    # The committed output of `run.py --baseline-report` and the script that cut its fixtures: the baseline suite pins both.
    "docs/experiments/baseline-spread-20261009/": ("shiploop-e2e-baseline",),
    # The packets and commits regrade of the saved runs, its mutation record and the script that wrote them.
    "docs/experiments/commit-baseline-20261010/": ("shiploop-e2e-commit-counters",),
    # The saved pass-1 and pass-2 living files of the ticket pair and the delta ledgers cut from them, and the script that cut them.
    "docs/experiments/multipass-20261031/": ("shiploop-e2e-delta",),
    # The real pass-1 living files chain B's words and ledger patterns were written from, and the script that cut them.
    "docs/experiments/multipass-chain-b-20261101/": ("shiploop-e2e-user-directory",),
    "docs/experiments/incremental-feature-chain-20261101/": ("shiploop-e2e-incremental-pilot",),
    "docs/experiments/user-listing-chain-20261101/": ("shiploop-e2e-user-chain",),
    # The frozen record shapes the Run Review tests read (figures.json) and the scripts that cut them: the Run Review suite pins both.
    "docs/experiments/run-review-r22c-20261009/": ("shiploop-run-review",),
    "docs/experiments/run-review-r23-20261009/": ("shiploop-run-review",),
    # Frozen extracts of saved runs, each read by the one family suite named here (their file names select nothing).
    "test/fixtures/baseline-spread/": ("shiploop-e2e-baseline",),
    "test/fixtures/fidelity/": ("shiploop-e2e-fidelity",),
    "test/fixtures/reorientation/": ("shiploop-e2e-reorientation",),
    "test/fixtures/e2e-environment/": ("shiploop-e2e-environment",),
    "test/fixtures/quality/": ("shiploop-e2e-quality", "shiploop-e2e-brownfield", "shiploop-e2e-brownfield-tickets",
                               "shiploop-e2e-test-adequacy", "shiploop-e2e-ticket-comments", "shiploop-e2e-ticket-sla",
                               "shiploop-e2e-user-chain", "shiploop-e2e-user-directory"),
    "test/fixtures/commit-counters/": ("shiploop-e2e-commit-counters",),
    # The two saved-run extracts the efficiency measurement reads, and the journal rows its test checks.
    "test/fixtures/efficiency/": ("shiploop-e2e-efficiency",),
    "docs/experiments/shiploop-eff-journal-rows/": ("shiploop-efficiency-journal",),
    "docs/shiploop-efficiency-journal-": ("shiploop-efficiency-journal",),
    # Any ShipLoop text may gain a domain word or bring back a retired term: the denylist lint (about 3 s) and the
    # glossary's retired-term scan (under 1 s) read the whole skill folder.
    "skills/shiploop/": ("shiploop-domain-words", "shiploop-retired-terms"),
    # The Improve skill's ShipLoop route files are text a ShipLoop child reads, scanned for retired terms too.
    "skills/improve/references/shiploop-": ("shiploop-retired-terms",),
    "skills/shiploop-run-review/": ("shiploop-run-review", "marketplace-package"),
    # The vendored Until Loop runtime: one suite pins its provenance and hashes, one starts it from a read-only installed
    # copy. Their file names select nothing, so an edit of the runtime ran neither (the stop-rule branch's F2).
    "skills/improve/runtime/until-loop/": ("until-loop-vendor", "installed-skill-invocation"),
}


def _light(suite: Suite) -> bool:
    """Quick/prompt eligibility, independent of refreshed scheduling costs."""
    return suite.id not in _FULL_ONLY_IDS


def _stem(path: str) -> str:
    """A file name as a suite-id stem: shiploop_keepalive.py -> shiploop-keepalive."""

    name = PurePosixPath(path).name
    for suffix in (".test.py", ".test.cjs", ".test.js", ".test.sh"):
        name = name.removesuffix(suffix)
    return PurePosixPath(name).stem.replace("_", "-").lower()


def _prefixed(stem: str, suites: Iterable[Suite]) -> set[str]:
    return {suite.id for suite in suites if suite.id == stem or suite.id.startswith(stem + "-")}


# File names that say nothing about which suite covers them.  plan, review and spec join the list because frozen
# evidence and fixtures carry them (PLAN.md, SPEC.md, review.json, frames/plan.txt: 56 tracked files, all but two
# of them not read by the suites those names matched), and a name match would run eight plan-dispatcher suites, or
# shiploop-e2e, shiploop-navigator-contract and shiploop-run-review, for a push that edits one.  The two real files
# are named explicitly in _PATH_SUITE_IDS and _PREFIX_SUITE_IDS.  shiploop joins the list because the baseline-report
# fixtures carry nineteen frozen copies of the CLI entry, each named shiploop, and a name match ran all seventy-one
# ShipLoop suites (about nineteen minutes) for a push that edits one; the real entry is the leaf's own file name, which the
# leaf rule already skips, and _SHIPLOOP_WIDE_PATHS selects its hub consumers.
_GENERIC_STEMS = frozenset({"skill", "readme", "changelog", "license", "--init--", "plan", "review", "spec", "shiploop"})

_ROOT = Path(__file__).resolve().parents[1]

# The packet-size suites: each renders packets offline and holds their heads under the cut, in order and complete
# (about 25 s together).  A prompt or packet source change is the edit most likely to break them, yet the hub rule
# selected none of them for shiploop_prompts.py: on 2026-10-25 two quick runs after a step-plan prompt edit missed them,
# and a third, wider run caught a head over its cut.
PACKET_SIZE_IDS = (
    "shiploop-packet-completeness",
    "shiploop-step-packets",
    "shiploop-packet-recut",
    "shiploop-head-order",
)

# The code that writes packet text: the prompt catalog, the navigator that assembles each packet, the stage spec
# that orders the stages, and the loop and narrative text the packet obligation ledger anchors in.  Each selects the
# packet-size suites and the ledger beside whatever its name or the hub rule selects.
#
# Assumptions (guarded by PacketSourceSelectionTest in test/test-groups.test.py; change one only with its guard):
# - Every module that writes packet text is listed here.  A new one that is not stays unguarded on a quick run.
# - The hub rule replaces a hub's consumers with _HUB_SUITE_IDS, so the packet suites reach a packet edit only through
#   this explicit list.  Folding this rule into the hub rule, or dropping a module from it, brings back the
#   2026-10-25 miss.
# - The ledger travels with the packet-size suites: its anchors are literal phrases of the prompt text, which a
#   rewrap can split (2.11.0), while the packet-size suites check only sizes and order.
# - Rules only add suites.  targeted() is a union, so this rule never removes a suite another rule selected.
_SHIPLOOP_PACKET_SOURCES = frozenset({
    "skills/shiploop/scripts/shiploop_prompts.py",
    "skills/shiploop/scripts/shiploop_navigator.py",
    "skills/shiploop/scripts/shiploop_stage_spec.py",
    "skills/shiploop/scripts/shiploop_loops.py",
    "skills/shiploop/scripts/shiploop_narrative.py",
})
_SHIPLOOP_PACKET_IDS = (*PACKET_SIZE_IDS, "shiploop-packet-obligations")

# ShipLoop's prompt surface: the skill card, its references and its commands
# reach models through packets that these suites render and check.
_SHIPLOOP_PROMPT_IDS = (
    "shiploop-package-integrity",
    "shiploop-guidance",
    "shiploop-reference-routing",
    "shiploop-delegation",
    "shiploop-packet-bounds",
    *PACKET_SIZE_IDS,
    "shiploop-reference",
    "shiploop-navigator-dry-run",
)
_SHIPLOOP_PROMPT_PREFIXES = ("skills/shiploop/references/", "skills/shiploop/commands/")

# The ShipLoop entrypoint and the protocol module it hands every command to;
# every CLI suite runs through them, and no file name finds those suites.
_SHIPLOOP_WIDE_PATHS = frozenset({
    "skills/shiploop/scripts/shiploop",
    "skills/shiploop/scripts/shiploop_protocol.py",
})

# A file most suites reference (the navigator, the store, the prompt catalog,
# the CLI entrypoint) is a hub: selecting every consumer runs most of ShipLoop
# for any edit.  A hub selects this fixed set of its representative consumers
# instead; the full tier on release commits still runs everything.
HUB_REFERENCE_LIMIT = 8
_HUB_SUITE_IDS = (
    "shiploop-delegation",
    "shiploop-lint",
    "shiploop-actual-improve-cli",
    "shiploop-guidance",
    "shiploop-quality",
    "shiploop-store",
    "shiploop-privacy",
    "shiploop-keepalive",
    "shiploop-planning-handoff",
)

# Code paths whose names suites mention; a document's name says nothing.
_REFERENCE_PREFIXES = ("skills/", "agents/", "scripts/", "test/")


@cache
def _suite_sources() -> dict[str, str]:
    """Each suite's source text plus the test helper modules it imports by name."""

    helpers = {
        path.stem: path.read_text(errors="ignore")
        for path in (_ROOT / "test").glob("*.py")
        if not path.name.endswith(".test.py")
    }
    sources = {}
    for suite in SUITES:
        path = _ROOT / suite.path
        text = path.read_text(errors="ignore") if path.is_file() else ""
        text += "".join(body for stem, body in helpers.items()
                        if re.search(rf"\b{re.escape(stem)}\b", text))
        sources[suite.id] = text
    # Splitting one suite must preserve its reference selection and hub weight.
    # Any constituent reference selects all three, as the old aggregate did.
    e2e_text = "\n".join(sources[identifier] for identifier in _E2E_SPLIT_IDS)
    for identifier in _E2E_SPLIT_IDS:
        sources[identifier] = e2e_text
    return sources


def _referencing(path: str) -> set[str]:
    """Suites whose source names the changed file (a module name or a file name).

    Only code paths qualify; a document's name (docs/notes.md) says nothing
    about coverage.  Names without a separator (run.py, the bare shiploop
    entrypoint) are too common to mean anything and select nothing here.
    """

    if not path.startswith(_REFERENCE_PREFIXES):
        return set()
    name = PurePosixPath(path).name
    token = PurePosixPath(name).stem if name.endswith(".py") else name
    if _stem(path) in _GENERIC_STEMS or not re.search(r"[_.-]", token):
        return set()
    pattern = re.compile(rf"(?<![\w.-]){re.escape(token)}(?![\w-])")
    return {identifier for identifier, text in _suite_sources().items() if pattern.search(text)}


def targeted(changed: Iterable[str]) -> set[str]:
    """Suite ids that a set of changed repository paths points at.

    A changed suite runs itself.  A changed file selects the suites named after
    it (shiploop_navigator.py selects its consumers).  A change under
    skills/<leaf>/, agents/<leaf>.md or changes/<leaf>/ selects the core suites
    named after the leaf, except ShipLoop's, whose leaf name prefixes every
    one of its suites.  A changed file also
    selects the suites whose source names it, so a shared module such as
    shiploop_navigator.py or a test helper reaches its consumers; a hub that more
    than HUB_REFERENCE_LIMIT suites reference, and ShipLoop's entrypoint, select
    the fixed hub consumer set instead.  ShipLoop's prompt surface selects the
    packet suites, and a packet source the packet-size suites, whatever the hub
    rule picks.  A path in _ROW_ONLY_PATHS selects its row, and nothing from
    the prefix, consumer or hub rules.
    """

    ids: set[str] = set()
    for path in changed:
        parts = PurePosixPath(path).parts
        if not parts:
            continue
        row_only = path in _ROW_ONLY_PATHS
        ids.update(suite.id for suite in SUITES if suite.path == path)
        ids.update(_PATH_SUITE_IDS.get(path, ()))
        for prefix, prefixed_ids in _PREFIX_SUITE_IDS.items():
            if path.startswith(prefix) and not row_only:
                ids.update(prefixed_ids)
        leaf = None
        if parts[0] in ("skills", "changes") and len(parts) > 2:
            leaf = parts[1]
        elif parts[0] == "agents" and len(parts) == 2:
            leaf = PurePosixPath(parts[1]).stem
        stem = _stem(path)
        if stem and stem != leaf and stem not in _GENERIC_STEMS:
            ids.update(_prefixed(stem, SUITES))
        if leaf:
            ids.update(_prefixed(leaf, (suite for suite in SUITES if suite.family != "shiploop")))
        if path not in {suite.path for suite in SUITES} and not row_only:
            consumers = _referencing(path)
            logical_count = len(consumers - set(_E2E_SPLIT_IDS)) + bool(consumers.intersection(_E2E_SPLIT_IDS))
            ids.update(consumers if logical_count <= HUB_REFERENCE_LIMIT else _HUB_SUITE_IDS)
        if path == "skills/shiploop/SKILL.md" or path.startswith(_SHIPLOOP_PROMPT_PREFIXES):
            ids.update(_SHIPLOOP_PROMPT_IDS)
        if path in _SHIPLOOP_PACKET_SOURCES:
            ids.update(_SHIPLOOP_PACKET_IDS)
        if path in _SHIPLOOP_WIDE_PATHS:
            ids.update(_HUB_SUITE_IDS)
    return ids


def quick(changed: Iterable[str] = ()) -> tuple[Suite, ...]:
    """The quick tier: the fixed baseline plus light suites matching the changed paths."""

    ids = set(_QUICK_CORE_IDS) | {suite.id for suite in SHIPLOOP_SUITES if "quick" in suite.groups}
    ids |= targeted(changed)
    return tuple(suite for suite in SUITES if suite.id in ids and _light(suite))


def prompt(changed: Iterable[str] = ()) -> tuple[Suite, ...]:
    """The prompt tier: the packet suites plus the light suites whose own files changed.

    The packet suites are the packet-size suites and the obligation ledger, whose
    anchors are literal phrases in the prompt text: the 2.11.0 release failed CI
    there after a rewrap split one across two source lines, while the four
    packet-size suites passed locally.  It is the local loop for a prompt or
    packet edit, about 25 s; quick stays the gate before a push.

    Assumptions: it is never a gate (it leaves out the hub consumers that quick
    adds), and like quick it runs only light suites, so a changed heavy suite
    waits for the full tier.
    """

    paths = set(changed)
    ids = set(_SHIPLOOP_PACKET_IDS) | {suite.id for suite in SUITES if suite.path in paths}
    if paths.intersection(_E2E_TEST_PATHS):
        ids.update(_E2E_SPLIT_IDS)
    return tuple(suite for suite in SUITES if suite.id in ids and _light(suite))


def select(groups: Iterable[str], changed: Iterable[str] = ()) -> tuple[Suite, ...]:
    """Return the deduplicated union in catalog order for named local groups.

    ``changed`` (repository-relative paths) only affects the quick and prompt groups.
    """

    requested = tuple(groups)
    unknown = set(requested) - set(GROUPS)
    if unknown:
        raise ValueError("unknown test group: " + ", ".join(sorted(unknown)))
    if not requested or "all" in requested:
        return SUITES
    selected: set[str] = set()
    for group in requested:
        if group == "quick":
            selected.update(suite.id for suite in quick(changed))
        elif group == "prompt":
            selected.update(suite.id for suite in prompt(changed))
        elif group.startswith("shiploop-") and group[-1:] in {"1", "2", "3"}:
            selected.update(suite.id for suite in SHIPLOOP_SHARDS[int(group[-1]) - 1])
        else:
            selected.update(
                suite.id for suite in SUITES
                if suite.family == group or group in suite.groups
            )
    return tuple(suite for suite in SUITES if suite.id in selected)


validate_catalog()
