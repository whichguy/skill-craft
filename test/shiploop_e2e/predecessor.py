"""Frozen, receipt-bound predecessor deliveries for registered incremental comparisons.

This module restores only the committed product history archived by delivery/work.bundle. The reviewer receipt is
required input and is never inferred or created here.
"""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import delivery
import metrics
import scorecard


DIMENSIONS = (
    "requested_behavior", "prior_behavior", "decision_handling",
    "knowledge_and_organization", "workflow_and_lineage",
)
BRANCH = "e2e-predecessor"
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _json(path: Path, name: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise ValueError(f"{name} is unreadable: {error}") from None
    if not isinstance(value, dict):
        raise ValueError(f"{name} must contain an object")
    return value


def _receipt_digest(receipt: dict) -> str:
    try:
        body = {key: value for key, value in receipt.items() if key != "sha256"}
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError(f"receipt is not a valid scorecard.run_receipt value: {error}") from None
    return hashlib.sha256(encoded).hexdigest()


def _canonical_run(value) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("predecessor run must be a canonical absolute path")
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("predecessor run must be an absolute path")
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValueError("predecessor run does not exist") from None
    if not resolved.is_dir() or str(resolved) != value:
        raise ValueError("predecessor run must be a canonical absolute existing run directory")
    return resolved


def _validate_receipt(receipt) -> tuple[dict, str, str, str]:
    if not isinstance(receipt, dict) or receipt.get("observed") is not True:
        raise ValueError("predecessor receipt is not an observed scorecard.run_receipt")
    if receipt.get("sha256") != _receipt_digest(receipt):
        raise ValueError("predecessor receipt sha256 does not match its scorecard.run_receipt contents")
    if receipt.get("missing") or receipt.get("unsafe_symlinks"):
        raise ValueError("predecessor receipt has missing or unsafe inputs")
    selected_run = receipt.get("selected_run")
    if (not isinstance(selected_run, dict) or selected_run.get("observed") is not True
            or not isinstance(selected_run.get("path"), str) or not Path(selected_run["path"]).is_absolute()):
        raise ValueError("predecessor receipt has no bound selected run")
    product = receipt.get("product")
    if not isinstance(product, dict) or product.get("observed") is not True:
        raise ValueError("predecessor receipt has no observed product fingerprint")
    head, tree = product.get("head"), product.get("tree")
    if not isinstance(head, str) or not head or not isinstance(tree, str) or not tree:
        raise ValueError("predecessor receipt product needs a non-empty HEAD and tree")
    if product.get("status") != []:
        raise ValueError("predecessor product is not clean")
    files = receipt.get("files")
    selector_sha = files.get("shiploop-run.json") if isinstance(files, dict) else None
    if not isinstance(selector_sha, str) or not SHA256.fullmatch(selector_sha):
        raise ValueError("predecessor receipt does not include the shiploop-run.json digest")
    bundle = files.get(delivery.BUNDLE) if isinstance(files, dict) else None
    if not isinstance(bundle, str) or not SHA256.fullmatch(bundle):
        raise ValueError("predecessor receipt does not include the delivery/work.bundle digest")
    receipt_sha = receipt.get("sha256")
    if not isinstance(receipt_sha, str) or not SHA256.fullmatch(receipt_sha):
        raise ValueError("predecessor receipt sha256 is malformed")
    return product, receipt_sha, bundle, head


def _validate_manual_review(review, receipt_sha: str) -> None:
    if not isinstance(review, dict):
        raise ValueError("predecessor entry needs an embedded manual review")
    reviewer = review.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("predecessor review needs a non-blank reviewer")
    if review.get("receipt_sha256") != receipt_sha:
        raise ValueError("predecessor review is not bound to the receipt sha256")
    dimensions = review.get("dimensions")
    if not isinstance(dimensions, dict) or set(dimensions) != set(DIMENSIONS):
        raise ValueError("predecessor review must contain exactly the five requested dimensions")
    for name in DIMENSIONS:
        dimension = dimensions[name]
        evidence = dimension.get("evidence") if isinstance(dimension, dict) else None
        if (not isinstance(dimension, dict) or dimension.get("status") != "pass"
                or not isinstance(evidence, list) or not evidence
                or any(not isinstance(item, str) or not item.strip() for item in evidence)):
            raise ValueError(f"predecessor review dimension {name!r} needs pass status and non-blank evidence")


def _validate_delivery_records(run: Path, product: dict) -> dict:
    result = _json(run / "result.json", "predecessor result.json")
    delivery_record = result.get("delivery")
    if not isinstance(delivery_record, dict):
        raise ValueError("predecessor result.json has no delivery record")
    for phase in ("before", "after"):
        snapshot = delivery_record.get(phase)
        if not isinstance(snapshot, dict) or snapshot.get("observed") is not True:
            raise ValueError(f"predecessor delivery {phase} snapshot is not observed")
        if any(snapshot.get(name) != product.get(name) for name in ("head", "tree")):
            raise ValueError(f"predecessor delivery {phase} HEAD/tree differs from its receipt product")
        if snapshot.get("status") != []:
            raise ValueError(f"predecessor delivery {phase} snapshot is not clean")
    before = delivery_record["before"]
    if before.get("bundle") != delivery.BUNDLE:
        raise ValueError("predecessor result does not name delivery/work.bundle")
    return result


def _fresh_receipt(run: Path) -> dict:
    try:
        return scorecard.run_receipt(run)
    except Exception as error:
        raise ValueError(f"predecessor scorecard.run_receipt could not be observed: {error}") from None


def validate_entry(entry, expected_case: str, *, observe: bool = True) -> None:
    """Validate one frozen run, its recorded manual review, and optionally its fresh scorecard evidence."""
    if not isinstance(entry, dict) or set(entry) != {"run", "receipt", "review"}:
        raise ValueError("predecessor entry must contain exactly run, receipt, and review")
    run = _canonical_run(entry.get("run"))
    if not isinstance(expected_case, str) or not expected_case.strip():
        raise ValueError("expected predecessor case must be a non-blank string")
    product, receipt_sha, _bundle_sha, _head = _validate_receipt(entry.get("receipt"))
    _validate_manual_review(entry.get("review"), receipt_sha)
    result = _validate_delivery_records(run, product)
    if result.get("case") != expected_case:
        raise ValueError(f"predecessor run case is {result.get('case')!r}, expected {expected_case!r}")
    if result.get("pass") is not True:
        raise ValueError("predecessor run did not pass")
    if not observe:
        return

    fresh = _fresh_receipt(run)
    if fresh != entry["receipt"]:
        raise ValueError("predecessor run receipt changed since registration")
    card = scorecard.score(run)
    if not isinstance(card, dict) or card.get("observed") is not True:
        raise ValueError("predecessor scorecard is not observed")
    accuracy = card.get("accuracy") if isinstance(card.get("accuracy"), dict) else {}
    fidelity = card.get("fidelity") if isinstance(card.get("fidelity"), dict) else {}
    validity = card.get("validity") if isinstance(card.get("validity"), dict) else {}
    correctness = validity.get("correctness") if isinstance(validity.get("correctness"), dict) else {}
    if accuracy.get("floor") != scorecard.PASS:
        raise ValueError("predecessor fresh scorecard accuracy floor did not pass")
    if fidelity.get("floor") != scorecard.PASS:
        raise ValueError("predecessor fresh scorecard fidelity floor did not pass")
    if correctness.get("valid") is not True:
        raise ValueError("predecessor fresh scorecard correctness is not valid")


def validate_registration(reg, *, observe: bool = True) -> None:
    """Require one reviewed predecessor exactly for each frozen case that follows another case."""
    if not isinstance(reg, dict):
        raise ValueError("registration must be an object")
    qualification = reg.get("qualification")
    frozen_cases = qualification.get("cases") if isinstance(qualification, dict) else None
    if not isinstance(frozen_cases, dict):
        raise ValueError("registration has no frozen qualification cases")
    follows = {}
    for name, frozen in frozen_cases.items():
        if not isinstance(name, str) or not name or not isinstance(frozen, dict):
            raise ValueError("registration has a malformed frozen case")
        followed = frozen.get("follows")
        if followed is None:
            continue
        if not isinstance(followed, str) or not followed.strip():
            raise ValueError(f"frozen case {name!r} has a malformed follows value")
        if "base" in frozen and frozen.get("base") is not None:
            raise ValueError(f"frozen case {name!r} cannot have both base and follows")
        follows[name] = followed
    predecessors = reg.get("predecessors", {})
    if not isinstance(predecessors, dict):
        raise ValueError("registration predecessors must be a case-to-entry mapping")
    if set(predecessors) != set(follows):
        missing = sorted(set(follows) - set(predecessors))
        extra = sorted(set(predecessors) - set(follows))
        detail = []
        if missing:
            detail.append("missing " + ", ".join(missing))
        if extra:
            detail.append("unexpected " + ", ".join(map(str, extra)))
        raise ValueError("registration predecessors do not exactly cover frozen follows cases" +
                         (": " + "; ".join(detail) if detail else ""))
    for case, expected_case in follows.items():
        validate_entry(predecessors[case], expected_case, observe=observe)


@contextmanager
def _safe_git_environment():
    """A Git environment with inherited redirects/config/templates removed and hooks disabled."""
    with tempfile.TemporaryDirectory(prefix="shiploop-e2e-empty-git-template-") as template:
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update({
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TEMPLATE_DIR": template,
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.hooksPath",
            "GIT_CONFIG_VALUE_0": os.devnull,
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_OPTIONAL_LOCKS": "0",
        })
        yield env


def _git(work: Path, *args: str, env) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(work), *args], capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, env=env)


