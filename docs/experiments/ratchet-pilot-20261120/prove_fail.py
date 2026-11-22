#!/usr/bin/env python3
"""Can each acceptance check of a run be made to fail? No model is called.

    python3 prove_fail.py WORK FIXTURE OUT.json [--changed N] [--unchanged N] [--workers N]
                                                [--lines all|even|odd] [--only base,sabotage,faults]

WORK is a run's work folder: the build with the acceptance tests and `ratchet/acceptance.json` laid over it, a Git work
tree whose first commit is the starting product. FIXTURE is the folder that starting product came from, or `-` to
take it from that first commit. Every command
of the manifest is run on the build as it is, and then on copies that ought to make some check fail:

  base        the starting product, with the acceptance tests laid over it: a check of new behaviour fails here
  sabotage    the build with one failing test appended to one of the product's own existing test files: a check
              that the existing tests still pass fails here
  fault-<n>   the build with one small fault from the E2E harness's catalog (test/shiploop_e2e/quality.py): first on
              the lines the build changed against FIXTURE, then on the lines it left as they were in the files it
              changed (mutate.py's two selections), N of each at most (defaults 12 and 24)

A check that passes on the build and on every copy has not been seen to fail. A copy on which no check fails has not
been noticed: a fault, the sabotaged copy, or the starting product. OUT.json holds these lists, each check's failures
by copy, and `refusal`: the text a test session is given. A check that fails on the build itself decides nothing and
is listed apart. Copies are made under TMPDIR, which should be a plain folder (a symbolic link breaks tests that
compare paths).

The trial on two suites whose truth was known (journal section 26, part C) set the unit: a check is one manifest
entry and may run several tests, so a test that can never fail hides behind a real one of the same entry, and "never
seen failing" stayed empty on a suite with a known do-nothing check. The sabotaged copy does see it: no check failed
there. So the copy that goes unnoticed is reported, not only the check.

--lines even (or odd) keeps only the faults on even (odd) numbered lines: a session shown the even ones leaves the
odd ones as a yardstick it was never shown. --only limits the copies made (for a census of the sabotaged copy alone).
"""
import concurrent.futures
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "test" / "shiploop_e2e"))
import quality

import gate as gate_module
import mutate

NAMED = [True]  # must a check's output name its item; a run's own record says (run.json beside WORK, `named_checks`)
SABOTAGE = ("\nrequire('node:test')('added by the checking script: this test fails on purpose', () => {\n"
            "  throw new Error('an existing test was made to fail on purpose');\n});\n")


def copy_work(work, scratch, label):
    folder = Path(tempfile.mkdtemp(prefix=f"prove-{label}-", dir=scratch))
    shutil.rmtree(folder)
    shutil.copytree(work, folder, symlinks=True, ignore=shutil.ignore_patterns("node_modules"))
    return folder


def base_tree(work, scratch):
    """The starting product with the run's acceptance tests, manifest and specification laid over it, and the run's
    history beside it (a test may compare with the base commit)."""
    folder = Path(tempfile.mkdtemp(prefix="prove-base-", dir=scratch))
    first = subprocess.run(["git", "-C", str(work), "rev-list", "--max-parents=0", "HEAD"], capture_output=True, text=True,
                           check=True).stdout.split()[0]
    archive = subprocess.run(["git", "-C", str(work), "archive", first], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(folder)], input=archive, check=True)
    for name in gate_module.FROZEN_PATHS:
        source = Path(work) / name
        if source.is_dir():
            shutil.copytree(source, folder / name, dirs_exist_ok=True)
        elif source.is_file():
            (folder / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, folder / name)
    shutil.copytree(Path(work) / ".git", folder / ".git", symlinks=True)
    return folder


def sabotage_target(work):
    """One of the product's own test files that the starting product already had, or None."""
    first = subprocess.run(["git", "-C", str(work), "rev-list", "--max-parents=0", "HEAD"], capture_output=True, text=True,
                           check=True).stdout.split()[0]
    listed = subprocess.run(["git", "-C", str(work), "ls-tree", "-r", "--name-only", first, "test/"], capture_output=True,
                            text=True, check=False).stdout.split("\n")
    names = sorted(name for name in listed if name.endswith(".test.js") and (Path(work) / name).is_file())
    return names[0] if names else None


