#!/usr/bin/env python3
"""The one declarative inventory for the repository's hermetic checks.

The shell entrypoints deliberately contain no test membership.  Keeping that
membership here lets local component runs, smoke, full qualification and CI
shards answer the same question without maintaining parallel lists.
"""

from __future__ import annotations

from dataclasses import dataclass
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


# These paths were the ordered 101-entry ShipLoop inventory before this
# catalog was introduced.  Order remains meaningful for full local output and
# for deterministic component unions.
_SHIPLOOP_PATHS = (
    "test/shiploop-no-model-launch.test.py",
    "test/shiploop-navigator.test.py",
    "test/shiploop-navigator-v3.test.py",
    "test/shiploop-navigator-v4.test.py",
    "test/shiploop-stopped-improve.test.py",
    "test/shiploop-v4-consumers.test.py",
    "test/shiploop-standalone-improve.test.py",
    "test/shiploop-actual-improve-cli.test.py",
    "test/shiploop-packet-bounds.test.py",
    "test/shiploop-v3-guidance.test.py",
    "test/shiploop-local-skills.test.py",
    "test/experiments/shiploop_ui_allocation/test_evidence.py",
    "test/shiploop-full-runtime.test.py",
    "test/shiploop-navigator-dry-run.test.py",
    "test/shiploop-auth-readiness.test.py",
    "test/shiploop-environment-lifecycle.test.py",
    "test/shiploop-cross-run.test.py",
    "test/shiploop-workspace.test.py",
    "test/shiploop-chain-ledger.test.py",
    "test/shiploop-chain-git.test.py",
    "test/shiploop-chain.test.py",
    "test/shiploop-chain-handoff.test.py",
    "test/shiploop-chain-lifecycle.test.py",
    "test/shiploop-chain-async.test.py",
    "test/shiploop-planning-context.test.py",
    "test/shiploop-chain-planning-context.test.py",
    "test/experiments/shiploop_chain/test_trace.py",
    "test/experiments/shiploop_chain/test_grok_trace.py",
    "test/experiments/shiploop_chain/test_native_pilot.py",
    "test/shiploop-consumer-delivery.test.py",
    "test/shiploop-consumer-delivery-cli.test.py",
    "test/shiploop-delegation.test.py",
    "test/shiploop-delivery-prompts.test.py",
    "test/experiments/shiploop_delivery/fake_deployment.test.py",
    "test/experiments/shiploop_delivery/browser_consumer/serve_fixture.test.py",
    "test/improve-managed.test.py",
    "test/shiploop-graph-driver.test.py",
    "test/shiploop-graph-trace.test.py",
    "test/shiploop-store.test.py",
    "test/shiploop-evidence.test.py",
    "test/shiploop-file-safety.test.py",
    "test/shiploop-prompt-integrity.test.py",
    "test/shiploop-literal-transport.test.py",
    "test/shiploop-validators.test.py",
    "test/shiploop-discovery.test.py",
    "test/shiploop-capability-fixture.test.py",
    "test/shiploop-capability-runtime.test.py",
    "test/shiploop-generalized-discovery.test.py",
    "test/shiploop-probe-decisions.test.py",
    "test/shiploop-capability-async.test.cjs",
    "test/shiploop-repeatable-experiments.test.py",
    "test/shiploop-system-context.test.py",
    "test/shiploop-research-template.test.py",
    "test/shiploop-research-packet-protocol.test.py",
    "test/shiploop-question-resume.test.py",
    "test/shiploop-iteration-docs.test.py",
    "test/shiploop-iteration-docs-protocol.test.py",
    "test/shiploop-system-tests.test.py",
    "test/shiploop-system-tests-protocol.test.py",
    "test/shiploop-system-tests-report.test.py",
    "test/shiploop-history-policy.test.py",
    "test/shiploop-improve-policy.test.py",
    "test/shiploop-outer-work.test.py",
    "test/shiploop-outer-work-protocol.test.py",
    "test/shiploop-observations.test.py",
    "test/shiploop-observations-protocol.test.py",
    "test/shiploop-artifacts.test.py",
    "test/shiploop-artifact-consumers.test.py",
    "test/shiploop-privacy.test.py",
    "test/shiploop-revalidation.test.py",
    "test/shiploop-revalidation-context.test.py",
    "test/shiploop-risk.test.py",
    "test/shiploop-boundaries.test.py",
    "test/shiploop-objectives.test.py",
    "test/shiploop-contracts.test.py",
    "test/shiploop-contract-protocol.test.py",
    "test/shiploop-delivery.test.py",
    "test/shiploop-report.test.py",
    "test/shiploop-packets.test.py",
    "test/shiploop-orientation.test.py",
    "test/shiploop-loop-scope.test.py",
    "test/shiploop-orientation-context.test.py",
    "test/shiploop-orientation-integration.test.py",
    "test/shiploop-reference-routing.test.py",
    "test/shiploop-backchain-guidance.test.py",
    "test/shiploop-teachback.test.py",
    "test/shiploop-protocol.test.py",
    "test/shiploop-history-pages.test.py",
    "test/shiploop-merge-recovery.test.py",
    "test/shiploop-migration-prompt.test.py",
    "test/shiploop-knowledge.test.py",
    "test/shiploop-planning.test.py",
    "test/shiploop-until.test.py",
    "test/shiploop-step-planning.test.py",
    "test/shiploop-sdlc.test.py",
    "test/shiploop-improve-bridge.test.py",
    "test/shiploop-managed-contracts.test.py",
    "test/shiploop-invalidation.test.py",
    "test/shiploop-managed-invalidation.test.py",
    "test/shiploop-managed-package.test.py",
    "test/shiploop-managed-walk.test.py",
    "test/shiploop-action-walk.test.py",
)

