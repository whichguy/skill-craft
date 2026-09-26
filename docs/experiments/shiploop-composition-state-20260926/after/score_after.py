"""Judge and tabulate the rerun with the same judges as the original experiments."""
import json, re, pathlib, subprocess, sys, ast, collections
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, ".")
from score import text_of
OUT = pathlib.Path("after/out"); J = pathlib.Path("after/judge")
def claude(prompt):
    return subprocess.run(["claude", "-p", "--model", "sonnet", "--tools", ""], input=prompt, capture_output=True, text=True).stdout
def jload(t):
    m = re.search(r"\{.*\}", t, re.S); return json.loads(m.group(0))
def text(f):
    return text_of(f)[0] if f.suffix == ".jsonl" else f.read_text()
TRUST = ('In this Apps Script project the client RPC proxy (srv, via gas_client) sends code to apiExec, which runs it with new Function, '
         'so any user who can open the page can run arbitrary server code as themselves, including reading the stored state of a game. '
         'Does the plan below identify this trust risk for a multiplayer game with hidden fleets and plan a mitigation? '
         'Return only JSON {"identified": true|false, "mitigated": true|false, "how": "<short>"}.\n<<<\n{plan}\n>>>\n')
RT = {"GAS": "Google Apps Script web app", "SF": "Salesforce DX / Lightning Web Components", "CF": "Cloudflare Workers"}
RQ = {"solo": "Battleship in the browser against the computer", "invite": "multiplayer Battleship with email invites, sign-in, and a per-player game history"}
errs = json.load(open("errors6b.json"))
def job(f):
    stem = f.stem; t = text(f); dest = J / (stem + ".json")
    if dest.exists(): return
    if stem.startswith("R3_"):
        prompt = pathlib.Path("judge3.txt").read_text().replace("{plan}", t)
    elif stem.startswith("R45_"):
        _, rt, q, _k = stem.split("_")
        prompt = pathlib.Path("judge4.txt").read_text().replace("{rt}", RT[rt]).replace("{req}", RQ[q]).replace("{plan}", t)
    elif stem.startswith("R6b_"):
        key = stem[4:].rsplit("_", 1)[0]
        prompt = pathlib.Path("judge6b.txt").read_text().replace("{errors}", "\n".join("- " + x for x in errs[key])).replace("{plan}", t)
    elif stem.startswith("R7_"):
        dest.write_text(claude(TRUST.replace("{plan}", t)))
        (J / (stem + ".layer.json")).write_text(claude(pathlib.Path("judge7_gas.txt").read_text().replace("{plan}", t))); return
    else: return
    dest.write_text(claude(prompt))
files = [f for f in sorted(OUT.iterdir()) if f.suffix in (".md", ".jsonl")]
with ThreadPoolExecutor(10) as ex: list(ex.map(job, files))
# R0 AST scoring, same rule as E0.
r0 = collections.defaultdict(list)
for f in sorted(OUT.glob("R0_*.md")):
    t = f.read_text(); s = f.stem.split("_")[1]
    blocks = re.findall(r"# file: (\S+)\n```python\n(.*?)```|```python\n# file: (\S+)\n(.*?)```", t, re.S)
    src = "\n".join((b or d) for a, b, c, d in blocks if (a or c).endswith(".py") and "errors" not in (a or c))
    try: tree = ast.parse(src)
    except Exception: r0[s].append("PARSE-FAIL"); continue
    fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    if s == "S1":
        w = [n for n, fn in fns.items() if "csv.writer" in ast.unparse(fn)]
        r0[s].append("compose" if len(w) == 1 else f"writers={w}")
    else:
        sc = fns.get("shipping_cost"); args = [a.arg for a in sc.args.args + sc.args.kwonlyargs] if sc else None
        tax = [n for n, fn in fns.items() if "taxable" in ast.unparse(fn)]
        r0[s].append("separate" if args == ["order"] and tax and "shipping_cost" not in tax else f"fused args={args}")
res = {"R0": dict(r0)}
def load_all(prefix):
    return {f.stem: jload(f.read_text()) for f in sorted(J.glob(prefix + "*.json")) if not f.stem.endswith(".layer")}
res["R3"] = load_all("R3_"); res["R45"] = load_all("R45_"); res["R6b"] = load_all("R6b_"); res["R7"] = load_all("R7_")
res["R7_layer"] = {f.stem: jload(f.read_text()) for f in J.glob("R7_*.layer.json")}
json.dump(res, open("after/verdicts_after.json", "w"), indent=1, sort_keys=True)
print("R0:", dict(r0))
def cnt(d, pred): return f"{sum(1 for v in d.values() if pred(v))}/{len(d)}"
r3 = res["R3"]
print("R3 intake:", {k: cnt(r3, lambda j, k=k: j.get(k)) for k in ("asks_players_devices", "asks_persistence", "asks_identity", "asks_hidden_info", "silent_single_browser")}, [j["question_count"] for j in r3.values()])
for q in ("invite", "solo"):
    d = {k: v for k, v in res["R45"].items() if f"_{q}_" in k}
    print(f"R45 {q}:", {k: cnt(d, f) for k, f in (
        ("srv", lambda j: j["state_authority"] == "server"), ("rt-id", lambda j: j["identity"] == "runtime-identity"),
        ("hidden", lambda j: j["hidden_info_protected"] is True), ("concur", lambda j: bool(j["concurrency_mechanism"])),
        ("EOL", lambda j: j["state_end_of_life"] is True), ("quota", lambda j: j["quotas_addressed"] is True),
        ("pii", lambda j: j.get("pii_identified") is True), ("retain", lambda j: j.get("retention_defined") is True),
        ("delete", lambda j: j.get("deletion_path") is True), ("logs", lambda j: j.get("logs_redacted") is True),
        ("inv-exp", lambda j: j.get("invite_expiry") is True))},
        "errs", sum(len(j.get("platform_errors") or []) for j in d.values()), "extra", sum(len(j.get("unrequested_features") or []) for j in d.values()))
r6 = res["R6b"]
print("R6b review: caught", sum(min(j["caught"], j["listed"]) for j in r6.values()), "/", sum(j["listed"] for j in r6.values()), "new errors", sum(len(j["new_platform_errors"]) for j in r6.values()), "over", len(r6))
print("R7 trust:", {k: (v["identified"], v["mitigated"], v["how"][:140]) for k, v in res["R7"].items()})
print("R7 layer:", {k: {kk: vv for kk, vv in v.items()} for k, v in res["R7_layer"].items()})