def fault_sites(work, fixture, changed, unchanged, parity="all"):
    """(file, site, where) for the faults to try: the build's changed lines first, then existing lines of touched files.
    `parity` even or odd keeps only the sites on such line numbers."""
    wanted = {"all": (0, 1), "even": (0,), "odd": (1,)}[parity]
    targets = quality.targets(Path(work), mutate.NOT_PRODUCT)
    new, old = {}, {}
    for name in sorted(targets):
        lines = mutate.changed_lines(work, fixture, name)
        if not lines:
            continue
        text = (Path(work) / name).read_bytes().decode("utf-8", "surrogateescape")
        sites = [site for site in quality.sites(text) if site["line"] % 2 in wanted]
        on_new = [site for site in sites if site["line"] in lines]
        if on_new:
            new[name] = on_new
        if (Path(fixture) / name).is_file():
            on_old = [site for site in sites if site["line"] not in lines]
            if on_old:
                old[name] = on_old
    chosen = [(name, site, "changed") for name, site in quality.round_robin(new)[:changed]]
    chosen += [(name, site, "existing") for name, site in quality.round_robin(old)[:unchanged]]
    return chosen


def measure(folder, scratch, label):
    temp = Path(tempfile.mkdtemp(prefix=f"tmp-{label}-", dir=scratch))
    try:
        record = gate_module.gate(folder, clauses_only=True, no_restore=True, config={}, extra_env={"TMPDIR": str(temp)}, named=NAMED[0])
        rows = record["clauses"]
        return {"failing": sorted(record["failing"]), "ids": sorted(rows),
                "did_not_end": sorted(ident for ident, row in rows.items() if not row["pass"] and row["rc"] is None)}
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        return {"error": f"{type(error).__name__}: {error}"[:300]}
    finally:
        shutil.rmtree(temp, ignore_errors=True)
        shutil.rmtree(folder, ignore_errors=True)


def one_fault(work, scratch, number, name, site):
    folder = copy_work(work, scratch, f"fault-{number}")
    path = folder / name
    text = path.read_bytes().decode("utf-8", "surrogateescape")
    path.write_bytes((text[:site["start"]] + site["new"] + text[site["end"]:]).encode("utf-8", "surrogateescape"))
    parses = subprocess.run(["node", "--check", name], cwd=str(folder), capture_output=True, check=False).returncode == 0
    if not parses:
        shutil.rmtree(folder, ignore_errors=True)
        return {"invalid": True}
    return measure(folder, scratch, f"fault-{number}")


def prove(work, fixture=None, changed=12, unchanged=24, workers=4, root=None, parity="all", only=("base", "sabotage", "faults")):
    """`fixture` None: the starting product is taken from the work repository's first commit. `root`: where the
    copies are made (a plain folder), the system's temporary folder when None."""
    work = Path(work).resolve()
    record = work.parent / "run.json"
    if record.is_file():
        NAMED[0] = bool(json.loads(record.read_text()).get("named_checks", True))
    scratch = Path(tempfile.mkdtemp(prefix="ratchet-prove-", dir=root))
    try:
        if fixture is None:
            fixture = scratch / "starting-product"
            fixture.mkdir()
            first = subprocess.run(["git", "-C", str(work), "rev-list", "--max-parents=0", "HEAD"], capture_output=True, text=True,
                                   check=True).stdout.split()[0]
            archive = subprocess.run(["git", "-C", str(work), "archive", first], capture_output=True, check=True).stdout
            subprocess.run(["tar", "-x", "-C", str(fixture)], input=archive, check=True)
        fixture = Path(fixture).resolve()
        build = measure(copy_work(work, scratch, "build"), scratch, "build")
        if "error" in build:
            return {"error": build["error"]}
        jobs = {}
        if "base" in only:
            jobs["base"] = lambda: measure(base_tree(work, scratch), scratch, "base")
        target = sabotage_target(work) if "sabotage" in only else None
        if target:
            def sabotaged():
                folder = copy_work(work, scratch, "sabotage")
                with (folder / target).open("a") as handle:
                    handle.write(SABOTAGE)
                return measure(folder, scratch, "sabotage")
            jobs["sabotage"] = sabotaged
        faults = fault_sites(work, fixture, changed, unchanged, parity) if "faults" in only else []
        described = {}
        for number, (name, site, where) in enumerate(faults, 1):
            label = f"fault-{number}"
            described[label] = {"file": name, "line": site["line"], "op": site["op"], "old": site["old"], "new": site["new"], "where": where}
            jobs[label] = (lambda number=number, name=name, site=site: one_fault(work, scratch, number, name, site))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {label: pool.submit(job) for label, job in jobs.items()}
            copies = {label: future.result() for label, future in futures.items()}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    wrong_on_build = set(build["failing"])
    usable = {label: row for label, row in copies.items() if "error" not in row and not row.get("invalid")}
    seen = {ident: sorted(label for label, row in usable.items() if ident in row["failing"] and ident not in row["did_not_end"])
            for ident in build["ids"] if ident not in wrong_on_build}
    never = sorted(ident for ident, labels in seen.items() if not labels)
    unnoticed = sorted((label for label, row in usable.items()
                        if label.startswith("fault-") and not (set(row["failing"]) - wrong_on_build)), key=lambda label: int(label[6:]))
    whole = sorted(label for label in ("base", "sabotage")
                   if label in usable and not (set(usable[label]["failing"]) - wrong_on_build))
    report = {"items": len(build["ids"]), "failing_on_the_build": sorted(wrong_on_build), "copies": sorted(usable),
              "not_usable": {label: row for label, row in copies.items() if label not in usable}, "sabotaged_file": target,
              "lines": parity, "faults": described, "seen_failing_on": seen, "never_seen_failing": never,
              "copies_unnoticed": whole, "faults_unnoticed": unnoticed}
    report["refusal"] = refusal(report)
    return report