def _follow_on(entry: dict, result: dict, product: dict, receipt_sha: str, bundle_sha: str) -> dict:
    earlier_metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    earlier_cli = result.get("cli") if isinstance(result.get("cli"), dict) else {}
    reported = result.get("metrics") if isinstance(result.get("metrics"), dict) else earlier_cli
    return {
        "prior": entry["run"], "start_head": product["head"],
        "prior_case": result.get("case"), "prior_pass": result.get("pass"),
        "prior_turns": (earlier_metrics or earlier_cli).get("turns") or earlier_cli.get("num_turns"),
        "prior_cost_usd": (earlier_metrics or earlier_cli).get("cost_usd"),
        "prior_lower_bound": metrics.lower_bound(reported),
        "registered_predecessor": {
            "receipt_sha256": receipt_sha, "bundle_sha256": bundle_sha,
            "head": product["head"], "tree": product["tree"],
        },
    }


def restore(entry, work: Path, expected_case: str) -> dict:
    """Restore the frozen committed predecessor into an empty work folder and bind the follow-on record to it."""
    validate_entry(entry, expected_case, observe=True)
    target = Path(work)
    if target.is_symlink() or not target.is_dir():
        raise ValueError("predecessor work destination must be an existing empty directory")
    try:
        if next(target.iterdir(), None) is not None:
            raise ValueError("predecessor work destination must be empty")
        target.rmdir()
    except OSError as error:
        raise ValueError(f"predecessor work destination could not be removed: {error}") from None

    product, receipt_sha, bundle_sha, head = _validate_receipt(entry["receipt"])
    run = Path(entry["run"])
    result = _json(run / "result.json", "predecessor result.json")
    with _safe_git_environment() as env:
        try:
            delivery.restore(run, target, head, git_env=env)
        except Exception:
            # Preserve any clone output as evidence for the caller.
            raise
        switched = _git(target, "checkout", "-q", "-B", BRANCH, head, env=env)
        if switched.returncode != 0:
            raise RuntimeError("could not create the fixed predecessor branch: " + switched.stderr.strip()[:240])
        configured = _git(target, "config", "--local", "core.hooksPath", os.devnull, env=env)
        if configured.returncode != 0:
            raise RuntimeError("could not disable hooks in the restored product: " + configured.stderr.strip()[:240])
        restored = delivery.fingerprint(target, git_env=env)
        if (restored.get("observed") is not True or restored.get("head") != product["head"]
                or restored.get("tree") != product["tree"] or restored.get("status") != []):
            raise ValueError("restored predecessor does not match its clean receipt product fingerprint")

    fresh = _fresh_receipt(run)
    if fresh != entry["receipt"]:
        raise ValueError("predecessor run receipt or delivery bundle changed during restore")
    try:
        current_bundle = hashlib.sha256((run / delivery.BUNDLE).read_bytes()).hexdigest()
    except OSError as error:
        raise ValueError(f"predecessor delivery bundle could not be rechecked after restore: {error}") from None
    if current_bundle != bundle_sha:
        raise ValueError("predecessor delivery bundle changed during restore")
    return _follow_on(entry, result, product, receipt_sha, bundle_sha)


