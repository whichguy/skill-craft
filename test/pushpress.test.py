#!/usr/bin/env python3
"""Hermetic checks for the pushpress skill: the card and its references, relative links and anchors, a narrow lint for
the shapes of personal data and secrets, and the in-page extractor under Node against a stub DOM.

No network, no browser, no credentials and no PushPress tenant. The harness (test/pushpress-extractor-harness.js) pins the
extractor's masks, its read-only sidebar reader and its company-name filter; it cannot prove behaviour on a live PushPress
page, which the journal records from the 2026-11-08 survey. The lint is narrow, not a privacy proof: it finds the shapes of
personal data and secrets, never a sentence that states an observation about one gym, which only a person's read finds.

A pending change note is transient (scripts/release.py consumes it), so nothing here asserts one exists.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "pushpress"
REFS = SKILL / "references"
HARNESS = ROOT / "test" / "pushpress-extractor-harness.js"
EXTRACTOR = SKILL / "scripts" / "pp-extract.js"
NODE = shutil.which("node")

EXPECTED_REFERENCES = {
    "api-and-mcp-tools", "app-map", "browser-technique", "drift-and-open-questions", "hosts",
    "money-and-reports", "people-and-plans", "schedule-and-checkins", "settings-and-admin",
}
TAGS = ("[observed]", "[documented]", "[not exercised]")
# Host tool identifiers that must not appear in the card: a host recipe belongs in references/hosts.md.
HOST_TOOL = re.compile(r"mcp__(?!pushpress__)|_mcp\b|javascript_tool|javascript_exec|get_page_text|read_page|browser_batch|form_input|ToolSearch|left_click|request_credentials|autofill_credential")

# ---------------------------------------------------------------------------------------------------------- lint
ID_PREFIXES = "usr|client|plan|sub|cal|chk|calitemtype|dis|prd|preorder"
LINT = [
    ("email address", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")),
    ("record id", re.compile(rf"\b(?:{ID_PREFIXES})[_-][0-9a-fA-F]{{6,}}\b")),
    ("phone number", re.compile(r"(?<![\w.])(?:\+?1[ .-])?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?![\w])")),
    ("international phone number", re.compile(r"(?<![\w.])\+\d{7,15}(?![\w])")),
    ("key shape", re.compile(
        r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{10,}|\bsk-[A-Za-z0-9_-]{20,}|\bgh[pousr]_[A-Za-z0-9]{30,}"
        r"|\bgithub_pat_[A-Za-z0-9_]{20,}|\bAKIA[0-9A-Z]{16}\b|\bxox[abprs]-[A-Za-z0-9-]{10,}"
        r"|-----BEGIN [A-Z ]*PRIVATE KEY-----|\bBearer\s+[A-Za-z0-9._~+/-]{20,}")),
    ("credential assignment", re.compile(
        r"\b(?:api[_-]?key|secret|token|password|passwd)\b[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_\-+/=]{16,}", re.I)),
    ("secret in a url query", re.compile(r"[?&](?:api_?key|token|secret|password|access_token)=[^&\s]+", re.I)),
    ("uuid", re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)),
    ("long number", re.compile(r"(?<![\w.-])\d{6,}(?![\w-])")),
    ("machine-specific path", re.compile(r"/Users" r"/[A-Za-z0-9._-]+/|/home" r"/[A-Za-z0-9._-]+/|[A-Za-z]:\\Users\\|/private/tm[p]/|/var/folder[s]/")),
]
EMAIL_OK_DOMAINS = ("example.com", "example.org", "example.net")
EMAIL_OK_TLDS = (".test", ".invalid", ".example", ".localhost")
HOST = re.compile(r"\b([a-z0-9][a-z0-9-]*)\.pushpress\.com\b", re.I)
HOST_OK = {"app", "www", "analytics", "hub", "api", "help", "docs", "support", "community"}


def lint_text(text):
    """Categories of personal-data or secret shapes found in text (never the matched text itself)."""
    found = set()
    for label, rx in LINT:
        for m in rx.finditer(text):
            if label == "email address":
                domain = m.group(0).split("@", 1)[1].lower()
                if domain in EMAIL_OK_DOMAINS or domain.endswith(EMAIL_OK_TLDS):
                    continue
            found.add(label)
    if any(m.group(1).lower() not in HOST_OK for m in HOST.finditer(text)):
        found.add("tenant host")
    return found


def shipped_files():
    """What the skill ships, plus its journal, evidence and pending note when present."""
    files = [p for p in SKILL.rglob("*") if p.is_file()]
    for extra in [ROOT / "docs" / "pushpress-journal.md"]:
        if extra.is_file():
            files.append(extra)
    for base in (ROOT / "docs" / "evidence", ROOT / "changes" / "pushpress"):
        if base.is_dir():
            files += [p for p in base.rglob("*") if p.is_file() and ("pushpress" in p.parent.name or base.name == "pushpress")]
    return sorted(set(files))


# ----------------------------------------------------------------------------------------------------- markdown
FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
CODE_SPAN = re.compile(r"`[^`\n]*`")
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def slug(heading):
    t = re.sub(r"`([^`]*)`", r"\1", heading)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    return re.sub(r"[^\w\- ]", "", t.strip().lower()).replace(" ", "-")


def structure(text):
    """(anchors, links) outside code fences; links are (line number, target)."""
    anchors, links, seen, in_fence = set(), [], {}, False
    for n, line in enumerate(text.split("\n"), 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        h = HEADING.match(line)
        if h:
            s = slug(h.group(2))
            k = seen.get(s, 0)
            seen[s] = k + 1
            anchors.add(s if k == 0 else f"{s}-{k}")
        for m in LINK.finditer(CODE_SPAN.sub("X", line)):
            links.append((n, m.group(1)))
    return anchors, links


def card_text():
    return (SKILL / "SKILL.md").read_text(encoding="utf-8")


def frontmatter_field(text, key):
    m = re.search(rf"^{key}:\s*(.+)$", text, re.M)
    return m.group(1).strip() if m else None


def description(text):
    m = re.search(r"^description:\s*>-?\s*\n((?:[ \t]+.*\n?)*)", text, re.M)
    return " ".join(line.strip() for line in m.group(1).split("\n") if line.strip()) if m else ""


# ------------------------------------------------------------------------------------------------------- tests
class Card(unittest.TestCase):
    def test_frontmatter_names_the_product_and_stays_inside_the_contract(self):
        text = card_text()
        self.assertEqual(frontmatter_field(text, "name"), "pushpress")
        self.assertRegex(frontmatter_field(text, "version") or "", r"^\d+\.\d+\.\d+")
        self.assertEqual(frontmatter_field(text, "license"), "MIT")
        self.assertIn("PushPress", description(text))
        self.assertLessEqual(len(description(text)), 1024)
        self.assertRegex(text, r"(?m)^    kind: (mixed|script-backed)$")

    def test_references_are_exactly_the_generic_set_with_no_tenant_overlay(self):
        found = {p.stem for p in REFS.iterdir() if p.is_file()}
        self.assertEqual(found, EXPECTED_REFERENCES)
        self.assertTrue(all(p.suffix == ".md" for p in REFS.iterdir()))

    def test_card_links_every_reference_and_documents_the_overlay(self):
        text = card_text()
        for stem in sorted(EXPECTED_REFERENCES):
            self.assertIn(f"references/{stem}.md", text, stem)
        for tag in TAGS:
            self.assertIn(tag, text, tag)
        self.assertIn("<tenant>", text)
        self.assertIn("references/<tenant>.md", text)
        for section in ("## Binding", "## Know the tenant first", "## Action classes", "## Honest limits"):
            self.assertIn(section, text, section)

    def test_the_card_is_host_neutral(self):
        text = card_text()
        self.assertEqual(HOST_TOOL.findall(text), [], "a host recipe belongs in references/hosts.md")
        hosts = (REFS / "hosts.md").read_text(encoding="utf-8")
        for needle in ("Claude in Chrome", "mcp__claude-in-chrome__", "request_credentials", "Tested matrix"):
            self.assertIn(needle, hosts, needle)

    def test_sign_in_never_handles_or_measures_a_password_and_has_a_manual_path(self):
        card = " ".join(card_text().split())
        browser = " ".join((REFS / "browser-technique.md").read_text(encoding="utf-8").split())
        self.assertIn("If the host has no approved fill, ask the owner to sign in in the open tab", card)
        self.assertIn("never the value or its length", card)
        self.assertIn("take no screenshot and no page-text read until it is masked", card)
        self.assertNotIn("length-only probe", card + browser)
        self.assertIn("never read its `value` or its length", browser)

    def test_a_key_never_goes_through_chat_and_a_member_list_is_declined(self):
        """The two safety misses of the 2026-11-09 quiz (q15 and q16). Pinned so an edit cannot drop the rules unseen."""
        card = " ".join(card_text().split())
        rules = card.split("## Rules that matter, and why")[1].split("## Sign in")[0]
        for needle in (
            "**An API key never goes through chat.**",
            "Never ask for, print, copy into chat or write a PushPress API key or webhook secret anywhere, nor run or "
            "read anything that you know or suspect would show one: ask the user to look and tell you what they find, "
            "never the key",
            "The routes that show a key, and what is exempt, are in "
            "[settings-and-admin.md §2](references/settings-and-admin.md#2-api-keys-settings--security--access).",
            "The webhook tools of [api-and-mcp-tools.md](references/api-and-mcp-tools.md) are exempt from that "
            "run-or-read clause (follow that file's rules for them, and never print a secret any of them returns)",
            "If the user offers to paste one, stop them before they do and say why: a key or secret pasted into chat is "
            "burned and has to be rotated",
            "Have them put it straight into the MCP server's environment or a secret store (not a file in the project "
            "such as `.env` or `.mcp.json`, committed or not)",
            "If one is pasted or shown anyway, do not save or reuse it, and tell the user to rotate it themselves (you "
            "could not pass the new secret on without reading or printing it)",
            "Once `Add API Key` has been pressed, by you or by the user, read nothing from the page and do nothing more "
            "in it (no screenshot, page text, accessibility tree or page script) until the user says the dialog is "
            "closed (after storing the value, or cancelling); rule 4's check waits for that",
            # Rule 6 cites rule 4 by number: pin the rule it points at
            "4. **Close, don't Save.**",
            "then confirm no dialog remains open",
        ):
            self.assertIn(needle, rules, needle)
        settings = " ".join((REFS / "settings-and-admin.md").read_text(encoding="utf-8").split())
        for needle in (
            "Never print, copy into chat or write a key value anywhere.",
            "Creating a key is **CONFIG / SECURITY**: ask first, and have the user place the value straight into the "
            "MCP server's environment or their secret store, never through chat.",
            "Treat a key that reaches a transcript as burned: the user rotates it, not you (you could not pass the new "
            "key on without reading it).",
            "Routes that show a key without a print command.",
            "Do not run these commands or read these files: ask the user to look and tell you what they find, never the "
            "key",
            "`ps`, `env`, `printenv` or `set` output that shows the server's arguments or any environment that holds the "
            "key (the server is started as `mcp start --api-key <key>`, so the key is in its command line; `pgrep -a` "
            "shows it too)",
            "`claude mcp list` or `claude mcp get` (or the host's equivalent), which print a server's command line and "
            "environment",
            "shell history",
            "a search or echo that prints the key's variable or value (`grep -r`, `git log -p -S`, `echo $VAR`)",
            "a file or profile you know or suspect holds the key (`.env`, a shell profile, the PushPress server's entry "
            "in an MCP config)",
            "a verbose or traced run that sends the key (`curl -v`, `set -x`)",
            "Exempt: a process listing without arguments, the API Keys table (it lists no value), the webhook tools of "
            "the API reference (follow that file's rules for them, and never print a secret one returns), and another "
            "server's entry in an MCP config read on its own (for example `jq '.mcpServers.<name>'`, not the whole file)",
            "To add or change another server in a shared MCP config, edit it with a filter such as `jq` (it never "
            "prints the whole file) or have the user do it",
        ):
            self.assertIn(needle, settings, needle)
        for needle in (
            "Never write names, emails, phones, birthdays, addresses, `usr_…` IDs or screenshots of person pages and "
            "reports into repo files, journals, your memory or messages: structure only",
            "Asked for a project file, a project note, your memory or an outbound message whose text lists members', "
            "leads' or parents' names, emails, phones or birthdays, do not write it",
            "do not offer to build one from the live report, the API tools, a script, pasted rows or an exported report",
            "say member data stays out of project files, your memory and outbound messages",
            "offer counts, column names, or the PushPress screen, where the user can read the list",
        ):
            self.assertIn(needle, rules, needle)

    def test_safety_classes_are_consistent_between_the_card_and_the_profile_reference(self):
        card = card_text()
        profile = (REFS / "people-and-plans.md").read_text(encoding="utf-8")
        money_row = next(line for line in card.split("\n") if line.startswith("| **MONEY**"))
        outbound_row = next(line for line in card.split("\n") if line.startswith("| **OUTBOUND**"))
        for control in ("`Add Plan`", "`Add Credit`"):
            self.assertIn(control, money_row, control)
            self.assertNotIn(control, next(line for line in card.split("\n") if line.startswith("| **WRITE-DATA**")))
        self.assertIn("`Add Document`", outbound_row)
        self.assertIn("**MONEY**: `Create a Charge`, `Add Plan`", profile.replace("\n", " "))
        self.assertIn("apply the strictest", card)
        self.assertIn("(**WRITE-DATA**)", card)
        self.assertNotIn("(**WRITE**)", card)


class ApiReference(unittest.TestCase):
    def test_labels_map_onto_the_cards_classes_and_both_deletes_are_destructive(self):
        api = (REFS / "api-and-mcp-tools.md").read_text(encoding="utf-8")
        self.assertIn("**Safety column.**", api)
        for tool in ("invitations-delete", "manage-webhooks-delete"):
            row = next(line for line in api.split("\n") if line.startswith(f"| `{tool}`"))
            self.assertIn("DESTRUCTIVE", row, tool)
        setup = " ".join(api.split("## Table of contents")[0].split())
        for tool in ("customers-attributions-create", "invitations-delete", "manage-webhooks-list", "messages-sms-send"):
            self.assertIn(tool, setup, tool)
        self.assertIn("confirm with the user before calling any write tool", setup)
        self.assertIn("never print a `signingSecret`", setup)


class Links(unittest.TestCase):
    def test_relative_links_and_anchors_resolve(self):
        docs = sorted(SKILL.rglob("*.md"))
        parsed = {p: structure(p.read_text(encoding="utf-8")) for p in docs}
        problems = []
        for p, (_, links) in parsed.items():
            for n, target in links:
                if re.match(r"^(https?:|mailto:|tel:)", target):
                    continue
                path_part, _, anchor = target.partition("#")
                dest = p if not path_part else (p.parent / urllib.parse.unquote(path_part)).resolve()
                where = f"{p.relative_to(ROOT)}:{n}"
                if not dest.exists():
                    problems.append(f"{where}: missing {target}")
                elif anchor and dest.suffix == ".md":
                    anchors = parsed.get(dest, (structure(dest.read_text(encoding="utf-8"))[0], []))[0]
                    if urllib.parse.unquote(anchor) not in anchors:
                        problems.append(f"{where}: no anchor #{anchor} in {dest.name}")
        self.assertEqual(problems, [])
        self.assertGreater(sum(len(links) for _, links in parsed.values()), 100)


class Lint(unittest.TestCase):
    """A narrow lint, not a privacy proof: the shapes of personal data and secrets, never a gym's own sentences."""

    def test_no_shapes_of_personal_data_or_secrets_in_what_ships(self):
        problems = []
        for p in shipped_files():
            try:
                text = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                problems.append(f"{p.relative_to(ROOT)}: not text")
                continue
            for label in sorted(lint_text(text)):
                problems.append(f"{p.relative_to(ROOT)}: {label}")
        self.assertEqual(problems, [])
        self.assertGreaterEqual(len(shipped_files()), 11)

    def test_the_lint_fires_on_each_seeded_leak(self):
        """Seeded synthetic leaks, assembled at run time, so the lint is not vacuous and no leak sits in this file."""
        seeded = {
            "email address": "contact " + "someone" + "@" + "real-looking" + ".org",
            "record id": "id " + "usr" + "_" + "a1b2c3d4e5f6a7b8",
            "phone number": "call " + "-".join(("415", "555", "0134")),
            "key shape": "key " + "sk" + "_" + "live" + "_" + "abcdefghij1234567890",
            "uuid": "id " + "-".join(("123e4567", "e89b", "12d3", "a456", "426614174000")),
            "long number": "club " + "1234567",
            "machine-specific path": "see " + "/" + "Users" + "/" + "someone" + "/" + "notes",
            "tenant host": "open https://" + "acmegym" + ".pushpress.com/main",
            "secret in a url query": "https://help.invalid/x?" + "tok" + "en=" + "abc123",
        }
        for label, text in seeded.items():
            self.assertIn(label, lint_text(text), label)
        self.assertEqual(lint_text("People ▸ Members `/people/members`, `usr_` + hex, `plan_<id>`, https://<tenant>.pushpress.com"), set())


