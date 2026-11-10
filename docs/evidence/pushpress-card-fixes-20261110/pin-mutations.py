"""Does each pin of test_a_key_never_goes_through_chat_and_a_member_list_is_declined fire?

For every needle the test pins, the card (or the settings reference) is mutated in memory so that exactly that needle is
gone, the one test is run, and it must fail. The unmutated run is the control and must pass. Nothing in the repository is changed (a scratch copy of the references
is made under the system temp directory and removed). The needle lists below are this script's own copy of the phrases the
test pins: when the test's phrases change, change them here too; pin-mutations-result.txt records the commit it was run at.
"""
import importlib.util, io, json, shutil, sys, tempfile, unittest
from pathlib import Path

sys.dont_write_bytecode = True  # importing the test module must not leave a __pycache__ in test/
ROOT = Path(__file__).resolve().parents[3]  # docs/evidence/<folder>/pin-mutations.py -> the repository root
spec = importlib.util.spec_from_file_location("pp_unit", ROOT / "test" / "pushpress.test.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NAME = "test_a_key_never_goes_through_chat_and_a_member_list_is_declined"
orig_card = mod.card_text
orig_refs = mod.REFS


def run_one():
    out = io.StringIO()
    res = unittest.TextTestRunner(stream=out, verbosity=0).run(unittest.TestSuite([mod.Card(NAME)]))
    return res.wasSuccessful(), ("error" if res.errors else "failure" if res.failures else "ok")


CARD_NEEDLES = [
    "**An API key never goes through chat.**",
    "Never ask for, print, copy into chat or write a PushPress API key or webhook secret anywhere",
    "If the user offers to paste one, stop them before they do and say why: a key or secret pasted into chat is burned and has to be rotated",
    "Have them put it straight into the MCP server's environment or a secret store (not a file in the project, committed or not)",
    "If one is pasted anyway, do not save or reuse it, and tell the user to rotate it themselves",
    "a rotation done by you, through a tool or the page, would put the new secret in this transcript too",
    "Once `Add API Key` has been pressed, by you or by the user, read nothing from the page and do nothing more in it (no screenshot, page text, "
    "accessibility tree or page script) until the user says the value is stored and the dialog is closed; rule 4's check waits for that",
    "4. **Close, don't Save.**",
    "then confirm no dialog remains open",
    "into repo files, journals or messages: structure only",
    "Asked for a project file, a project note or an outbound message that lists members' names, emails, phones or birthdays, do not write it",
    "do not offer to build one from the live report, pasted rows or an exported report",
    "say member data stays out of project files and outbound messages",
    "offer counts, column names, or the PushPress screen, where the user can read the list",
]
SETTINGS_NEEDLES = ["never through chat", "burned and rotate it"]

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