# Measured in the audited full GitHub qualification.  Every known duration is
# committed as data so assigning a shard never depends on local history.  A
# deterministic fallback retains that property for a newly added suite until a
# later audit supplies an observed duration.
_DURATION_SECONDS = {
    "test/shiploop-navigator-v3.test.py": 2.793,
    "test/shiploop-v4-consumers.test.py": 1.048,
    "test/shiploop-packet-bounds.test.py": 0.167,
    "test/experiments/shiploop_ui_allocation/test_evidence.py": 0.602,
    "test/shiploop-auth-readiness.test.py": 29.207,
    "test/shiploop-workspace.test.py": 19.448,
    "test/shiploop-chain.test.py": 191.262,
    "test/shiploop-chain-async.test.py": 35.083,
    "test/experiments/shiploop_chain/test_trace.py": 0.701,
    "test/shiploop-consumer-delivery.test.py": 1.165,
    "test/experiments/shiploop_delivery/fake_deployment.test.py": 0.0,
    "test/shiploop-graph-driver.test.py": 2.836,
    "test/shiploop-evidence.test.py": 0.925,
    "test/shiploop-literal-transport.test.py": 2.548,
    "test/shiploop-capability-fixture.test.py": 67.625,
    "test/shiploop-probe-decisions.test.py": 1.175,
    "test/shiploop-system-context.test.py": 0.017,
    "test/shiploop-question-resume.test.py": 12.255,
    "test/shiploop-system-tests.test.py": 0.004,
    "test/shiploop-history-policy.test.py": 1.033,
    "test/shiploop-outer-work-protocol.test.py": 38.337,
    "test/shiploop-artifacts.test.py": 0.054,
    "test/shiploop-revalidation.test.py": 41.404,
    "test/shiploop-boundaries.test.py": 0.119,
    "test/shiploop-contract-protocol.test.py": 0.306,
    "test/shiploop-packets.test.py": 7.384,
    "test/shiploop-orientation-context.test.py": 3.482,
    "test/shiploop-backchain-guidance.test.py": 0.047,
    "test/shiploop-history-pages.test.py": 79.193,
    "test/shiploop-knowledge.test.py": 408.786,
    "test/shiploop-step-planning.test.py": 225.95,
    "test/shiploop-managed-contracts.test.py": 0.228,
    "test/shiploop-managed-package.test.py": 0.445,
    "test/shiploop-navigator.test.py": 70.283,
    "test/shiploop-stopped-improve.test.py": 1.27,
    "test/shiploop-actual-improve-cli.test.py": 45.762,
    "test/shiploop-local-skills.test.py": 1.983,
    "test/shiploop-navigator-dry-run.test.py": 3.603,
    "test/shiploop-cross-run.test.py": 20.313,
    "test/shiploop-chain-git.test.py": 27.248,
    "test/shiploop-chain-lifecycle.test.py": 803.023,
    "test/shiploop-chain-planning-context.test.py": 118.442,
    "test/experiments/shiploop_chain/test_native_pilot.py": 72.521,
    "test/shiploop-delivery-prompts.test.py": 0.011,
    "test/improve-managed.test.py": 0.191,
    "test/shiploop-store.test.py": 0.015,
    "test/shiploop-prompt-integrity.test.py": 14.67,
    "test/shiploop-discovery.test.py": 10.128,
    "test/shiploop-generalized-discovery.test.py": 23.84,
    "test/shiploop-repeatable-experiments.test.py": 21.134,
    "test/shiploop-research-packet-protocol.test.py": 101.999,
    "test/shiploop-iteration-docs-protocol.test.py": 3.329,
    "test/shiploop-system-tests-report.test.py": 0.045,
    "test/shiploop-outer-work.test.py": 17.47,
    "test/shiploop-observations-protocol.test.py": 8.609,
    "test/shiploop-privacy.test.py": 0.002,
    "test/shiploop-risk.test.py": 0.002,
    "test/shiploop-contracts.test.py": 0.013,
    "test/shiploop-report.test.py": 0.305,
    "test/shiploop-loop-scope.test.py": 4.815,
    "test/shiploop-reference-routing.test.py": 2.666,
    "test/shiploop-protocol.test.py": 38.278,
    "test/shiploop-migration-prompt.test.py": 10.946,
    "test/shiploop-until.test.py": 0.042,
    "test/shiploop-improve-bridge.test.py": 4.799,
    "test/shiploop-managed-invalidation.test.py": 0.404,
    "test/shiploop-action-walk.test.py": 1074.878,
    "test/shiploop-no-model-launch.test.py": 4.064,
    "test/shiploop-navigator-v4.test.py": 3.337,
    "test/shiploop-standalone-improve.test.py": 2.811,
    "test/shiploop-v3-guidance.test.py": 4.581,
    "test/shiploop-full-runtime.test.py": 156.431,
    "test/shiploop-environment-lifecycle.test.py": 95.288,
    "test/shiploop-chain-ledger.test.py": 0.34,
    "test/shiploop-chain-handoff.test.py": 0.758,
    "test/shiploop-planning-context.test.py": 0.976,
    "test/experiments/shiploop_chain/test_grok_trace.py": 0.178,
    "test/shiploop-consumer-delivery-cli.test.py": 4.374,
    "test/shiploop-delegation.test.py": 3.445,
    "test/experiments/shiploop_delivery/browser_consumer/serve_fixture.test.py": 2.53,
    "test/shiploop-graph-trace.test.py": 0.004,
    "test/shiploop-file-safety.test.py": 0.205,
    "test/shiploop-validators.test.py": 0.272,
    "test/shiploop-capability-runtime.test.py": 0.996,
    "test/shiploop-research-template.test.py": 0.011,
    "test/shiploop-iteration-docs.test.py": 0.02,
    "test/shiploop-system-tests-protocol.test.py": 1.134,
    "test/shiploop-improve-policy.test.py": 162.566,
    "test/shiploop-observations.test.py": 0.004,
    "test/shiploop-artifact-consumers.test.py": 16.37,
    "test/shiploop-revalidation-context.test.py": 4.355,
    "test/shiploop-objectives.test.py": 32.727,
    "test/shiploop-delivery.test.py": 0.422,
    "test/shiploop-orientation.test.py": 0.131,
    "test/shiploop-orientation-integration.test.py": 10.45,
    "test/shiploop-teachback.test.py": 7.609,
    "test/shiploop-merge-recovery.test.py": 8.123,
    "test/shiploop-planning.test.py": 761.391,
    "test/shiploop-sdlc.test.py": 0.034,
    "test/shiploop-invalidation.test.py": 0.008,
    "test/shiploop-managed-walk.test.py": 264.462,
}
_FALLBACK_DURATION_SECONDS = 60.0