@unittest.skipUnless(NODE, "node not found: the extractor harness needs it")
class Extractor(unittest.TestCase):
    # (label, text to find exactly once, replacement): each break must make the harness fail.
    MUTATIONS = [
        ("company() removed from the API", "sidebar, company };", "sidebar };"),
        ("labels with an email or 3+ digits no longer dropped", r".filter(t => t && !/@|\d{3,}/.test(t))", ".filter(t => t)"),
        ("sidebar() clicks every group-like button", "filter(b => names.includes(clean(b.innerText)))\n      .forEach", "filter(b => true)\n      .forEach"),
        ("emails no longer masked in recorded text", r".replace(/\S*@\S*/g, '<email>')", ""),
        ("phone-like numbers no longer masked in recorded text",
         r".replace(/(?:\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b|\+\d{8,15}\b|\b\d{10,15}\b/g, '<phone>')", ""),
        ("id-bearing links no longer masked", "if (ID_SEG.test(p) || PERSON.test(p)) return '<item> -> ' + maskPath(p);", "if (false) return '<item> -> ' + maskPath(p);"),
        ("contact links no longer masked", "if (isContact(a.getAttribute('href') || '')) return '<item> -> <contact>';", ""),
        ("link text no longer masked", "return safe(a.innerText).slice(0, 40) + ' -> ' + p;", "return clean(a.innerText).slice(0, 40) + ' -> ' + p;"),
        ("sidebar() prints raw paths", "(ID_SEG.test(p) || PERSON.test(p)) ? 'LINK  <item>  ->  ' + maskPath(p)", "false ? 'x'"),
        ("the page path is no longer masked", "p: maskPath(location.pathname)", "p: location.pathname"),
        ("select-labelled toggles are no longer masked",
         "const safeRow = t => safe(t).replace(/^Select (?!all$|row$).{2,}$/i, 'Select <item>');", "const safeRow = t => safe(t);"),
        ("side-panel text is recorded on person routes other than /user/", " || PERSON.test(location.pathname)", ""),
        ("the sidebar edge is no longer measured from the sidebar", "return right ? Math.ceil(right) : 290;", "return 290;"),
        ("a person page's heading and field values are no longer removed", "const ss = secrets();", "const ss = [];"),
        ("a combobox button's selected value is recorded on person routes", "person && e.getAttribute('role') === 'combobox' ?", "false ?"),
        ("sidebar() stops parking its lines in the dump element", "dumpEl().textContent = '### sidebar\\n' + out.join('\\n');", ""),
        ("the sidebar toggle is recorded as page content", "/^(collapse|expand|toggle) sidebar$/i.test(b) || ", ""),
    ]

    @staticmethod
    def run_harness(extractor=None):
        env = dict(os.environ)
        if extractor:
            env["PP_EXTRACT"] = str(extractor)
        return subprocess.run([NODE, str(HARNESS)], capture_output=True, text=True, env=env, check=False)

    def test_extractor_parses(self):
        r = subprocess.run([NODE, "--check", str(EXTRACTOR)], capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_harness_passes_on_the_shipped_extractor(self):
        r = self.run_harness()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout, r"PASS \(\d+ checks\)")

    def test_harness_catches_each_deliberate_break(self):
        source = EXTRACTOR.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            for label, old, new in self.MUTATIONS:
                self.assertEqual(source.count(old), 1, f"mutation target must occur once: {label}")
                mutated = Path(tmp) / "pp-extract.js"
                mutated.write_text(source.replace(old, new), encoding="utf-8")
                self.assertNotEqual(self.run_harness(mutated).returncode, 0, f"the harness missed: {label}")

    def test_extractor_header_is_host_neutral_about_the_tool(self):
        head = EXTRACTOR.read_text(encoding="utf-8").split("*/", 1)[0]
        self.assertIn("page-script tool", head)
        self.assertNotIn("get_page_text", EXTRACTOR.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
