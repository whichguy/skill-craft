#!/usr/bin/env python3
"""Hermetic checks for the sport80 skill: the catalogue, the CLI contract, drift detection and the in-page runtime.

No network, no browser, no credentials. Node is required: the runtime and the generated discovery script run under Node
against a fake portal (test/sport80-runtime-harness.js). That pins request construction and result handling; it cannot
prove browser CORS, cookie behaviour or portal compatibility, which the journal records from consented live smoke checks.
"""
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "sport80"
sys.path.insert(0, str(SKILL / "scripts"))
import sport80 as S  # noqa: E402

CLI = [sys.executable, str(SKILL / "scripts" / "sport80.py")]
EVIDENCE = ROOT / "docs" / "evidence" / "sport80-discovery-20261108"
LIVE = EVIDENCE / "live-discovery.json"
HARNESS = ROOT / "test" / "sport80-runtime-harness.js"
NODE = shutil.which("node")


def cli(*args, env=None):
    return subprocess.run(CLI + list(args), check=False, capture_output=True, text=True, env=env)


def doc():
    return copy.deepcopy(S.load())


def entry(d, i):
    return next(e for e in d["entries"] if e["id"] == i)


class Catalogue(unittest.TestCase):
    def test_catalogue_validates(self):
        self.assertEqual(S.validate(S.load()), [])

    def test_safety_invariants_for_named_entries(self):
        e = {x["id"]: x for x in S.load()["entries"]}
        for i in ("account.logout", "account.security"):
            self.assertEqual((e[i]["mode"], e[i]["effects"]), ("owner-only", ["security"]), i)
        for i in ("orders.checkout", "orders.donation", "events.enter", "member.add_on", "account.auto_renewal", "admin.bulk_renewal.renew", "sanction.new"):
            self.assertEqual(e[i]["mode"], "guided", i)
            self.assertIn("financial", e[i]["effects"], i)
            self.assertRegex(e[i]["confirm"], r"(?i)card", i)
        self.assertEqual((e["members.send_email"]["mode"], e["members.send_email"]["effects"]), ("guided", ["outbound"]))
        self.assertEqual(e["members.create_subscriber_group"]["effects"], ["write"])
        self.assertEqual(e["members.download_report"]["effects"], ["export"])
        self.assertEqual(e["club.setup"]["mode"], "guided")
        for i in ("club.notes", "member.addresses", "member.background_screening", "member.safesport", "member.certifications", "member.collegiate_eligibility",
                  "orders.history", "affiliation.affiliations", "affiliation.blocks", "members.quick_search", "finance.stripe.disputes", "account.settings.access"):
            self.assertEqual(e[i]["data"], "sensitive", i)
        self.assertEqual(e["results.events"]["roles"]["club"]["scope"], "scoped to the club's athletes")

    def test_both_roles_and_every_area_are_covered(self):
        d = S.load()
        self.assertEqual({e["area"] for e in d["entries"]}, {"account", "dashboard", "members", "member", "club", "events", "sanction", "results", "orders", "admin", "finance", "affiliation"})
        roles = {r for e in d["entries"] for r in e["roles"]}
        self.assertEqual(roles, {"personal", "club", "public"})
        self.assertGreaterEqual(len(d["entries"]), 100)

    def test_runnable_means_read_and_exercised(self):
        d = S.load()
        out = json.loads(cli("catalog", "--runnable", "--json").stdout)
        self.assertGreater(len(out), 50)
        for e in out:
            self.assertEqual(e["mode"], "read", e["id"])
            self.assertTrue({r["verified"] for r in e["roles"].values()} & S.USABLE, e["id"])
        unverified = [e for e in d["entries"] if e["mode"] == "read" and not ({r["verified"] for r in e["roles"].values()} & S.USABLE)]
        self.assertTrue(unverified, "menu-only entries stay listed but are not offered as runnable")
        self.assertFalse({e["id"] for e in unverified} & {e["id"] for e in out})

    def test_coverage_ledger_is_complete_against_the_recorded_live_run(self):
        d = S.load()
        live = json.loads(LIVE.read_text())
        ledger = {(n["role"], n["trail"]) for n in d["coverage"]["menu_nodes"]}
        self.assertEqual({(n["role"], n["trail"]) for n in live["nodes"]}, ledger)
        self.assertEqual(set(live["pages"]), {p["component"] for p in d["coverage"]["pages"]})
        for p in d["coverage"]["pages"]:
            if p["surface"] in ("unmapped", "out-of-scope", "inaccessible"):
                self.assertTrue(p["reason"], p["component"])

    def test_the_validator_catches_each_kind_of_breakage(self):
        cases = []
        d = doc(); entry(d, "orders.checkout").pop("confirm"); cases.append((d, "need confirm"))
        d = doc(); entry(d, "orders.checkout")["confirm"] = "Completes a purchase."; cases.append((d, "never to enter card"))
        d = doc(); entry(d, "members.quick_search")["effects"] = ["read", "write"]; cases.append((d, "effects [read] only"))
        d = doc(); entry(d, "account.menu.main")["kind"] = "carrier-pigeon"; cases.append((d, "bad kind"))
        d = doc(); d["coverage"]["menu_nodes"][0]["entry"] = "no.such.entry"; cases.append((d, "unknown entry"))
        d = doc(); d["entries"].append(copy.deepcopy(d["entries"][0])); cases.append((d, "duplicate id"))
        d = doc(); entry(d, "club.notes")["notes"] = "ask someone@example.org"; cases.append((d, "email address"))
        d = doc(); entry(d, "account.roles")["notes"] = "id 123e4567-e89b-12d3-a456-426614174000"; cases.append((d, "uuid"))
        d = doc(); entry(d, "account.roles")["notes"] = "club 1234567"; cases.append((d, "long number"))
        d = doc(); entry(d, "member.memberships")["via"]["param"] = "undeclared"; cases.append((d, "via param"))
        d = doc(); entry(d, "events.find")["params"] = [p for p in entry(d, "events.find")["params"] if p["name"] != "type"]; cases.append((d, "placeholder"))
        d = doc(); entry(d, "members.quick_search")["requires_filter"] = ["ghost"]; cases.append((d, "undeclared filter"))
        d = doc(); entry(d, "account.logout")["effects"] = ["read"]; entry(d, "orders.donation")["effects"] = ["security"]; cases.append((d, "security effects are owner-only"))
        d = doc(); entry(d, "results.events")["auth"] = "maybe"; cases.append((d, "auth"))
        d = doc(); entry(d, "orders.history")["roles"]["personal"]["verified"] = "sure"; cases.append((d, "bad verified"))
        d = doc(); d["coverage"]["pages"][0]["surface"] = "mystery"; cases.append((d, "bad surface"))
        for broken, needle in cases:
            errs = S.validate(broken)
            self.assertTrue(any(needle in x for x in errs), f"{needle!r} not reported: {errs[:3]}")