_SMOKE_PATHS = frozenset({
    "test/shiploop-no-model-launch.test.py",
    "test/shiploop-navigator-v3.test.py",
    "test/shiploop-navigator-v4.test.py",
    "test/shiploop-stopped-improve.test.py",
    "test/shiploop-v4-consumers.test.py",
    "test/shiploop-packet-bounds.test.py",
    "test/shiploop-navigator-dry-run.test.py",
    "test/shiploop-chain-async.test.py",
    "test/shiploop-graph-driver.test.py",
    "test/shiploop-graph-trace.test.py",
})

# Current Ask-Agent checks are deliberately distinct from the retained U18 W1
# historical experiment.  The adapter rows exercise the ShipLoop consumers
# that make the current helper contract material.
_ASK_AGENT_PATHS = frozenset({
    "test/experiments/shiploop_chain/test_native_pilot.py",
    "test/shiploop-chain-async.test.py",
    "test/shiploop-chain-handoff.test.py",
    "test/shiploop-consumer-delivery.test.py",
    "test/shiploop-consumer-delivery-cli.test.py",
    "test/shiploop-delivery-prompts.test.py",
})

_COMPOSITION_PATHS = frozenset({
    "test/improve-managed.test.py",
    "test/shiploop-actual-improve-cli.test.py",
    "test/shiploop-chain-async.test.py",
    "test/shiploop-chain-git.test.py",
    "test/shiploop-chain-handoff.test.py",
    "test/shiploop-chain-ledger.test.py",
    "test/shiploop-chain-lifecycle.test.py",
    "test/shiploop-chain-planning-context.test.py",
    "test/shiploop-chain.test.py",
    "test/shiploop-consumer-delivery-cli.test.py",
    "test/shiploop-consumer-delivery.test.py",
    "test/shiploop-delegation.test.py",
    "test/shiploop-delivery-prompts.test.py",
    "test/shiploop-full-runtime.test.py",
    "test/shiploop-graph-driver.test.py",
    "test/shiploop-graph-trace.test.py",
    "test/shiploop-improve-bridge.test.py",
    "test/shiploop-improve-policy.test.py",
    "test/shiploop-managed-contracts.test.py",
    "test/shiploop-managed-invalidation.test.py",
    "test/shiploop-managed-package.test.py",
    "test/shiploop-managed-walk.test.py",
    "test/shiploop-planning-context.test.py",
    "test/shiploop-standalone-improve.test.py",
    "test/shiploop-stopped-improve.test.py",
})


