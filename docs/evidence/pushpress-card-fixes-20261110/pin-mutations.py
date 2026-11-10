"""Does each pin of test_a_key_never_goes_through_chat_and_a_member_list_is_declined fire?

The pinned phrases are read from the test itself (its syntax tree), so there is no second copy to keep in step with it.
For every phrase, the card (or the settings reference) is mutated in memory so that exactly that phrase is gone, the one
test is run, and it must fail. Two structural mutations (the rules heading renamed; the rules moved out of their section)
are run as well, and the unmutated test is the control, before and after, and must pass. Nothing in the repository is
changed (a scratch copy of the references is made under the system temp directory and removed).
"""
import ast, importlib.util, io, json, shutil, sys, tempfile, unittest
from pathlib import Path

sys.dont_write_bytecode = True  # importing the test module must not leave a __pycache__ in test/
ROOT = Path(__file__).resolve().parents[3]  # docs/evidence/<folder>/pin-mutations.py -> the repository root
TEST = ROOT / "test" / "pushpress.test.py"
NAME = "test_a_key_never_goes_through_chat_and_a_member_list_is_declined"

spec = importlib.util.spec_from_file_location("pp_unit", TEST)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
orig_card = mod.card_text
orig_refs = mod.REFS

# The phrases the test pins, read from its syntax tree: every `for needle in (...)` loop of the test whose body is
# self.assertIn(needle, <rules or settings>, needle). Adjacent string literals are already joined by the parser.
tree = ast.parse(TEST.read_text(encoding="utf-8"))
fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == NAME)
CARD_NEEDLES, SETTINGS_NEEDLES = [], []
for node in ast.walk(fn):
    if not (isinstance(node, ast.For) and isinstance(node.iter, (ast.Tuple, ast.List))):
        continue
    target = None
    for stmt in node.body:
        call = getattr(stmt, "value", None)
        if (isinstance(call, ast.Call) and getattr(call.func, "attr", "") == "assertIn"
                and len(call.args) >= 2 and isinstance(call.args[1], ast.Name)):
            target = call.args[1].id
    needles = [e.value for e in node.iter.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
    assert len(needles) == len(node.iter.elts), "a pinned phrase that is not a plain string"
    {"rules": CARD_NEEDLES, "settings": SETTINGS_NEEDLES}[target].extend(needles)
assert CARD_NEEDLES and SETTINGS_NEEDLES


def run_one():
    out = io.StringIO()
    res = unittest.TextTestRunner(stream=out, verbosity=0).run(unittest.TestSuite([mod.Card(NAME)]))
    return res.wasSuccessful(), ("error" if res.errors else "failure" if res.failures else "ok")


results = []
ok, kind = run_one()
results.append({"mutation": "none (control)", "test_passes": ok, "kind": kind})
assert ok, "control must pass"

norm_card = " ".join(orig_card().split())
for n in CARD_NEEDLES:
    assert n in norm_card, f"needle not in the card: {n}"
    mod.card_text = lambda n=n: norm_card.replace(n, "XXXX")
    ok, kind = run_one()
    results.append({"mutation": f"card without: {n}", "test_passes": ok, "kind": kind})
mod.card_text = orig_card

# the heading the rules are split on, renamed: the pins must not pass on the whole card
mod.card_text = lambda: norm_card.replace("## Rules that matter, and why", "## Rules")
ok, kind = run_one()
results.append({"mutation": "heading 'Rules that matter, and why' renamed", "test_passes": ok, "kind": kind})
mod.card_text = orig_card

# the rules moved below the Sign in heading: the section split must not find them
moved = norm_card.split("## Rules that matter, and why")
rules_part, rest = moved[1].split("## Sign in", 1)
mod.card_text = lambda: moved[0] + "## Rules that matter, and why" + " 1. nothing here. " + "## Sign in" + rest + " " + rules_part
ok, kind = run_one()
results.append({"mutation": "the rules moved out of their section", "test_passes": ok, "kind": kind})
mod.card_text = orig_card

settings_raw = (orig_refs / "settings-and-admin.md").read_text(encoding="utf-8")
norm_settings = " ".join(settings_raw.split())
tmp = Path(tempfile.mkdtemp(prefix="pp-pin-"))
try:
    for n in SETTINGS_NEEDLES:
        assert n in norm_settings, f"needle not in settings: {n}"
        shutil.copytree(orig_refs, tmp / "refs", dirs_exist_ok=True)
        (tmp / "refs" / "settings-and-admin.md").write_text(norm_settings.replace(n, "XXXX"), encoding="utf-8")
        mod.REFS = tmp / "refs"
        ok, kind = run_one()
        results.append({"mutation": f"settings reference without: {n}", "test_passes": ok, "kind": kind})
finally:
    mod.REFS = orig_refs
    shutil.rmtree(tmp, ignore_errors=True)

ok, kind = run_one()
results.append({"mutation": "none (control, after)", "test_passes": ok, "kind": kind})

bad = [r for r in results if r["mutation"].startswith("none") != r["test_passes"]]
print(json.dumps(results, indent=1))
print("mutations that the test did NOT catch:", [r["mutation"] for r in bad if not r["mutation"].startswith("none")])
print("controls pass:", all(r["test_passes"] for r in results if r["mutation"].startswith("none")))
print("pinned phrases:", len(CARD_NEEDLES) + len(SETTINGS_NEEDLES), "(card", len(CARD_NEEDLES), "+ settings", len(SETTINGS_NEEDLES), ") + 2 structural mutations")
print("caught:", sum(1 for r in results if not r["mutation"].startswith("none") and not r["test_passes"]), "of", sum(1 for r in results if not r["mutation"].startswith("none")))
sys.exit(1 if bad else 0)
