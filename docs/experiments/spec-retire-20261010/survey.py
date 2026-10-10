#!/usr/bin/env python3
"""The retire step and the feature list, run on the saved ShipLoop E2E runs (batch 1012 task R).

    python3 survey.py <scratch-dir> [<saved-runs-root>]

For every saved work repository that holds `docs/shiploop/features/<folder>/spec.md` (the root defaults to
/Users/dadleet/e2e-runs; it is only read), this script asks the engine's own functions, never a copy of their rules:

  unmerged     `knowledge_home._unmerged`: the requirement IDs the feature spec names that the living spec lacks, or None when it
               cannot be judged (a living spec that names no ID).
  planned      `knowledge_home._planned_record`: the run's prepare close, found by its exact subject over the whole log, and whether
               the feature spec at that commit equals the final one. A path-limited log of the folder is counted beside it.
  retire       `knowledge_home.retire(state, True)` on a clone of the repository (made in <scratch-dir>, removed afterwards): the
               commit it makes, the paths that commit changes, and that retired_by / is_retire_subject recognise it.
  list         `knowledge_home.feature_list` on the repository's tree: every line through the credential screen.

A folder the model named itself (no `-<6 characters>` run suffix) has no run id to rebuild its state from, so it is counted apart
and not retired. Nothing in the saved runs is written: the clones are the only repositories this script changes.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
os.environ.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_OPTIONAL_LOCKS": "0"})

import shiploop_knowledge_home as knowledge  # noqa: E402
import shiploop_privacy as privacy  # noqa: E402

SUFFIXED = re.compile(r"^(?P<slug>[a-z0-9-]+)-(?P<suffix>[a-z0-9]{6})$")


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def state_for(repo: Path, folder: str) -> dict | None:
    """A state whose feature_dir is this folder (the slug is six words at most, so it rebuilds from its own words)."""
    found = SUFFIXED.match(folder)
    if not found:
        return None
    state = {"repo": str(repo), "prompt": found.group("slug").replace("-", " "), "run_id": "nav-" + "0" * 26 + found.group("suffix")}
    return state if knowledge.feature_dir(state).rsplit("/", 1)[-1] == folder else None


def main() -> int:
    scratch = Path(sys.argv[1]).resolve()
    saved = Path(sys.argv[2] if len(sys.argv) > 2 else "/Users/dadleet/e2e-runs")
    scratch.mkdir(parents=True, exist_ok=True)
    rows, homes, flagged = [], 0, 0
    for work in sorted(saved.glob("*/**/work")):
        features = work / "docs" / "shiploop" / "features"
        if ".shiploop-runs" in str(work) or not features.is_dir() or not (work / ".git").exists():
            continue
        homes += 1
        text = knowledge.feature_list(work)
        flagged += sum(bool(privacy.sensitive_text(line)) for line in text.splitlines())
        for folder in sorted(path.name for path in features.iterdir() if (path / "spec.md").is_file()):
            relative = "docs/shiploop/features/" + folder
            row = {"repo": str(work.relative_to(saved)), "folder": folder, "unmerged": knowledge._unmerged(work, relative)}
            state = state_for(work, folder)
            if state is None:
                row["model_named"] = True
                rows.append(row)
                continue
            planned = knowledge._planned_record(work, state)
            row["planned_found"] = bool(planned)
            if planned:
                then = git(work, "show", planned + ":" + relative + "/spec.md")
                row["planned_equals_final"] = then.returncode == 0 and then.stdout == (work / relative / "spec.md").read_text(errors="replace")
            by_path = git(work, "log", "--format=%H", "--", relative).stdout.split()
            row["planned_in_path_log"] = bool(planned) and planned in by_path
            clone = scratch / (str(work.relative_to(saved)).replace("/", "__") + "__" + folder)
            shutil.rmtree(clone, ignore_errors=True)
            made = subprocess.run(["git", "clone", "-q", "--no-hardlinks", str(work), str(clone)], capture_output=True, text=True)
            if made.returncode:
                row["clone_error"] = made.stderr.strip()[:200]
                rows.append(row)
                continue
            try:
                state["repo"] = str(clone)
                done = knowledge.retire(state, True)
                row["retire"] = {"commit": bool(done.commit), "kept": done.kept}
                if done.commit:
                    changed = sorted(line for line in git(clone, "show", "--name-status", "--format=", "HEAD").stdout.splitlines() if line)
                    subject = git(clone, "log", "-1", "--format=%s").stdout.strip()
                    row["retire"].update({
                        "changed": [line.split("\t")[0] + " " + Path(line.split("\t")[1]).name for line in changed],
                        "subject_ok": subject == knowledge.retire_subject(state) and knowledge.is_retire_subject(subject),
                        "retired_by": bool(knowledge.retired_by(clone, relative)),
                        "planned_line": ("Planned at " + planned + " (the prepare close).") in git(clone, "log", "-1", "--format=%B").stdout,
                        "gone": not (clone / relative / "spec.md").exists()})
                    row["retry"] = {"commit": bool(knowledge.retire(state, True).commit)}
            finally:
                shutil.rmtree(clone, ignore_errors=True)
            rows.append(row)
    suffixed = [row for row in rows if not row.get("model_named")]
    summary = {
        "work_repositories_with_a_features_folder": homes,
        "feature_specs": len(rows),
        "model_named_folders_not_retired": sum(bool(row.get("model_named")) for row in rows),
        "judged_by_the_id_check": sum(row["unmerged"] is not None for row in rows),
        "not_judged_living_spec_names_no_id": sum(row["unmerged"] is None for row in rows),
        "names_an_id_the_living_spec_lacks": sum(bool(row["unmerged"]) for row in rows),
        "planned_record_found_by_subject": sum(bool(row.get("planned_found")) for row in suffixed),
        "planned_record_equals_the_final_feature_spec": sum(bool(row.get("planned_equals_final")) for row in suffixed),
        "planned_record_also_in_the_path_limited_log": sum(bool(row.get("planned_in_path_log")) for row in suffixed),
        "retired": sum(bool(row.get("retire", {}).get("commit")) for row in suffixed),
        "kept": sorted({row["retire"]["kept"] for row in suffixed if row.get("retire", {}).get("kept")}),
        # A saved run predates the list, so its retire commit adds the list (A); a run on this engine already has it (M).
        "retired_commits_that_delete_the_spec_and_add_the_list": sum(
            sorted(row["retire"].get("changed", [])) == ["A README.md", "D spec.md"] for row in suffixed if row.get("retire", {}).get("commit")),
        "retired_commits_that_delete_the_spec_and_modify_the_list": sum(
            sorted(row["retire"].get("changed", [])) == ["D spec.md", "M README.md"] for row in suffixed if row.get("retire", {}).get("commit")),
        "retired_with_subject_matcher_and_retired_by_and_planned_line": sum(
            all(row["retire"].get(key) for key in ("subject_ok", "retired_by", "planned_line", "gone")) for row in suffixed
            if row.get("retire", {}).get("commit")),
        "a_retry_made_a_second_commit": sum(bool(row.get("retry", {}).get("commit")) for row in suffixed),
        "list_lines_flagged_by_the_credential_screen": flagged,
    }
    print(json.dumps(summary, indent=2))
    (scratch / "survey-rows.json").write_text(json.dumps(rows, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
