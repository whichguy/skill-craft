"""Read causal Improve evidence from the run bind and runtime pass snapshots."""
from __future__ import annotations

import io
import json
import os
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

import common

GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
_TREE = re.compile(r"^[0-9a-f]{40,64}$")
_TEST = re.compile(r"(^|/)(test|tests|__tests__)/|\.test\.|\.spec\.|_test\.")
_TEST_CHECK = re.compile(r"(?i)(--test\b|\bnpm\s+test\b|\bpytest\b|\bjest\b)")
_PASS = re.compile(r"pass-([1-9][0-9]*)\.json$")
_BINDING_MARKER = "ShipLoop standalone Improve binding: "
SUPPORTED_CASES = frozenset({"node-seeded-case-compare", "node-seeded-numeric-sort",
                             "node-seeded-empty-guard", "node-seeded-early-validation"})
# These seeded work-item reviews can begin at step-plan before the item implementation exists. Later Improve stages
# inspect work already present in the item and cannot infer not-applicable from a missing module.
PRE_IMPLEMENTATION_STAGES = frozenset({"step-plan"})


def _git(repo: Path, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, env=GIT_ENV, timeout=timeout)


def _json(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _slug(stage: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", stage.lower()).strip("-") or "stage"


def _fixture_paths(case: dict) -> list[str]:
    """Files that differ between the seeded defect's naive and fixed references."""
    seeded = case.get("seeded_defect") or {}
    root = common.FIXTURES / str(seeded.get("tree") or "")
    naive, fixed = root / "naive", root / "fixed"
    if not naive.is_dir() or not fixed.is_dir():
        return []
    left = {path.relative_to(naive).as_posix(): path for path in naive.rglob("*") if path.is_file()}
    right = {path.relative_to(fixed).as_posix(): path for path in fixed.rglob("*") if path.is_file()}
    return sorted(path for path in left.keys() | right.keys()
                  if not _TEST.search(path)
                  and (path not in left or path not in right or left[path].read_bytes() != right[path].read_bytes()))


def _review_actions(sample: Path, run_dir: Path) -> tuple[list[dict], str | None]:
    """Reviews on the seeded work item, from its seed action onward, linked by state and binding marker."""
    invocation = _json(Path(sample) / "invocation.json")
    state = common.read_block(run_dir / "state.md")
    if invocation is None or not isinstance(state, dict):
        return [], "run invocation or state record is missing or unreadable"
    seeded = invocation.get("seeded")
    seed_action = seeded.get("action") if isinstance(seeded, dict) else None
    if not isinstance(seed_action, str) or not seed_action:
        return [], "seeded action is missing from the invocation"
    history = state.get("history")
    if not isinstance(history, list):
        return [], "run state has no action history"
    start = next((i for i, row in enumerate(history)
                  if isinstance(row, dict) and row.get("action") == seed_action), None)
    if start is None:
        return [], f"seeded action {seed_action!r} is not linked from run history"
    workitem = history[start].get("workitem")
    if workitem is None:
        scoped_history = history[start:start + 1]
    elif isinstance(workitem, str) and workitem:
        scoped_history = history[start:]
    else:
        return [], "seeded action has malformed work-item linkage"
    results = state.get("improve_results")
    if not isinstance(results, dict):
        return [], "run state has no Improve result links"
    rows = []
    for item in scoped_history:
        if not isinstance(item, dict) or item.get("workitem") != workitem:
            continue
        action = item.get("action")
        record = results.get(action) if isinstance(action, str) else None
        if not isinstance(record, dict):
            continue
        # Seeded navigation may install synthetic predecessor records. A real Improve import has both fields.
        improve_action = record.get("improve_action")
        if improve_action is None and record.get("binding_id") is None:
            continue
        if not isinstance(improve_action, str) or not isinstance(record.get("binding_id"), str):
            return [], f"Improve link for action {action!r} is incomplete"
        run_id = state.get("run_id")
        binding_id = f"{run_id}/{action}"
        if record.get("binding_id") != binding_id:
            return [], f"Improve binding for action {action!r} does not match the run/action link"
        if record.get("stage") != item.get("stage"):
            return [], f"Improve stage for action {action!r} conflicts with run history"
        rows.append({"action": action, "stage": item.get("stage"), "workitem": workitem,
                     "improve_action": improve_action, "binding_id": binding_id})
    if not rows:
        return [], f"no action-linked Improve records exist for seeded work item {workitem!r}"
    return rows, None


def _linked_start(worktree: Path, record: dict) -> tuple[Path | None, str | None]:
    action = record["action"]
    expected = record["binding_id"]
    runtime_root = worktree / ".shiploop-improve"
    if not runtime_root.is_dir():
        return None, "Improve runtime directory is missing"
    matched = []
    suffix_candidates = []
    for path in runtime_root.glob("*/start.json"):
        if path.is_symlink() or not path.is_file():
            continue
        data = _json(path)
        context = data.get("context") if isinstance(data, dict) else None
        request = context.get("request") if isinstance(context, dict) else None
        markers = [line[len(_BINDING_MARKER):] for line in request.splitlines()
                   if line.startswith(_BINDING_MARKER)] if isinstance(request, str) else []
        if path.parent.name.endswith(action[-8:]):
            suffix_candidates.append((path, markers))
        if markers == [expected]:
            matched.append(path)
    if len(matched) > 1:
        return None, f"ambiguous action-linked Improve directories for action {action}"
    if not matched:
        if any(not markers for _path, markers in suffix_candidates):
            return None, f"Improve action linkage is unreadable or ambiguous for action {action}"
        return None, f"no start packet links Improve action to reviewed action {action}"
    start = matched[0]
    expected_dir = f"{_slug(str(record['stage']))}-{action[-8:]}"
    if start.parent.name != expected_dir:
        return None, f"Improve start directory {start.parent.name!r} does not match action/stage linkage"
    data = _json(start)
    if not isinstance(data, dict):
        return None, f"Improve start packet for action {action} is unreadable"
    context = data.get("context")
    request = context.get("request") if isinstance(context, dict) else None
    if not isinstance(request, str) or request.splitlines().count(_BINDING_MARKER + record["binding_id"]) != 1:
        return None, f"Improve start packet for action {action} has no unique binding marker"
    return start.parent, None


def _pass_rows(reviews: Path, bind_tree: str, repo: Path) -> tuple[list[dict], str | None]:
    found = []
    for path in reviews.glob("pass-*.json"):
        match = _PASS.fullmatch(path.name)
        if match:
            found.append((int(match.group(1)), path))
    found.sort()
    if not found:
        return [], "Improve review has no recorded pass snapshots"
    if [n for n, _ in found] != list(range(1, found[-1][0] + 1)):
        return [], "Improve pass snapshot sequence has a gap"
    rows = []
    previous = bind_tree
    for number, path in found:
        item = _json(path)
        if not isinstance(item, dict) or item.get("pass") != number:
            return [], f"Improve pass {number} record is missing or malformed"
        tree, changed, commit = item.get("tree"), item.get("changed"), item.get("commit", object())
        if not isinstance(tree, str) or not _TREE.fullmatch(tree) or not isinstance(changed, bool):
            return [], f"Improve pass {number} lacks a resolvable tree/change snapshot"
        if "commit" not in item or (commit is not None and not isinstance(commit, str)):
            return [], f"Improve pass {number} lacks its commit field"
        if changed != (tree != previous):
            return [], f"Improve pass {number} changed flag conflicts with its adjacent tree snapshots"
        if commit is not None:
            resolved = _git(repo, "rev-parse", "--verify", commit + "^{commit}")
            full = resolved.stdout.decode("ascii", "replace").strip()
            if resolved.returncode or not full.startswith(commit):
                return [], f"Improve pass {number} commit {commit!r} is not resolvable"
        rows.append({"pass": number, "tree": tree, "changed": changed, "commit": commit})
        previous = tree
    return rows, None


def _review_inputs(sample: Path, case: dict, worktree: Path) -> tuple[list[dict], str | None, list[str]]:
    run_dir = common.run_dir(sample)
    if run_dir is None or not run_dir.is_dir():
        return [], "run directory is missing", []
    if not worktree.is_dir():
        return [], "final worktree is missing", []
    required = _fixture_paths(case)
    if not required:
        return [], "seeded defect fixture has no changed product paths", []
    actions, why = _review_actions(sample, run_dir)
    if why:
        return [], why, required
    rows = []
    repo = worktree.resolve()
    for action in actions:
        bind_path = run_dir / "improve" / (action["action"] + "-bind.md")
        if bind_path.is_symlink() or not bind_path.is_file():
            return [], f"Improve bind snapshot is missing for action {action['action']}", required
        bind = common.read_block(bind_path)
        if not isinstance(bind, dict):
            return [], f"Improve bind snapshot is unreadable for action {action['action']}", required
        if not isinstance(bind.get("tree"), str) or not _TREE.fullmatch(bind["tree"]):
            return [], f"Improve bind tree is missing or malformed for action {action['action']}", required
        if os.path.realpath(str(bind.get("toplevel") or "")) != os.path.realpath(str(repo)):
            return [], f"Improve bind worktree conflicts with the sample worktree for action {action['action']}", required
        prefix = bind.get("prefix")
        if not isinstance(prefix, str) or Path(prefix).is_absolute() or ".." in Path(prefix).parts:
            return [], f"Improve bind scope prefix is invalid for action {action['action']}", required
        start_dir, why = _linked_start(worktree, action)
        if why:
            return [], why, required
        passes, why = _pass_rows(start_dir / "reviews", bind["tree"], repo)
        if why:
            return [], f"action {action['action']}: {why}", required
        rows.append({**action, "repo": repo, "prefix": prefix, "bind_tree": bind["tree"],
                     "passes": passes})
    return rows, None, required


def _extract_archive(repo: Path, prefix: str, tree: str, destination: Path) -> Path | None:
    archived = _git(repo, "archive", tree, timeout=60)
    if archived.returncode:
        return None
    root = destination.resolve()
    try:
        with tarfile.open(fileobj=io.BytesIO(archived.stdout), mode="r:") as archive:
            for member in archive.getmembers():
                target = (root / member.name).resolve()
                if target != root and root not in target.parents:
                    return None
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    source = archive.extractfile(member)
                    if source is None:
                        return None
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(source.read())
                elif member.issym():
                    link_target = (target.parent / member.linkname).resolve()
                    if link_target != root and root not in link_target.parents:
                        return None
                    target.parent.mkdir(parents=True, exist_ok=True)
                    os.symlink(member.linkname, target)
                else:
                    return None
    except (OSError, tarfile.TarError):
        return None
    target = root if prefix == "." else root / prefix
    return target if target.is_dir() else None


def _diff_paths(repo: Path, before: str, after: str) -> list[str] | None:
    result = _git(repo, "diff-tree", "-r", "-z", "--no-renames", "--name-only", before, after)
    if result.returncode:
        return None
    return sorted(value.decode("utf-8", "surrogateescape")
                  for value in result.stdout.split(b"\0") if value)


def _probe(case: dict, tree: Path) -> dict | None:
    import seeded_defects  # noqa: PLC0415
    try:
        return seeded_defects.score(case, tree)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        return None


def _probe_state(case: dict, tree: Path) -> dict | None:
    """Return a usable probe even when a separate test command fails in an intermediate snapshot."""
    result = _probe(case, tree)
    if not isinstance(result, dict) or not isinstance(result.get("present"), bool):
        return None
    probes, checks = result.get("probes"), result.get("checks")
    if not isinstance(probes, list) or not probes or not isinstance(checks, list) or not checks:
        return None
    if any(not isinstance(row, dict) or not isinstance(row.get("pass"), bool)
           or not isinstance(row.get("exit"), int) for row in probes):
        return None
    behavior_checks = [row for row in checks
                       if isinstance(row, dict) and isinstance(row.get("command"), str)
                       and not _TEST_CHECK.search(row["command"])]
    if not behavior_checks or any(not isinstance(row.get("pass"), bool)
                                  or not isinstance(row.get("exit"), int) for row in behavior_checks):
        return None
    return {**result, "behavior_checks_pass": all(row["pass"] for row in behavior_checks),
            "checks_pass": all(isinstance(row, dict) and row.get("pass") is True for row in checks),
            "behavior_checks": behavior_checks}


def _module_paths(required: list[str]) -> list[str]:
    """Known Node resolution layout for the seeded source module and its index.js relocation."""
    paths = set(required)
    for relative in required:
        path = Path(relative)
        if path.suffix == ".js":
            paths.add((path.parent / path.stem / "index.js").as_posix())
    return sorted(paths)


def _module_missing(state: dict | None) -> bool:
    """A pre-implementation skip requires positive module-resolution evidence, not just a failed probe."""
    if state is None or state.get("behavior_checks_pass"):
        return False
    outputs = [str(row.get("output") or "") for row in state.get("behavior_checks", [])]
    return bool(outputs) and all(re.search(r"Cannot find module|ERR_MODULE_NOT_FOUND|MODULE_NOT_FOUND", text)
                                  for text in outputs)


def _run_test(tree: Path, paths: list[str]) -> dict:
    if not paths:
        return {"test": None, "passes_after": False, "fails_before_fix": False}
    command = "node --test " + " ".join(shlex.quote(path) for path in paths)
    result = common.sh(command, tree)
    return {"test": command, "passes_after": result["exit"] == 0, "output": result["output"]}


def _basket_counterfactual(case: dict, snapshot: Path, destination: Path) -> tuple[Path | None, str | None]:
    """Restore only the calibrated constructor-order/guard fragments, preserving unrelated module additions."""
    seeded = case.get("seeded_defect") or {}
    fixture = common.FIXTURES / str(seeded.get("tree") or "")
    fixed_path, naive_path = fixture / "fixed/src/basket.js", fixture / "naive/src/basket.js"
    source_path = snapshot / "src/basket.js"
    if seeded.get("id") != "validation-before-input" or not fixed_path.is_file() or not naive_path.is_file():
        return None, "no calibrated Basket counterfactual is available for this seeded case"
    if not source_path.is_file():
        return None, "the final Basket module is outside the supported counterfactual layout"
    try:
        fixed_text = fixed_path.read_text(encoding="utf-8")
        naive_text = naive_path.read_text(encoding="utf-8")
        final_text = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"cannot read the calibrated Basket fragments: {exc}"

    constructor_marker = "  constructor({ limit } = {}) {"
    check_marker = "  check() {"

    def constructor(text: str) -> str | None:
        start = text.find(constructor_marker)
        end = text.find(check_marker, start + len(constructor_marker)) if start >= 0 else -1
        return text[start:end] if start >= 0 and end >= 0 else None

    def guard(text: str) -> str | None:
        check_at = text.find(check_marker)
        start = text.find("    if (", check_at + len(check_marker)) if check_at >= 0 else -1
        end = text.find("\n", start) if start >= 0 else -1
        return text[start:end] if start >= 0 and end >= 0 else None

    fixed_constructor, naive_constructor = constructor(fixed_text), constructor(naive_text)
    fixed_guard, naive_guard = guard(fixed_text), guard(naive_text)
    if not all((fixed_constructor, naive_constructor, fixed_guard, naive_guard)):
        return None, "the seeded Basket fixture no longer has the calibrated fragments"
    if (final_text.count(fixed_constructor) != 1 or final_text.count(fixed_guard) != 1
            or final_text.count(naive_constructor) or final_text.count(naive_guard)):
        return None, "the final Basket source does not uniquely contain the calibrated fixed fragments"

    destination.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(snapshot, destination, dirs_exist_ok=True)
        before_path = destination / "src/basket.js"
        before_text = before_path.read_text(encoding="utf-8")
        before_text = before_text.replace(fixed_constructor, naive_constructor, 1)
        before_text = before_text.replace(fixed_guard, naive_guard, 1)
        before_path.write_text(before_text, encoding="utf-8")
    except OSError as exc:
        return None, f"cannot build the calibrated Basket counterfactual: {exc}"
    return destination, None


def evaluate(sample: Path, case: dict, worktree: Path, *, test_repairs: bool) -> dict:
    """Return review-repair status and (for E5) before/after regression behavior."""
    invocation = _json(Path(sample) / "invocation.json")
    if invocation is None or invocation.get("case") not in SUPPORTED_CASES:
        return {"status": "unknown", "value": None, "e5_value": None, "repair_count": None,
                "why": "Improve attribution is limited to the four seeded review cases",
                "fixes": [], "actions": [], "final_defect_present": None}
    rows, why, required = _review_inputs(Path(sample), case, Path(worktree))
    if why:
        return {"status": "unknown", "value": None, "repair_count": None, "why": why,
                "fixes": [], "actions": []}
    final = _probe_state(case, Path(worktree))
    if final is None:
        return {"status": "unknown", "value": None, "repair_count": None,
                "e5_value": None, "why": "final seeded-defect probe could not be read",
                "fixes": [], "actions": [], "final_defect_present": None}
    final_present = bool(final.get("present"))
    module_paths = set(_module_paths(required))
    repairs = []
    introductions = []
    valid_entry_fault = False
    entry_clean = False
    skipped = []
    actions_out = []
    with tempfile.TemporaryDirectory(prefix="shiploop-improve-attribution-") as temp:
        root = Path(temp)
        cache: dict[tuple[str, str], Path] = {}

        def materialize(repo: Path, prefix: str, tree: str, name: str) -> Path | None:
            key = (tree, prefix)
            if key in cache:
                return cache[key]
            destination = root / name
            destination.mkdir(parents=True, exist_ok=True)
            extracted = _extract_archive(repo, prefix, tree, destination)
            if extracted is not None:
                cache[key] = extracted
            return extracted

        for index, review in enumerate(rows):
            bind = materialize(review["repo"], review["prefix"], review["bind_tree"], f"{index}-bind")
            if bind is None:
                return {"status": "unknown", "value": None, "repair_count": None,
                        "why": f"bind tree {review['bind_tree']} for action {review['action']} is unresolvable",
                        "fixes": [], "actions": actions_out}
            passes = []
            for item in review["passes"]:
                snapshot = materialize(review["repo"], review["prefix"], item["tree"],
                                       f"{index}-pass-{item['pass']}")
                if snapshot is None:
                    return {"status": "unknown", "value": None, "repair_count": None,
                            "why": f"pass {item['pass']} tree {item['tree']} for action {review['action']} is unresolvable",
                            "fixes": [], "actions": actions_out}
                passes.append({**item, "snapshot": snapshot})

            present_at_bind = [path for path in module_paths if (bind / path).is_file()]
            bound_probe = _probe_state(case, bind)
            if (not present_at_bind and review["stage"] in PRE_IMPLEMENTATION_STAGES
                    and _module_missing(bound_probe)):
                # A skip needs both absent known module paths and a failed import in the public behavior check.
                skipped.append(review["action"])
                actions_out.append({"action": review["action"], "stage": review["stage"],
                                    "status": "not_applicable", "why": "seeded module paths are absent at bind",
                                    "passes": [{k: item[k] for k in ("pass", "tree", "changed", "commit")}
                                               for item in passes]})
                continue
            if not present_at_bind:
                why = (f"seeded module is absent at later review stage {review['stage']!r}; absence cannot establish "
                       "a pre-implementation not-applicable result"
                       if _module_missing(bound_probe) else
                       f"action {review['action']} bind has no supported seeded module path or valid missing-module evidence")
                return {"status": "unknown", "value": None, "repair_count": None,
                        "why": why,
                        "fixes": [], "actions": actions_out}
            if bound_probe is None or not bound_probe.get("behavior_checks_pass"):
                return {"status": "unknown", "value": None, "repair_count": None,
                        "why": f"public behavior checks do not validate action {review['action']} bind snapshot",
                        "fixes": [], "actions": actions_out}
            bound_fault = bool(bound_probe.get("present"))
            entry_clean = entry_clean or not bound_fault
            valid_entry_fault = valid_entry_fault or bound_fault
            prior_tree = review["bind_tree"]
            prior_fault = bound_fault
            transitions = []
            action_introduced = False
            pass_states = []
            for item, current in zip(review["passes"], passes):
                current_paths = [path for path in module_paths if (current["snapshot"] / path).is_file()]
                delta = _diff_paths(review["repo"], prior_tree, item["tree"])
                if delta is None:
                    return {"status": "unknown", "value": None, "repair_count": None,
                            "why": f"cannot diff action {review['action']} pass {item['pass']} against its prior snapshot",
                            "fixes": [], "actions": actions_out}
                if not current_paths:
                    return {"status": "unknown", "value": None, "repair_count": None,
                            "why": f"action {review['action']} pass {item['pass']} has no supported seeded module path",
                            "fixes": [], "actions": actions_out}
                current_probe = _probe_state(case, current["snapshot"])
                if current_probe is None or not current_probe.get("behavior_checks_pass"):
                    return {"status": "unknown", "value": None, "repair_count": None,
                            "why": f"public behavior checks do not validate action {review['action']} pass {item['pass']}",
                            "fixes": [], "actions": actions_out}
                current_fault = bool(current_probe.get("present"))
                pass_states.append({"pass": item["pass"], "probe_present": current_fault,
                                    "checks_pass": current_probe["checks_pass"],
                                    "behavior_checks_pass": current_probe["behavior_checks_pass"]})
                touched = sorted(set(delta) & module_paths)
                if prior_fault and not current_fault:
                    if not touched:
                        return {"status": "unknown", "value": None, "repair_count": None,
                                "why": f"action {review['action']} pass {item['pass']} clears the probe without changing a seeded path",
                                "fixes": [], "actions": actions_out}
                    transitions.append({"pass": item["pass"], "tree": item["tree"], "commit": item["commit"],
                                        "paths": touched, "snapshot": current["snapshot"]})
                elif not prior_fault and current_fault and touched:
                    introductions.append({"action": review["action"], "pass": item["pass"], "paths": touched})
                    action_introduced = True
                prior_tree, prior_fault = item["tree"], current_fault
            if transitions:
                repair = transitions[-1]
                record = {"action": review["action"], "stage": review["stage"], "pass": repair["pass"],
                          "commit": repair["commit"], "paths": repair["paths"], "test": None,
                          "passes_after": None, "fails_before_fix": None,
                          "counterfactual_supported": None, "counterfactual_why": None}
                if test_repairs:
                    last_snapshot = passes[-1]["snapshot"]
                    changed = _diff_paths(review["repo"], review["bind_tree"], review["passes"][-1]["tree"])
                    if changed is None:
                        return {"status": "unknown", "value": None, "repair_count": None,
                                "why": f"cannot diff action {review['action']} final pass against its bind snapshot",
                                "fixes": [], "actions": actions_out}
                    test_paths = [path for path in changed if _TEST.search(path) and (last_snapshot / path).is_file()]
                    after_command = _run_test(last_snapshot, test_paths)
                    before = root / f"{index}-before-fix"
                    record.update(test=after_command["test"], passes_after=after_command["passes_after"])
                    if not test_paths:
                        record.update(fails_before_fix=False, counterfactual_supported=True,
                                      counterfactual_why="the linked review changed no test files")
                    else:
                        before, counterfactual_why = _basket_counterfactual(case, last_snapshot, before)
                        if before is None:
                            record.update(fails_before_fix=None, counterfactual_supported=False,
                                          counterfactual_why=counterfactual_why)
                        else:
                            before_probe = _probe_state(case, before)
                            if (before_probe is None or not before_probe.get("present")
                                    or not before_probe.get("behavior_checks_pass")):
                                record.update(fails_before_fix=None, counterfactual_supported=False,
                                              counterfactual_why="counterfactual did not preserve public behavior and reproduce the seeded defect")
                            else:
                                before_command = _run_test(before, test_paths)
                                record.update(fails_before_fix=before_command["test"] is not None
                                              and before_command["passes_after"] is False,
                                              counterfactual_supported=True,
                                              counterfactual_seeded_defect_present=True,
                                              counterfactual_behavior_checks_pass=True)
                repairs.append(record)
            actions_out.append({"action": review["action"], "stage": review["stage"],
                                "status": "repaired" if transitions else
                                "introduced" if action_introduced
                                else "unrepaired" if bound_fault and prior_fault else
                                "no_repair" if bound_fault else "not_applicable",
                                "bound_defect_present": bound_fault,
                                "final_pass_defect_present": prior_fault,
                                "passes": [{k: item[k] for k in ("pass", "tree", "changed", "commit")}
                                           for item in passes], "pass_probe_states": pass_states})

    if not final.get("checks_pass") or not final.get("behavior_checks_pass"):
        status, value, why = "unknown", None, "final public checks are invalid, so final repair status cannot be claimed"
    elif introductions:
        status = "introduced"
        value = 0
        why = "an action-linked Improve pass introduced the seeded defect"
    elif repairs:
        status = "repaired" if not final_present else "unrepaired"
        value = 1 if status == "repaired" else 0
        why = ("a linked Improve pass removed the seeded defect and the final tree remains clear"
               if status == "repaired" else "the seeded defect returned in the final tree after an Improve repair")
    elif valid_entry_fault and final_present:
        status, value, why = "unrepaired", 0, "the seeded defect was present at a linked review and remains in the final tree"
    elif valid_entry_fault and not final_present:
        status, value, why = "no_repair", 0, "the final tree is clear, but no linked Improve pass removed the seeded defect"
    elif entry_clean or skipped:
        status, value, why = "not_applicable", None, "the seeded defect was absent at every applicable review bind"
    else:
        status, value, why = "unknown", None, "no linked review snapshot could establish the seeded defect state"
    e5_value = (None if any(item.get("counterfactual_supported") is False
                            or item.get("counterfactual_supported") is None for item in repairs) else
                int(all(item.get("passes_after") and item.get("fails_before_fix") for item in repairs))
                if status == "repaired" and test_repairs else
                0 if status in ("unrepaired", "introduced", "no_repair") else None)
    return {"status": status, "value": value, "e5_value": e5_value,
            "repair_count": len(repairs), "why": why, "fixes": repairs,
            "actions": actions_out, "final_defect_present": final_present}