def _shiploop(path: str) -> Suite:
    groups: set[str] = set()
    if path in _SMOKE_PATHS:
        groups.add("smoke")
    if path in _ASK_AGENT_PATHS:
        groups.add("ask-agent")
    if path in _COMPOSITION_PATHS:
        groups.add("shiploop-composition")
    interpreter = "node" if path.endswith(".cjs") else "python3"
    return _suite(_identifier(path), "shiploop", path, interpreter, path, groups=groups)


_CORE_SUITES = (
    _suite("test-groups", "core", "test/test-groups.test.py", "python3", "test/test-groups.test.py"),
    _suite("ci-policy", "core", "test/ci-policy.test.py", "python3", "test/ci-policy.test.py"),
    _suite("integration-boundaries", "core", "test/integration-boundaries.test.py", "python3", "test/integration-boundaries.test.py"),
    _suite("release-push", "core", "test/release-push.test.py", "python3", "test/release-push.test.py"),
    _suite("ask-agent-workspace", "core", "test/ask-agent-workspace.test.py", "python3", "test/ask-agent-workspace.test.py", groups=("ask-agent",)),
    _suite("ask-agent-delivery", "core", "test/ask-agent-delivery.test.py", "python3", "test/ask-agent-delivery.test.py", groups=("ask-agent",)),
    _suite("ask-agent-managed-harness", "core", "test/ask-agent-managed-harness.test.py", "python3", "test/ask-agent-managed-harness.test.py", groups=("ask-agent",)),
    _suite("skill-interop-hygiene", "core", "test/skill-interop-hygiene.test.sh", "bash", "test/skill-interop-hygiene.test.sh"),
    _suite("sync-plugin-views", "core", "test/sync-plugin-views.test.sh", "bash", "test/sync-plugin-views.test.sh"),
    _suite("native-marketplace-adapters", "core", "test/native-marketplace-adapters.test.sh", "bash", "test/native-marketplace-adapters.test.sh"),
    _suite("vendored-bundles", "core", "test/vendored-bundles.test.py", "python3", "test/vendored-bundles.test.py"),
    _suite("marketplace-package", "core", "test/marketplace-package.test.py", "python3", "test/marketplace-package.test.py"),
    _suite("marketplace-host-isolation", "core", "test/marketplace-host-isolation.test.py", "python3", "test/marketplace-host-isolation.test.py"),
    _suite("installed-skill-invocation", "core", "test/installed-skill-invocation.test.py", "python3", "test/installed-skill-invocation.test.py"),
    _suite("prompt-marketplace-contract", "core", "test/prompt-marketplace-contract.test.py", "python3", "test/prompt-marketplace-contract.test.py"),
    _suite("skill-frontmatter", "core", "test/skill-frontmatter.test.js", "node", "test/skill-frontmatter.test.js"),
    _suite("scaffold-skill", "core", "test/scaffold-skill.test.sh", "bash", "test/scaffold-skill.test.sh"),
    _suite("marketplace-run", "core", "test/marketplace-run.test.sh", "bash", "test/marketplace-run.test.sh"),
    _suite("install-targets", "core", "test/install-targets.test.sh", "bash", "test/install-targets.test.sh"),
    _suite("install-arbitrary-skill", "core", "test/install-arbitrary-skill.test.sh", "bash", "test/install-arbitrary-skill.test.sh"),
    _suite("hermes-binding", "core", "test/hermes-binding.test.sh", "bash", "test/hermes-binding.test.sh"),
    _suite("install-status-uninstall", "core", "test/install-status-uninstall.test.sh", "bash", "test/install-status-uninstall.test.sh"),
    _suite("devloop-run", "core", "test/devloop-run.test.sh", "bash", "test/devloop-run.test.sh"),
    _suite("evidence-gates", "core", "test/evidence-gates.test.sh", "bash", "test/evidence-gates.test.sh"),
    _suite("improve", "core", "test/improve.test.sh", "bash", "test/improve.test.sh"),
    _suite("improve-plugin", "core", "test/improve-plugin.test.py", "python3", "test/improve-plugin.test.py"),
    _suite("shiploop-testkit", "core", "test/shiploop-testkit.test.sh", "bash", "test/shiploop-testkit.test.sh"),
    _suite("review-coverage", "core", "test/review-coverage.test.sh", "bash", "test/review-coverage.test.sh"),
    _suite("dual-body-guard", "core", "test/dual-body-guard.test.sh", "bash", "test/dual-body-guard.test.sh"),
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
    timeout_seconds=1_200,
)

