#!/usr/bin/env python3
"""Prepare four offline, fresh-context ShipLoop service-discovery fixtures.

This creates inputs only. It never starts an agent, connects remotely, or uses a credential.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / "skills" / "shiploop"


def put(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): digest(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def git_value(*args: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args], text=True, capture_output=True, check=False
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def freeze_source(out: Path) -> tuple[Path, dict[str, str]]:
    """Freeze packet code and Markdown references; never copy transient covers."""
    package = out / "source-snapshot" / "skills" / "shiploop"
    (package / "scripts").mkdir(parents=True)
    (package / "references").mkdir()
    selected = [SOURCE / "SKILL.md", SOURCE / "README.md"]
    selected += sorted(
        path for path in (SOURCE / "scripts").iterdir()
        if path.is_file() and (path.suffix == ".py" or path.name == "shiploop")
    )
    selected += sorted((SOURCE / "references").rglob("*.md"))
    source_hashes: dict[str, str] = {}
    for path in selected:
        relative = path.relative_to(SOURCE)
        target = package / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        source_hashes[str(relative)] = digest(path)
    return package, source_hashes


def crm_baseline(repo: Path) -> None:
    put(
        repo / "test_fixture.py",
        """import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parent / "src"))
from contact_panel import display_contact


class FixtureSmokeTest(unittest.TestCase):
    def test_panel_keeps_existing_display_fields(self):
        self.assertEqual(
            display_contact({"Name": "Example", "ComputedScore__c": 87}),
            {"name": "Example", "score": 87},
        )
""",
    )


def common_repo(repo: Path, title: str) -> None:
    put(
        repo / "README.md",
        f"""# {title}

Run python3 -B -m unittest discover -v before any product edit. Its fixture
smoke coverage is deliberately narrow.
""",
    )
    put(
        repo / "SHIPLOOP.md",
        """# Project knowledge

Read current source and decision notes before relying on a prior summary.
""",
    )


def seed_crm(repo: Path) -> None:
    common_repo(repo, "CRM review panel")
    put(
        repo / "src/contact_read_service.py",
        '''"""The runtime adapter always uses the app CRM service account."""


class ContactReadService:
    def __init__(self, cache, runtime):
        self.cache, self.runtime = cache, runtime

    def list_contacts(self, query):
        cached = self.cache.get(query)
        if cached is not None:
            return cached
        rows = self.runtime.query_contacts(query)
        self.cache.put(query, rows, ttl_seconds=600)
        return rows
''',
    )
    put(
        repo / "src/contact_panel.py",
        '''def display_contact(contact):
    return {"name": contact["Name"], "score": contact.get("ComputedScore__c")}
''',
    )
    put(
        repo / "src/app_audit.py",
        '''import logging

audit = logging.getLogger("app.audit")


def record_contact_change(contact_id, field):
    audit.info("contact_change", extra={"contact_id": contact_id, "field": field})
''',
    )
    put(
        repo / "workers/review_status_poller.py",
        '''"""Remote ReviewRequest.status is the durable status owner; this worker only polls it."""


def refresh_pending_reviews(remote, request_ids):
    return [remote.read_review_request(request_id)["status"] for request_id in request_ids]
''',
    )
    put(
        repo / "remote/contact-metadata.partial.json",
        json.dumps(
            {
                "as_of": "fixture",
                "coverage": "fields approved for the old panel only",
                "complete": False,
                "fields": ["Id", "Name", "Consent__c"],
            },
            indent=2,
        ),
    )
    put(
        repo / "remote/contact-record-shape.json",
        json.dumps(
            {
                "Id": "synthetic-contact",
                "Name": "Example",
                "Consent__c": True,
                "ComputedScore__c": 87,
                "Lifecycle__c": "active",
            },
            indent=2,
        ),
    )
    put(
        repo / "tools/identity-manifest.json",
        json.dumps(
            {
                "runtime_query": {
                    "identity": "crm-app-service",
                    "effect": "Contact data query",
                },
                "metadata_read": {
                    "identity": "crm-describe-reader",
                    "effect": "read-only describe",
                },
                "metadata_write": {
                    "identity": "crm-schema-writer",
                    "effect": "approval and target required",
                },
            },
            indent=2,
        ),
    )
    put(
        repo / "docs/async-and-observability.md",
        """# Existing operations

ReviewRequest.status is reread by the panel through the existing poller. A
notification, when connected, is only a prompt to reread the durable record.
The identity provider owns successful and failed interactive-login events.
app.audit already reaches the operator event sink for application-owned events;
do not duplicate provider login records there.
""",
    )
    crm_baseline(repo)


def seed_cold_plan(repo: Path) -> tuple[Path, str]:
    seed_crm(repo)
    current = repo / "docs/decisions/current-contact-review.md"
    put(
        current,
        """# Current contact-review decision

## Accepted contract

