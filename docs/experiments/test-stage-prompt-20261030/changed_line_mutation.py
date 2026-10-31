"""Changed-line mutation score of a delivered brownfield worktree (read-only on the worktree).

For each case: list the product lines the run added since its baseline commit (src/ only), apply each js-1 operator site
on those lines alone in an archive copy, run the product's own `npm test`, and record killed / survived.
Usage: python3 -I changed_line_mutation.py <out.json> <case-name>=<worktree>:<base-commit> ...
"""
import json, os, re, shutil, signal, subprocess, sys, tarfile, tempfile, io, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "skills/shiploop/scripts"))
sys.path.insert(0, str(REPO / "test/shiploop_e2e"))
import quality  # noqa: E402  (js-1 catalog: quality.sites, quality.OPERATOR_ID)

SCRATCH = Path(os.environ.get("MUTATION_SCRATCH") or tempfile.mkdtemp(prefix="changed-line-mutation-"))
TIMEOUT = 60


def changed_lines(worktree: str, base: str) -> dict[str, set[int]]:
    diff = subprocess.run(["git", "-C", worktree, "diff", "-U0", base, "HEAD", "--", "src"],
                          capture_output=True, text=True, check=True).stdout
    out, current = {}, None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            out.setdefault(current, set())
        m = re.match(r"@@ -\S+ \+(\d+)(?:,(\d+))? @@", line)
        if m and current:
            start, count = int(m.group(1)), int(m.group(2) or 1)
            out[current].update(range(start, start + count))
    return {k: v for k, v in out.items() if v and k.endswith((".js", ".cjs", ".mjs"))}


def export(worktree: str, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    data = subprocess.run(["git", "-C", worktree, "archive", "HEAD"], capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(dest, filter="data")


def run_tests(cwd: Path) -> tuple[int | None, str]:
    proc = subprocess.Popen(["npm", "test", "--silent"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, start_new_session=True, env={**os.environ, "CI": "1"})
    try:
        out, _ = proc.communicate(timeout=TIMEOUT)
        return proc.returncode, out[-4000:]
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return None, "timeout"


def first_failure(output: str) -> str:
    for line in output.splitlines():
        if line.lstrip().startswith(("not ok", "✖")):
            return line.strip()[:160]
    return ""


def measure(name: str, worktree: str, base: str) -> dict:
    copy = SCRATCH / name
    export(worktree, copy)
    rc, out = run_tests(copy)
    record = {"case": name, "worktree": worktree, "base": base, "operator_id": quality.OPERATOR_ID,
              "baseline_rc": rc, "mutants": []}
    if rc != 0:
        record["error"] = "unmutated suite not green: " + out[-500:]
        return record
    for rel, lines in sorted(changed_lines(worktree, base).items()):
        path = copy / rel
        source = path.read_text()
        for site in quality.sites(source):
            if site["line"] not in lines:
                continue
            mutated = source[:site["start"]] + site["new"] + source[site["end"]:]
            path.write_text(mutated)
            started = time.monotonic()
            mrc, mout = run_tests(copy)
            path.write_text(source)
            status = "survived" if mrc == 0 else "killed"
            record["mutants"].append({"file": rel, "line": site["line"], "op": site["op"], "from": site["old"],
                                      "to": site["new"], "status": status, "rc": mrc,
                                      "by": first_failure(mout) if status == "killed" else "",
                                      "text": source.splitlines()[site["line"] - 1].strip()[:140],
                                      "seconds": round(time.monotonic() - started, 2)})
    killed = sum(m["status"] == "killed" for m in record["mutants"])
    record.update(killed=killed, total=len(record["mutants"]),
                  ratio=round(killed / len(record["mutants"]), 4) if record["mutants"] else None)
    return record


def main() -> None:
    out = Path(sys.argv[1])
    results = []
    for arg in sys.argv[2:]:
        name, rest = arg.split("=", 1)
        worktree, base = rest.rsplit(":", 1)
        results.append(measure(name, worktree, base))
        out.write_text(json.dumps(results, indent=1))
        r = results[-1]
        print(name, r.get("killed"), "/", r.get("total"), r.get("ratio"), r.get("error", ""), flush=True)


if __name__ == "__main__":
    main()
