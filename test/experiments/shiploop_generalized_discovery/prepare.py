#!/usr/bin/env python3
"""Materialize matched discovery cases using a coordinator-owned frozen study."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

from study_inputs import validate_study_inputs


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_fixtures(path: Path):
    spec = importlib.util.spec_from_file_location("generic_fixtures", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare_pair(study: Path, family: str, repetition: int) -> list[str]:
    study = Path(study)
    validate_study_inputs(study)
    study = study.resolve()
    state = json.loads((study / "study.json").read_text())
    arms = state.setdefault("arms", {})
    if any(a["family"] == family and a["repetition"] == repetition for a in arms.values()):
        raise ValueError("pair already prepared; preserve previous inputs")
    if len(arms) + 2 > state["max_arm_launches"]:
        raise ValueError("maximum prepared contexts reached")
    fixtures = load_fixtures(study / "frozen" / "fixtures.py")
    names = []
    # Alternate which arm starts first. Names do not expose the variant.
    order = ("baseline", "candidate") if (int(family[-1]) + repetition) % 2 else ("candidate", "baseline")
    for variant in order:
        name = f"trial-{len(arms) + 1:02d}"
        arm = study / "arms" / name
        workspace = arm / "workspace"
        workspace.mkdir(parents=True, exist_ok=False)
        fixtures.materialize(family, workspace)
        shutil.copytree(study / "guides" / "references", workspace / "guidance")
        shutil.copyfile(study / "guides" / f"{variant}.md", workspace / "guidance" / "research-loop.md")
        prompt = f"""Perform a bounded discovery investigation for this task:

{fixtures.TASKS[family]}

Read guidance/research-loop.md, beginning at Recursive discovery and experiments.
Use its general discovery method, supported by relevant linked guidance when
necessary. This is discovery, not a request to implement the application or run
an entire delivery workflow. Record findings in REPORT.md in this workspace.
Cover the eight areas with evidence, justified non-applicability or unresolved
questions. Describe the next implementation and validation decisions warranted
by the evidence. Distinguish inspected sources and actually observed behavior.

The sole provided workspace tool is your inspection/execution route. The target
system is the fixture described by its README; the tool itself does not establish
that the application uses MCP. Use workspace paths relative to the supplied root.
Use documented safe local probes where useful. You may write REPORT.md and
scratch output; do not alter provided source/configuration or install anything.
All supplied fixture data is synthetic. No real account or external service is
authorized or needed. Do not inspect neighboring workspaces or coordinator files.

Allowance: 8 minutes and 32 workspace tool calls total. At 6 minutes or 24 calls,
stop exploration and use the remaining allowance to finish REPORT.md. The same
allowance covers linked guidance and experiments; no reset. Keep individual
commands within remaining exploration time. If insufficient, report the specific
remaining gap. Finish with a short summary and the REPORT.md locator.
"""
        (arm / "prompt.md").write_text(prompt)
        inputs = {str(p.relative_to(workspace)): sha(p) for p in sorted(workspace.rglob("*")) if p.is_file()}
        (arm / "input-hashes.json").write_text(json.dumps(inputs, indent=2) + "\n")
        arms[name] = {"family": family, "variant": variant, "repetition": repetition,
                      "prompt_sha256": sha(arm / "prompt.md"), "input_hashes_sha256": sha(arm / "input-hashes.json")}
        names.append(name)
    state["arms"] = arms
    (study / "study.json").write_text(json.dumps(state, indent=2) + "\n")
    return names


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", required=True, type=Path)
    parser.add_argument("--families", default="f1,f2,f3,f4")
    parser.add_argument("--repetition", type=int, default=0)
    args = parser.parse_args()
    names = []
    for family in args.families.split(","):
        names += prepare_pair(args.study, family, args.repetition)
    print(json.dumps({"prepared": names}))


if __name__ == "__main__":
    main()