def _binding(entry: dict) -> dict:
    product, receipt_sha, bundle_sha, _head = _validate_receipt(entry["receipt"])
    return {"receipt_sha256": receipt_sha, "bundle_sha256": bundle_sha,
            "head": product["head"], "tree": product["tree"]}


def _check_ancestry(output: Path, final_head: str, predecessor_head: str) -> str | None:
    """Prove ancestry from the receipt-bound delivery archive, never the mutable live work/.git metadata."""
    bundle = output / delivery.BUNDLE
    receipt = _fresh_receipt(output)
    if receipt.get("observed") is not True:
        return "final run receipt is not observed, so its delivery bundle cannot prove ancestry"
    selected_run = receipt.get("selected_run")
    if (not isinstance(selected_run, dict) or selected_run.get("observed") is not True
            or not isinstance(selected_run.get("path"), str) or not Path(selected_run["path"]).is_absolute()):
        return "final run receipt has no bound selected run, so its delivery bundle cannot prove ancestry"
    if receipt.get("sha256") != _receipt_digest(receipt):
        return "final run receipt sha256 is malformed"
    files = receipt.get("files") if isinstance(receipt.get("files"), dict) else {}
    bundle_sha = files.get(delivery.BUNDLE)
    if not isinstance(bundle_sha, str) or not SHA256.fullmatch(bundle_sha):
        return "fresh final run receipt does not include the delivery/work.bundle digest"
    try:
        if hashlib.sha256(bundle.read_bytes()).hexdigest() != bundle_sha:
            return "final delivery bundle does not match its fresh run receipt digest"
    except OSError as error:
        return f"final delivery bundle cannot be read: {error}"
    with _safe_git_environment() as env:
        with tempfile.TemporaryDirectory(prefix="shiploop-e2e-final-product-") as scratch:
            final_work = Path(scratch) / "work"
            try:
                delivery.restore(output, final_work, final_head, git_env=env)
            except Exception as error:
                return f"final product HEAD cannot be restored from its delivery bundle: {error}"
            try:
                restored_bundle_sha = hashlib.sha256(bundle.read_bytes()).hexdigest()
            except OSError as error:
                return f"final delivery bundle cannot be rechecked after restore: {error}"
            if restored_bundle_sha != bundle_sha:
                return "final delivery bundle changed while its history was being restored"
            ancestor = _git(final_work, "merge-base", "--is-ancestor", predecessor_head, final_head, env=env)
            return None if ancestor.returncode == 0 else "registered predecessor HEAD is not an ancestor of final product HEAD"