def refusal(report):
    """What a test session is told, or "" when every check was seen to fail and every copy was noticed."""
    lines = []
    tried = len([label for label in report["copies"] if label.startswith("fault-")])
    if "sabotage" in report["copies_unnoticed"]:
        lines += ["## A broken existing test went unnoticed",
                  (f"The script added one failing test to `{report['sabotaged_file']}`, one of the product's own test files, and "
                   "every check still passed. So no check here shows that the product's existing tests pass."),
                  ("If a clause requires the existing tests to pass, make its check fail when one of them fails (a check that "
                   "runs other tests must show that they ran, and how many passed and failed), or say under a heading `## Checks "
                   "nothing here can break` in your tests report why no clause requires it."), ""]
    if "base" in report["copies_unnoticed"]:
        lines += ["## Every check passes on the starting product",
                  ("The script ran the checks on the product as it was before the change, and none failed. So no check here "
                   "shows that the change was made."),
                  ("Make the check of each clause that states new behaviour fail where that behaviour is absent, or say under "
                   "a heading `## Checks nothing here can break` in your tests report why the request changes nothing a check "
                   "can see."), ""]
    if report["never_seen_failing"]:
        lines += ["## The script could not make these checks fail",
                  ("Each of these checks passes on the build, and still passes on the starting product, on a copy of the build in "
                   "which one of the product's own existing tests was made to fail"
                   + (f" (`{report['sabotaged_file']}`)" if report["sabotaged_file"] else "")
                   + f", and on {tried} copies of the build that each carry one small fault. A check that nothing makes fail proves "
                   "nothing."),
                  *[f"- {ident}" for ident in report["never_seen_failing"]],
                  ("For each one: change the check so that it fails when the behaviour it names is broken (a check that runs other "
                   "tests must show that they ran), or say under a heading `## Checks nothing here can break` in your tests report "
                   "which fault would break it and why none of these did."), ""]
    if report["faults_unnoticed"]:
        lines += ["## Faults no check noticed",
                  "Every check still passes when the build carries any one of these single faults:"]
        for label in report["faults_unnoticed"]:
            fault = report["faults"][label]
            lines.append(f"- `{fault['file']}` line {fault['line']} ({'a line the change added' if fault['where'] == 'changed' else 'existing code'}): "
                         f"`{fault['old']}` became `{fault['new']}`")
        lines += [("For each one: add or strengthen a check so that it fails on that fault, or say under a heading `## Faults that "
                   "change nothing` in your tests report why the edit does not alter behaviour."), ""]
    if lines:
        lines.append("Keep the rest of your work. Never weaken a check to make this list shorter.")
    return "\n".join(lines)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    options = {"--changed": 12, "--unchanged": 24, "--workers": 4}
    words = {"--lines": "all", "--only": "base,sabotage,faults"}
    for flag in list(options) + list(words):
        if flag in argv:
            value = argv[argv.index(flag) + 1]
            del argv[argv.index(flag):argv.index(flag) + 2]
            if flag in options:
                options[flag] = int(value)
            else:
                words[flag] = value
    if len(argv) != 3 or words["--lines"] not in ("all", "even", "odd"):
        raise SystemExit(__doc__)
    report = prove(argv[0], None if argv[1] == "-" else argv[1], options["--changed"], options["--unchanged"], options["--workers"], parity=words["--lines"],
                   only=tuple(words["--only"].split(",")))
    Path(argv[2]).write_text(json.dumps(report, indent=1) + "\n")
    if "error" in report:
        print(f"the build could not be measured: {report['error']}")
        return 1
    print(f"{report['items']} checks; {len(report['failing_on_the_build'])} fail on the build itself; copies tried: {len(report['copies'])}; "
          f"never seen failing: {report['never_seen_failing'] or 'none'}; copies unnoticed: {report['copies_unnoticed'] or 'none'}; "
          f"faults unnoticed: {len(report['faults_unnoticed'])} of "
          f"{len([label for label in report['copies'] if label.startswith('fault-')])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