# This is a historical U18 W1 test-only operator experiment.  Its assertions
# remain useful, but it is not a current Ask-Agent smoke or core contract.
_EXPERIMENT_SUITES = (
    _suite(
        "ask-agent-worktree-harness",
        "experiments",
        "test/ask-agent-worktree-harness.test.py",
        "python3",
        "test/ask-agent-worktree-harness.test.py",
    ),
)

SUITES = (*_CORE_SUITES, *SHIPLOOP_SUITES, _APPARATUS_SUITE, *_EXPERIMENT_SUITES)

GROUPS = (
    "all",
    "smoke",
    "core",
    "shiploop",
    "shiploop-1",
    "shiploop-2",
    "shiploop-3",
    "ask-agent",
    "shiploop-composition",
    "e2e-apparatus",
    "experiments",
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
    paths = [suite.path for suite in SUITES]
    if len(paths) != len(set(paths)):
        raise ValueError("catalog contains duplicate suite paths")
    if not all(suite.hermetic for suite in SUITES):
        raise ValueError("every catalog entry must be explicitly hermetic")
    for suite in SUITES:
        if not _ID_RE.fullmatch(suite.id):
            raise ValueError(f"invalid suite id: {suite.id}")
        if suite.family not in {"core", "shiploop", "e2e-apparatus", "experiments"}:
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


def select(groups: Iterable[str]) -> tuple[Suite, ...]:
    """Return the deduplicated union in catalog order for named local groups."""

    requested = tuple(groups)
    unknown = set(requested) - set(GROUPS)
    if unknown:
        raise ValueError("unknown test group: " + ", ".join(sorted(unknown)))
    if not requested or "all" in requested:
        return SUITES
    selected: set[str] = set()
    for group in requested:
        if group == "smoke":
            selected.update(suite.id for suite in _CORE_SUITES)
            selected.update(suite.id for suite in SHIPLOOP_SUITES if "smoke" in suite.groups)
        elif group.startswith("shiploop-") and group[-1:] in {"1", "2", "3"}:
            selected.update(suite.id for suite in SHIPLOOP_SHARDS[int(group[-1]) - 1])
        else:
            selected.update(
                suite.id for suite in SUITES
                if suite.family == group or group in suite.groups
            )
    return tuple(suite for suite in SUITES if suite.id in selected)


validate_catalog()