def linkage_problems(entry, output: Path, expected_case: str) -> list[str]:
    """Report missing/tampered predecessor binding or a final product that does not extend the pinned history."""
    try:
        validate_entry(entry, expected_case, observe=True)
        expected_binding = _binding(entry)
        canonical_prior = entry["run"]
    except (ValueError, OSError, TypeError) as error:
        return [f"registered predecessor is invalid: {error}"]
    output = Path(output)
    problems: list[str] = []
    records = {}
    for name in ("invocation.json", "result.json"):
        try:
            records[name] = _json(output / name, name)
        except ValueError as error:
            problems.append(str(error))
    if len(records) != 2:
        return problems
    if records["invocation.json"].get("case") != records["result.json"].get("case"):
        problems.append("invocation.json and result.json identify different follow-on cases")
    expected = {
        "prior": canonical_prior, "prior_case": expected_case, "prior_pass": True,
        "start_head": expected_binding["head"], "registered_predecessor": expected_binding,
    }
    for filename, record in records.items():
        follow = record.get("follow_on")
        if not isinstance(follow, dict):
            problems.append(f"{filename} has no follow_on binding")
            continue
        for key, value in expected.items():
            actual = follow.get(key)
            matches = actual is True if key == "prior_pass" else actual == value
            if not matches:
                problems.append(f"{filename} follow_on.{key} does not match the registered predecessor")
    result = records["result.json"]
    delivery_record = result.get("delivery") if isinstance(result.get("delivery"), dict) else {}
    after = delivery_record.get("after") if isinstance(delivery_record.get("after"), dict) else {}
    final_head = after.get("head")
    if after.get("observed") is not True or not isinstance(final_head, str) or not final_head:
        problems.append("result.json has no observed final product HEAD")
    elif not any("registered predecessor is invalid" in item for item in problems):
        ancestry = _check_ancestry(output, final_head, expected_binding["head"])
        if ancestry:
            problems.append(ancestry)
    return problems