class Cli(unittest.TestCase):
    def test_catalog_filters_and_json(self):
        owner = json.loads(cli("catalog", "--mode", "owner-only", "--json").stdout)
        self.assertEqual({e["id"] for e in owner}, {"account.logout", "account.security"})
        club = json.loads(cli("catalog", "--role", "club", "--area", "finance", "--json").stdout)
        self.assertTrue(club and all(e["area"] == "finance" and "club" in e["roles"] for e in club))
        text = cli("catalog", "--data", "sensitive").stdout
        self.assertIn("members.quick_search", text)
        self.assertRegex(text, r"\d+ of \d+ entries")

    def test_show_prints_what_an_agent_needs(self):
        read = cli("show", "members.quick_search").stdout
        for needle in ("mode: read", "data: sensitive", "requires at least one filter", "run: sport80 js members.quick_search"):
            self.assertIn(needle, read)
        guided = cli("show", "orders.checkout").stdout
        self.assertIn("confirm:", guided); self.assertIn("never enter card", guided); self.assertIn("refuses it", guided)
        r = cli("show", "no.such.thing"); self.assertEqual(r.returncode, 2)

    def test_js_refuses_what_it_must(self):
        for args, needle in [
            (("js", "orders.checkout"), "guided"), (("js", "account.logout"), "owner-only"), (("js", "no.such.thing"), "no capability"),
            (("js", "events.admin.panel", "--role", "club", "--param", "eid=1"), "not offered as runnable"),
            (("js", "members.quick_search", "--role", "club", "--filter", "first_name=A", "--rows", "5"), "sensitive"),
            (("js", "results.events", "--param", "nope=1"), "no parameter"), (("js", "dashboard.athlete", "--role", "club"), "not offered for role"),
        ]:
            r = cli(*args)
            self.assertEqual(r.returncode, 2, args)
            self.assertIn(needle, r.stdout, args)

    def test_role_can_name_one_club_of_several(self):
        r = cli("js", "results.events", "--role", "7", "--rows", "0")
        self.assertEqual(r.returncode, 0, r.stdout)
        opts = json.loads(re.search(r"\}, (\{.*\})\)", r.stdout).group(1))
        self.assertEqual(opts["role"], "7")
        self.assertIn("verified live", r.stdout)
        refused = cli("js", "dashboard.athlete", "--role", "7")
        self.assertEqual(refused.returncode, 2)
        self.assertIn("not offered for role 7", refused.stdout)

    def test_js_generates_runnable_snippets(self):
        r = cli("js", "results.events", "--role", "club", "--filter", "date_range_start=2026-01-01", "--rows", "100", "--fields", "meet,results")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Load the runtime first", r.stdout); self.assertIn("await S80.exec(", r.stdout)
        call = re.search(r"await S80\.exec\((\{.*\}), (\{.*\})\)", r.stdout)
        entry_json, opts = json.loads(call.group(1)), json.loads(call.group(2))
        self.assertEqual((entry_json["id"], entry_json["host"], entry_json["auth"], entry_json["verified"]), ("results.events", "rankings", "role", "live"))
        self.assertEqual(opts, {"role": "club", "filters": {"date_range_start": "2026-01-01"}, "fields": ["meet", "results"], "maxRows": 100})
        self.assertNotRegex(r.stdout, r"(?i)password|cookie|secret|bearer")
        fn = cli("js", "account.roles", "--wrap", "function").stdout
        self.assertIn("async () => {", fn)
        un = cli("js", "events.admin.panel", "--role", "club", "--param", "eid=1", "--unverified")
        self.assertEqual(un.returncode, 0); self.assertIn('"verified":"none"', un.stdout)
        counts = cli("js", "members.quick_search", "--role", "club", "--filter", "first_name=A", "--rows", "0")
        self.assertEqual(counts.returncode, 0)

    @unittest.skipUnless(NODE, "node is required")
    def test_generated_snippets_parse(self):
        with tempfile.TemporaryDirectory() as t:
            for name, args in (("expr", ["js", "account.roles"]), ("fn", ["js", "account.roles", "--wrap", "function"]), ("bundle", ["js", "orders.history", "--role", "club", "--rows", "0", "--with-runtime"])):
                p = Path(t) / (name + ".mjs")
                p.write_text(cli(*args).stdout)
                r = subprocess.run([NODE, "--check", str(p)], check=False, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, (name, r.stderr))

    def test_runtime_and_discover_print_the_files(self):
        self.assertEqual(cli("runtime").stdout, (SKILL / "scripts" / "runtime.js").read_text())
        d = cli("discover").stdout
        self.assertNotIn("/*ALLOW*/", d); self.assertIn('"/home"', d); self.assertNotIn('"/logout"', d); self.assertNotIn('"/body/setup"', d)
        self.assertIn("never part of an ordinary request", d)

    def test_check_command_and_the_node_prerequisite(self):
        ok = cli("check"); self.assertEqual(ok.returncode, 0, ok.stdout)
        self.assertRegex(ok.stdout, r"\d+ entries, 0 problems")
        if NODE:
            self.assertNotIn("SKIPPED", ok.stdout)
        bare = dict(os.environ, PATH="/nonexistent")
        skipped = cli("check", env=bare)
        self.assertEqual(skipped.returncode, 0); self.assertIn("SKIPPED JavaScript syntax check", skipped.stdout)
        strict = cli("check", "--require-node", env=bare)
        self.assertEqual(strict.returncode, 1)

    def test_coverage_report(self):
        out = cli("coverage").stdout
        for needle in ("entries:", "menu nodes:", "front-end pages:", "gaps:", "scope unknowns:", "G1"):
            self.assertIn(needle, out)
        j = json.loads(cli("coverage", "--json").stdout)
        self.assertEqual(j["pages"]["out-of-scope"], 5)


class Diff(unittest.TestCase):
    def live(self):
        return json.loads(LIVE.read_text())

    def test_the_recorded_live_run_matches_the_catalogue(self):
        r = cli("diff", str(LIVE))
        self.assertEqual(r.returncode, 0, r.stdout[-800:])
        res = S.compute_diff(S.load(), self.live())
        self.assertEqual((res["unclassified"], res["missing"], res["changed"]), ([], [], []))
        self.assertTrue(res["gaps"], "blocked and unobserved nodes are reported, never hidden")
        self.assertEqual(res["pages"], {"new": [], "gone": []})

    def test_a_new_menu_item_and_a_new_page_are_unclassified(self):
        live = self.live()
        live["nodes"].append({"role": "club", "trail": "bottom > Brand New > Thing", "protocol": "datatable", "columns": ["a"]})
        live["pages"].append("Shiny/NewPage")
        res = S.compute_diff(S.load(), live)
        self.assertEqual([x["trail"] for x in res["unclassified"]], ["bottom > Brand New > Thing"])
        self.assertEqual(res["pages"]["new"], ["Shiny/NewPage"]); self.assertFalse(res["ok"])

    def test_a_removed_menu_item_is_missing(self):
        live = self.live()
        live["nodes"] = [n for n in live["nodes"] if n["trail"] != "bottom > Finance Admin > Stripe Disputes"]
        res = S.compute_diff(S.load(), live)
        self.assertEqual([x["entry"] for x in res["missing"]], ["finance.stripe.disputes"]); self.assertFalse(res["ok"])

    def test_descriptor_and_button_changes_are_reported(self):
        live = self.live()
        for n in live["nodes"]:
            if n["role"] == "club" and n["trail"] == "top > Members > Quick Search":
                n["columns"] = [c for c in n["columns"] if c != "email"] + ["phone"]
            if n["role"] == "club" and n["trail"] == "top > Account [profile tabs] > Notes":
                n["buttons"] = ["Add Note", "Export Notes"]
        res = S.compute_diff(S.load(), live)
        got = {(c["entry"], c["what"]): c for c in res["changed"]}
        self.assertEqual(got[("members.quick_search", "columns")]["added"], ["phone"]); self.assertEqual(got[("members.quick_search", "columns")]["removed"], ["email"])
        self.assertEqual(got[("club.notes", "buttons")]["added"], ["Export Notes"]); self.assertFalse(res["ok"])

    def test_gaps_do_not_fail_the_diff_but_a_stopped_run_is_refused(self):
        live = self.live()
        live["nodes"].append(dict(live["nodes"][0], trail="top > Home", protocol="unvisited", reason="x"))
        self.assertTrue(S.compute_diff(S.load(), live)["ok"])
        live["error"] = "AUTH_REQUIRED"
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "live.json"; p.write_text(json.dumps(live))
            r = cli("diff", str(p))
            self.assertEqual(r.returncode, 2); self.assertIn("AUTH_REQUIRED", r.stdout)

    def test_write_descriptors_touches_only_descriptors(self):
        with tempfile.TemporaryDirectory() as t:
            copy_root = Path(t) / "skill"
            shutil.copytree(SKILL, copy_root)
            before = json.loads((copy_root / "references" / "capabilities.json").read_text())
            for e in before["entries"]:
                e.pop("descriptor", None)
            (copy_root / "references" / "capabilities.json").write_text(json.dumps(before))
            r = subprocess.run([sys.executable, str(copy_root / "scripts" / "sport80.py"), "diff", str(LIVE), "--write-descriptors"], check=False, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout)
            after = json.loads((copy_root / "references" / "capabilities.json").read_text())
            self.assertEqual(S.load()["entries"], after["entries"])
            for b, a in zip(before["entries"], after["entries"]):
                self.assertEqual({k: v for k, v in a.items() if k != "descriptor"}, b)


class Runtime(unittest.TestCase):
    @unittest.skipUnless(NODE, "node is required")
    def test_runtime_scenarios_under_node(self):
        r = subprocess.run([NODE, str(HARNESS)], check=False, capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        results = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertGreaterEqual(len(results), 25)
        for res in results:
            with self.subTest(res["name"]):
                self.assertTrue(res["ok"], res.get("error"))

    def test_node_is_available(self):
        self.assertIsNotNone(NODE, "the sport80 suite requires Node to run the runtime scenarios")


class Hygiene(unittest.TestCase):
    """A narrow lint, not a privacy proof: no email addresses, UUID literals or long numeric ids in what the skill ships."""

    def paths(self):
        out = [p for p in SKILL.rglob("*") if p.is_file()] + [p for p in EVIDENCE.rglob("*") if p.is_file()] + [ROOT / "docs" / "sport80-journal.md"]
        return [p for p in out if p.suffix in (".md", ".json", ".js", ".py", ".txt", "") and "__pycache__" not in p.parts]

    def test_no_addresses_uuids_or_long_ids(self):
        rx = [("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")), ("uuid", re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)), ("long number", re.compile(r"(?<![\w.-])\d{6,}(?![\w-])"))]
        for p in self.paths():
            text = p.read_text()
            for label, r in rx:
                m = r.search(text)
                self.assertIsNone(m, f"{label} in {p.relative_to(ROOT)}: {m.group(0) if m else ''}")

    def test_the_card_and_references_exist_and_the_cli_is_executable(self):
        for rel in ("SKILL.md", "references/access.md", "references/protocols.md", "references/safety.md", "references/hosts.md", "references/capabilities.json", "scripts/runtime.js", "scripts/discover.js", "scripts/sport80.py"):
            self.assertTrue((SKILL / rel).is_file(), rel)
        self.assertTrue(os.access(SKILL / "scripts" / "sport80", os.X_OK))


