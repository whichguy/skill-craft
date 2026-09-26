#!/usr/bin/env python3
"""The one declarative inventory for the repository's hermetic checks.

The shell entrypoints deliberately contain no test membership.  Keeping that
membership here lets local component runs, quick, full qualification and CI
shards answer the same question without maintaining parallel lists.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
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
_SHIPLOOP_PATHS = (
    "test/shiploop-no-model-launch.test.py",
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
    "test/shiploop-status-display.test.py",
    "test/shiploop-auth-readiness.test.py",
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
    "test/shiploop-improve-schedule.test.py",
    "test/shiploop-lint.test.py",
    "test/shiploop-quality.test.py",
    "test/shiploop-test-loop.test.py",
    "test/shiploop-test-counts.test.py",
    "test/shiploop-improve-changes.test.py",
    "test/shiploop-knowledge.test.py",
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
    "test/shiploop-keepalive.test.py",
    "test/shiploop-planning-handoff.test.py",
    "test/shiploop-package-integrity.test.py",
    "test/shiploop-e2e.test.py",
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
    "test/shiploop-literal-transport.test.py": 2.548,
    "test/shiploop-capability-fixture.test.py": 67.625,
    "test/shiploop-probe-decisions.test.py": 1.175,
    "test/shiploop-stopped-improve.test.py": 1.27,
    "test/shiploop-actual-improve-cli.test.py": 45.762,
    "test/shiploop-local-skills.test.py": 1.983,
    "test/shiploop-navigator-dry-run.test.py": 3.603,
    "test/shiploop-cross-run.test.py": 20.313,
    "test/shiploop-chain-git.test.py": 27.248,
    "test/shiploop-chain-lifecycle.test.py": 803.023,
    "test/shiploop-chain-planning-context.test.py": 118.442,
    "test/experiments/shiploop_chain/test_native_pilot.py": 72.521,
    "test/shiploop-store.test.py": 0.015,
    "test/shiploop-discovery.test.py": 10.128,
    "test/shiploop-generalized-discovery.test.py": 23.84,
    "test/shiploop-repeatable-experiments.test.py": 21.134,
    "test/shiploop-privacy.test.py": 0.002,
    "test/shiploop-reference-routing.test.py": 2.666,
    "test/shiploop-no-model-launch.test.py": 4.064,
    "test/shiploop-navigator-v4.test.py": 3.337,
    "test/shiploop-standalone-improve.test.py": 2.811,
    "test/shiploop-v3-guidance.test.py": 4.581,
    "test/shiploop-full-runtime.test.py": 156.431,
    "test/shiploop-chain-ledger.test.py": 0.34,
    "test/shiploop-chain-handoff.test.py": 0.758,
    "test/shiploop-planning-context.test.py": 0.976,
    "test/experiments/shiploop_chain/test_grok_trace.py": 0.178,
    "test/shiploop-consumer-delivery-cli.test.py": 4.374,
    "test/shiploop-delegation.test.py": 3.445,
    "test/shiploop-improve-schedule.test.py": 0.2,
    "test/shiploop-lint.test.py": 36.0,
    "test/shiploop-quality.test.py": 5.0,
    "test/shiploop-test-loop.test.py": 3.0,
    "test/shiploop-test-counts.test.py": 0.2,
    "test/shiploop-improve-changes.test.py": 1.5,
    "test/shiploop-knowledge.test.py": 1.0,
    "test/shiploop-assumptions.test.py": 0.2,
    "test/experiments/shiploop_delivery/browser_consumer/serve_fixture.test.py": 2.53,
    "test/shiploop-capability-runtime.test.py": 0.996,
    "test/shiploop-planning-handoff.test.py": 0.2,
    "test/shiploop-package-integrity.test.py": 0.2,
    "test/shiploop-e2e.test.py": 0.7,
}
_FALLBACK_DURATION_SECONDS = 60.0

# The quick tier's fixed ShipLoop baseline: fast graph, packet and boundary checks.
_QUICK_PATHS = frozenset({
    "test/shiploop-no-model-launch.test.py",
    "test/shiploop-navigator-v3.test.py",
    "test/shiploop-navigator-v4.test.py",
    "test/shiploop-stopped-improve.test.py",
    "test/shiploop-v4-consumers.test.py",
    "test/shiploop-packet-bounds.test.py",
    "test/shiploop-navigator-dry-run.test.py",
    "test/shiploop-status-display.test.py",
    "test/shiploop-chain-async.test.py",
    "test/shiploop-planning-handoff.test.py",
})

# Current Ask-Agent checks.  The adapter rows exercise the ShipLoop consumers
# that make the current helper contract material.
_ASK_AGENT_PATHS = frozenset({
    "test/experiments/shiploop_chain/test_native_pilot.py",
    "test/shiploop-chain-async.test.py",
    "test/shiploop-chain-handoff.test.py",
    "test/shiploop-consumer-delivery.test.py",
    "test/shiploop-consumer-delivery-cli.test.py",
})

_COMPOSITION_PATHS = frozenset({
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
    "test/shiploop-full-runtime.test.py",
    "test/shiploop-improve-schedule.test.py",
    "test/shiploop-planning-context.test.py",
    "test/shiploop-standalone-improve.test.py",
    "test/shiploop-stopped-improve.test.py",
})


def _shiploop(path: str) -> Suite:
    groups: set[str] = set()
    if path in _QUICK_PATHS:
        groups.add("quick")
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
    _suite("release-flow", "core", "test/release-flow.test.sh", "bash", "test/release-flow.test.sh"),
    _suite("release-boundary", "core", "test/release-boundary.test.sh", "bash", "test/release-boundary.test.sh"),
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
    _suite("review-coverage", "core", "test/review-coverage.test.sh", "bash", "test/review-coverage.test.sh"),
    _suite("dual-body-guard", "core", "test/dual-body-guard.test.sh", "bash", "test/dual-body-guard.test.sh"),
    _suite("plan-dispatcher-state", "core", "test/plan-dispatcher-state.test.js", "node", "test/plan-dispatcher-state.test.js"),
    _suite("plan-dispatcher-cli", "core", "test/plan-dispatcher-cli.test.js", "node", "test/plan-dispatcher-cli.test.js"),
    _suite("plan-dispatcher-progress", "core", "test/plan-dispatcher-progress.test.js", "node", "test/plan-dispatcher-progress.test.js"),
    _suite("plan-dispatcher-planning-context", "core", "test/plan-dispatcher-planning-context.test.js", "node", "test/plan-dispatcher-planning-context.test.js"),
    _suite("plan-dispatcher-compound", "core", "test/plan-dispatcher-compound.test.js", "node", "test/plan-dispatcher-compound.test.js"),
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
    "core",
    "shiploop",
    "shiploop-1",
    "shiploop-2",
    "shiploop-3",
    "ask-agent",
    "shiploop-composition",
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


# ---------------------------------------------------------------- quick tier
#
# The quick tier is what an ordinary push or pull request runs: a small fixed
# baseline plus the suites that match the changed files.  Suites measured above
# QUICK_MAX_SECONDS and the E2E apparatus run only in the full tier (release
# commits and manual dispatch).

QUICK_MAX_SECONDS = 120.0
_QUICK_CORE_IDS = frozenset({"test-groups", "ci-policy", "skill-frontmatter", "shiploop-mock-replay"})

# Repository files whose suites a name match would not find.
_PATH_SUITE_IDS = {
    "install.sh": ("install-targets", "install-arbitrary-skill", "install-status-uninstall"),
    "scripts/build-packages.py": ("marketplace-package",),
    "scripts/check-release-boundary.py": ("release-boundary",),
    "scripts/release-push.py": ("release-push",),
    "catalog/external-plugins.json": ("marketplace-package", "native-marketplace-adapters"),
    "catalog/skill-craft-plugin.json": ("marketplace-package", "native-marketplace-adapters", "release-flow"),
}

# Directories whose files have names too common to select by (run.py, hosts.py).
_PREFIX_SUITE_IDS = {
    "test/shiploop_e2e/": ("shiploop-e2e",),
}


def _light(suite: Suite) -> bool:
    return (suite.id != _APPARATUS_SUITE.id
            and _DURATION_SECONDS.get(suite.path, 0.0) <= QUICK_MAX_SECONDS)


def _stem(path: str) -> str:
    """A file name as a suite-id stem: shiploop_keepalive.py -> shiploop-keepalive."""

    name = PurePosixPath(path).name
    for suffix in (".test.py", ".test.cjs", ".test.js", ".test.sh"):
        name = name.removesuffix(suffix)
    return PurePosixPath(name).stem.replace("_", "-").lower()


def _prefixed(stem: str, suites: Iterable[Suite]) -> set[str]:
    return {suite.id for suite in suites if suite.id == stem or suite.id.startswith(stem + "-")}


# File names that say nothing about which suite covers them.
_GENERIC_STEMS = frozenset({"skill", "readme", "changelog", "license", "--init--"})

_ROOT = Path(__file__).resolve().parents[1]

# ShipLoop's prompt surface: the skill card, its references and its commands
# reach models through packets that these suites render and check.
_SHIPLOOP_PROMPT_IDS = (
    "shiploop-package-integrity",
    "shiploop-v3-guidance",
    "shiploop-reference-routing",
    "shiploop-delegation",
    "shiploop-packet-bounds",
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
    "shiploop-v3-guidance",
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
    it (shiploop_chain.py selects the shiploop-chain suites).  A change under
    skills/<leaf>/, agents/<leaf>.md or changes/<leaf>/ selects the core suites
    named after the leaf, except ShipLoop's, whose leaf name prefixes every
    one of its suites.  A changed file also
    selects the suites whose source names it, so a shared module such as
    shiploop_navigator.py or a test helper reaches its consumers; a hub that more
    than HUB_REFERENCE_LIMIT suites reference, and ShipLoop's entrypoint, select
    the fixed hub consumer set instead.  ShipLoop's prompt surface selects the
    packet suites.
    """

    ids: set[str] = set()
    for path in changed:
        parts = PurePosixPath(path).parts
        if not parts:
            continue
        ids.update(suite.id for suite in SUITES if suite.path == path)
        ids.update(_PATH_SUITE_IDS.get(path, ()))
        for prefix, prefixed_ids in _PREFIX_SUITE_IDS.items():
            if path.startswith(prefix):
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
        if path not in {suite.path for suite in SUITES}:
            consumers = _referencing(path)
            ids.update(consumers if len(consumers) <= HUB_REFERENCE_LIMIT else _HUB_SUITE_IDS)
        if path == "skills/shiploop/SKILL.md" or path.startswith(_SHIPLOOP_PROMPT_PREFIXES):
            ids.update(_SHIPLOOP_PROMPT_IDS)
        if path in _SHIPLOOP_WIDE_PATHS:
            ids.update(_HUB_SUITE_IDS)
    return ids


def quick(changed: Iterable[str] = ()) -> tuple[Suite, ...]:
    """The quick tier: the fixed baseline plus light suites matching the changed paths."""

    ids = set(_QUICK_CORE_IDS) | {suite.id for suite in SHIPLOOP_SUITES if "quick" in suite.groups}
    ids |= targeted(changed)
    return tuple(suite for suite in SUITES if suite.id in ids and _light(suite))


def select(groups: Iterable[str], changed: Iterable[str] = ()) -> tuple[Suite, ...]:
    """Return the deduplicated union in catalog order for named local groups.

    ``changed`` (repository-relative paths) only affects the quick group.
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
        elif group.startswith("shiploop-") and group[-1:] in {"1", "2", "3"}:
            selected.update(suite.id for suite in SHIPLOOP_SHARDS[int(group[-1]) - 1])
        else:
            selected.update(
                suite.id for suite in SUITES
                if suite.family == group or group in suite.groups
            )
    return tuple(suite for suite in SUITES if suite.id in selected)


validate_catalog()