Keep Contact and ReviewRequest remote-authoritative. Bypass the existing raw
shared cache until the runtime establishes current row and field authorization
and a tested invalidation, late-fill, and missed-change recovery contract. Until
then, a read passes through current policy enforcement or is denied; the raw
cache is never a fallback. The old partial metadata snapshot is not an absence
proof. Reconcile an additive
pending-review field against current metadata and retain Consent__c,
ComputedScore__c, Lifecycle__c, and unrelated automation.

ReviewRequest.status remains the durable status owner; preserve its
polling/re-read path. Notifications remain hints. The identity provider owns
login success/failure records. Add the missing application-owned review-state
audit event through the existing app.audit sink, not a second login logger.
Revalidate current metadata target, row/field authority, cache invalidation
evidence, and worker/status ownership immediately before any later change.
""",
    )
    put(
        repo / "docs/decisions/2025-cache-prototype.md",
        """# Superseded cache prototype

Use one ten-minute cache entry per query and let the service account decide
access. This note predates the current authorization requirement and must not
be used for new work.
""",
    )
    put(
        repo / "SHIPLOOP.md",
        """# Project knowledge

- Current accepted remote-review contract:
  docs/decisions/current-contact-review.md#accepted-contract.
- docs/decisions/2025-cache-prototype.md is superseded and retained only as
  history.
""",
    )
    locator = str(current) + "#accepted-contract"
    context = (
        "Read " + locator + "; revalidate current row/field authorization and "
        "cache invalidation before choosing a read-path change."
    )
    return current, context


def seed_auth(repo: Path) -> None:
    common_repo(repo, "Local password-auth diagnostics")
    put(
        repo / "src/auth_service.py",
        '''class PasswordAuth:
    def __init__(self, logger, sessions):
        self.logger, self.sessions = logger, sessions

    def authenticate(self, username, password, valid):
        if not valid:
            self.logger.info(
                "login_failed", extra={"subject": username, "method": "password"}
            )
            raise PermissionError("invalid credentials")
        return self.sessions.issue(username)
''',
    )
    put(
        repo / "docs/operations.md",
        """# Local operations

The structured app.audit logger is collected by the existing operator event
sink. Failed password attempts are ordinary authentication outcomes unless
incident rules classify them; do not log passwords, tokens, or session contents.
""",
    )
    put(
        repo / "test_fixture.py",
        """import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parent / "src"))
from auth_service import PasswordAuth


class Logger:
    def __init__(self):
        self.events = []

    def info(self, event, **details):
        self.events.append((event, details))


class Sessions:
    def __init__(self):
        self.issued = []

    def issue(self, subject):
        self.issued.append(subject)
        return "synthetic-session"


class ExistingAuthBehaviorTest(unittest.TestCase):
    def test_failed_password_attempt_is_logged_without_session(self):
        logger, sessions = Logger(), Sessions()
        with self.assertRaises(PermissionError):
            PasswordAuth(logger, sessions).authenticate("sam", "wrong", False)
        self.assertEqual(logger.events[0][0], "login_failed")
        self.assertEqual(sessions.issued, [])
""",
    )


def seed_formatter(repo: Path) -> None:
    common_repo(repo, "Local title formatter")
    put(
        repo / "src/title_formatter.py",
        '''def format_title(value):
    return " ".join(part.capitalize() for part in value.split())
''',
    )
    put(
        repo / "docs/scope.md",
        """# Scope

This utility formats local strings. It has no service, authentication, or
operator-event boundary.
""",
    )
    put(
        repo / "test_fixture.py",
        """import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parent / "src"))
from title_formatter import format_title


class ExistingFormatterBehaviorTest(unittest.TestCase):
    def test_whitespace_is_normalized_by_current_formatter(self):
        self.assertEqual(format_title("  client API  "), "Client Api")
""",
    )


def receipt(stage: str) -> dict[str, object]:
    return {
        "summary": (
            "Synthetic traversal setup through " + stage + "; no Improve execution occurred."
        ),
        "review_refs": [],
        "check_refs": [],
        "lessons": "Synthetic setup only; revalidate real work.",
    }


def render_packet(
    package: Path,
    case: Path,
    repo: Path,
    goal: str,
    target: str,
    *,
    work_context: str = "",
    plan_ref: str = "",
) -> Path:
    if str(SOURCE / "scripts") not in sys.path:
        sys.path.insert(0, str(SOURCE / "scripts"))
    import shiploop_navigator as navigator  # noqa: PLC0415
    import shiploop_store as store  # noqa: PLC0415

    core = type("FrozenPacketSource", (), {"PACKAGE_ROOT": package})()
    state = navigator.new_state(str(repo), goal, protocol_version=3, improve_skill="")
    while navigator.current_stage(state) != target:
        stage = navigator.current_stage(state)
        action = navigator.current_action(state)["id"]
        result: dict[str, object] = {
            "outcome": "done",
            "summary": "Synthetic fixture traversal; no project work claimed.",
            "evidence_refs": [],
        }
        if stage == "plan":
            result.update(
                work_items=[
                    {
                        "id": "W1",
                        "title": "Current controlled service work",
                        "context": work_context,
                    }
                ],
                evidence_refs=[plan_ref] if plan_ref else [],
            )
        state = navigator.apply(state, action, result)
        if state["active_improve"] is not None:  # Only planning checkpoints and the last carry-forward park an Improve child.
            state = navigator.finish_improve(state, action, receipt(stage))
    run = case / "run"
    run.mkdir(parents=True)
    navigator.save(run, state)
    recovered = store.read_record(run / "state.md")
    packet = navigator.render(core, run, recovered)
    destination = case / "participant" / "PACKET.md"
    put(destination, packet)
    return destination


def launch(case: Path, repo: Path, packet: Path, task: str) -> None:
    put(
        case / "participant" / "LAUNCH.md",
        f"""# Fresh-context semantic exercise