class ClubMemberRecord(unittest.TestCase):
    """The club role's view of a member record, checked live on the owner's own record (journal Round 6)."""

    def test_the_club_view_is_catalogued_with_what_was_and_was_not_exercised(self):
        d = S.load()
        e = {x["id"]: x for x in d["entries"]}
        for i in ("member.profile_tabs", "member.memberships", "member.results"):
            self.assertEqual(e[i]["roles"]["club"]["verified"], "live", i)
        for i in ("member.background_screening_due_payment", "member.reps_membership", "member.additional_trackings", "member.notes"):
            self.assertEqual(list(e[i]["roles"]), ["club"], i)
            self.assertEqual((e[i]["mode"], e[i]["effects"], e[i]["roles"]["club"]["verified"]), ("read", ["read"], "live"), i)
            self.assertTrue(e[i]["params"][0]["required"] and "default" not in e[i]["params"][0], i)
        self.assertEqual(e["member.notes"]["data"], "sensitive")
        self.assertEqual(e["member.notes"]["operations"][0]["label"], "Add Note")
        a = e["member.archive"]
        self.assertEqual((a["mode"], a["effects"], a["roles"]["club"]["verified"]), ("guided", ["write"], "none"))
        self.assertRegex(a["confirm"], r"explicit yes")
        for i in ("member.addresses", "member.entries", "member.comm_prefs", "member.learning_academy.results", "member.learning_academy.access"):
            self.assertNotIn("club", e[i]["roles"], i)
        self.assertIn("member.archive", next(g for g in d["coverage"]["gaps"] if g["id"] == "G9")["entries"])

    def test_a_club_role_must_name_the_member(self):
        refused = cli("js", "member.profile_tabs", "--role", "club")
        self.assertEqual(refused.returncode, 2)
        self.assertIn("--param cid=", refused.stdout)
        self.assertIn("club's own contact id", refused.stdout)
        ok = cli("js", "member.profile_tabs", "--role", "club", "--param", "cid=42")
        self.assertEqual(ok.returncode, 0, ok.stdout)
        self.assertEqual(json.loads(re.search(r"\}, (\{.*\})\)", ok.stdout).group(1)), {"role": "club", "params": {"cid": "42"}})
        self.assertEqual(cli("js", "member.notes", "--role", "club", "--param", "cid=42", "--rows", "0").returncode, 0)
        self.assertEqual(cli("js", "member.notes", "--role", "club", "--param", "cid=42", "--rows", "5").returncode, 2, "sensitive rows need fields")
        self.assertEqual(cli("js", "member.archive", "--role", "club", "--param", "cid=42").returncode, 2, "a write is never a snippet")
        self.assertEqual(cli("js", "member.profile_tabs").returncode, 0, "the personal role keeps its default")


if __name__ == "__main__":
    unittest.main()