Work only in {repo}. {task}

Read README.md, SHIPLOOP.md, relevant source/docs, and the actually rendered v3
packet at {packet}. Run the stated baseline as an observation before proposing
any product edit; its narrow fixture coverage is not remote-service evidence.
Write a concise REPORT.md in the fixture with findings, choices, unknowns,
affected file roles, and checks or revalidation needed. This is read/planning
only: do not edit product files, invoke a packet callback, alter run state, use
network or credentials, install dependencies, commit, push, deploy, or create
another ShipLoop run. The packet's prior transitions and Improve receipts are
synthetic setup, not completed work or an actual Improve campaign. Stop after
REPORT.md.

The coordinator must withhold other cases and evaluation material. This ordinary
filesystem fixture is not a security boundary; it has no remote account,
credential, or live endpoint.
""",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", required=True, type=Path,
        help="new directory outside this checkout",
    )
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise ValueError("--output must be a new directory outside the source checkout")
    out.mkdir(parents=True)
    package, source_hashes = freeze_source(out)
    outcomes = {
        "remote-discovery": [
            "separate runtime service account from metadata roles",
            "treat partial metadata as incomplete",
            "do not adopt the raw query-only cache without an authorization/invalidation contract",
            "preserve unrelated/computed remote fields and retain polling as a viable recovery path",
        ],
        "cold-step-plan": [
            "reopen the indexed current decision instead of the superseded cache note",
            "keep cache bypass pending current row/field authorization and invalidation evidence",
            "preserve fields and durable polling/status ownership",
            "reuse provider login logs and add only the missing app-owned audit event to app.audit",
        ],
        "local-auth": [
            "keep the work local",
            "reuse the structured logger and operator sink",
            "cover successful and failed password logins without turning ordinary failure into an incident",
            "avoid secrets in events",
        ],
        "local-formatter": [
            "keep service, cache, authentication, and observability additions out of scope",
        ],
    }
    builders = {
        "remote-discovery": seed_crm,
        "local-auth": seed_auth,
        "local-formatter": seed_formatter,
    }
    tasks = {
        "remote-discovery": (
            "Map the changes needed to add a pending-review Contact field and "
            "improve repeated Contact-list read latency."
        ),
        "cold-step-plan": (
            "Prepare the current work item's implementation step plan for the "
            "accepted CRM review decision."
        ),
        "local-auth": (
            "Map maintainable diagnostics and authentication logging for the "
            "local password-auth service."
        ),
        "local-formatter": (
            "Plan a title-formatting update that preserves all-uppercase acronym "
            "tokens such as API while retaining whitespace normalization."
        ),
    }
    records = {}
    for name in outcomes:
        case = out / "cases" / name
        repo = case / "workspace"
        repo.mkdir(parents=True)
        context = plan_ref = ""
        if name == "cold-step-plan":
            current, context = seed_cold_plan(repo)
            plan_ref = str(current) + "#accepted-contract"
        else:
            builders[name](repo)
        packet = render_packet(
            package,
            case,
            repo,
            tasks[name],
            "step-plan" if name == "cold-step-plan" else "discovery",
            work_context=context,
            plan_ref=plan_ref,
        )
        launch(case, repo, packet, tasks[name])
        records[name] = {
            "workspace": str(repo),
            "packet": str(packet),
            "launch": str(case / "participant" / "LAUNCH.md"),
            "input_hashes": hashes(repo),
            "packet_sha256": digest(packet),
        }
    put(
        out / "evaluation" / "expected-outcomes.json",
        json.dumps(outcomes, indent=2, sort_keys=True),
    )
    manifest = {
        "schema": "shiploop-service-discovery-fixtures-v1",
        "source_revision": git_value("rev-parse", "HEAD"),
        "source_dirty": bool(git_value("status", "--porcelain")),
        "source_hashes": source_hashes,
        "snapshot_hashes": hashes(package),
        "cases": records,
        "limits": (
            "Offline synthetic fixtures only; receipts set traversal state and "
            "did not execute Improve."
        ),
    }
    put(out / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
    print(
        json.dumps(
            {
                "output": str(out),
                "cases": records,
                "manifest": str(out / "manifest.json"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
