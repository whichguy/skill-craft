"""Hermetic operator CLI and callback fixtures for the registered hosted suite."""
import contextlib
import io
import json
import os
import subprocess
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import hosts
import lifecycle
from hosted_outcome import attempt, binding as b, cli, operator_lifecycle as op


def sid(value):
    return op.sfid(value)


CLASS = sid("01p000000000001")
FOREIGN_CLASS = sid("01p000000000002")
JOB = sid("707000000000001")
FOREIGN_JOB = sid("707000000000002")
DEPLOY = sid("0Af000000000001")
DESTRUCTIVE = sid("0Af000000000002")
PERMISSION = sid("0PS000000000001")
ASSIGNMENT = sid("0Pa000000000001")
OBJ = sid("01I000000000001")
ROW = sid("a01000000000001")
EXT_ID = sid("0pt000000000001")
STAMP = "2026-11-18T15:27:07.000Z"


def entry(name, mid):
    return {"fullName": name, "id": mid, "lastModifiedDate": STAMP, "ignored": "RAW_SECRET_FIXTURE"}


def ref(path):
    return {"path": str(path), "sha256": op.sha(path.read_bytes())}


class ExplainCall:
    returncode = 0
    pid = 1

    def __init__(self, argv, cwd, env, **kwargs):
        self.cli = self.__class__.cli
        self.cli.test.assertEqual(argv[0], self.cli.data["sf_bin"])
        self.cli.test.assertEqual(argv[-3:], ["--target-org", self.cli.data["target"]["username"], "--json"])
        self.cli.test.assertEqual(env["SF_DISABLE_LOG_FILE"], "true")
        self.cli.test.assertTrue(kwargs["start_new_session"])
        self.args, self.cwd = argv[1:-3], cwd

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def communicate(self, *, timeout):
        self.cli.test.assertGreater(timeout, 0)
        result = self.cli.run(self.args)
        return json.dumps({"status": 0, "result": result}).encode(), None


class FakeSalesforce:
    def __init__(self, test, data, external, cron):
        self.test, self.data, self.cron = test, data, cron
        target = data["target"]
        self.cli_org_id, self.cli_user_id = target["org_id"], target["user_id"]
        self.info_org_id, self.info_user_id = self.cli_org_id[:15], self.cli_user_id[:15]
        self.metadata = {kind: [] for kind in op.TYPES}
        self.metadata["ApexClass"] = [entry("ForeignClass", FOREIGN_CLASS)]
        self.metadata["ExternalCredential"] = [entry(external["reference"], external["id"])]
        self.jobs, self.deploys, self.assignments, self.custom = {}, {}, {}, {}
        self.mutations, self.calls = [], []
        self.complete, self.fail_deletion, self.lose_destructive_response = True, False, False

    def add_job(self, job_id, class_id, name, parent=None, status="Queued"):
        self.jobs[job_id] = {"Id": job_id, "ApexClassId": class_id, "ApexClass": {"Name": name},
                             "Status": status, "ParentJobId": parent}

    def query(self, query):
        select, source = query.split(" FROM ", 1)
        fields = select[len("SELECT "):].split(",")
        object_name = source.split(" ", 1)[0]
        if object_name == "Organization":
            rows = [{"Id": self.cli_org_id, "OrganizationType": "Developer Edition", "IsSandbox": False}]
        elif object_name == "NamedCredential":
            rows = [{"Id": self.data["named_id"], "DeveloperName": self.data["provider"]["reference"]}]
            self.test.assertIn(f"DeveloperName='{self.data['provider']['reference']}'", source)
        elif object_name == "DeployRequest":
            rows = [{"Id": rid, "Status": d["status"]} for rid, d in self.deploys.items()]
        elif object_name == "AsyncApexJob":
            rows = list(self.jobs.values())
        elif object_name == "CronTrigger":
            rows = [dict(row, CronJobDetail={"Name": "Unrelated"}) for row in self.cron]
        elif object_name == "PermissionSetAssignment":
            rows = list(self.assignments.values())
        elif object_name == "EntityDefinition":
            rows = []
        elif object_name in self.custom:
            rows = [{"Id": value} for value in self.custom[object_name]]
        else:
            self.test.fail(f"unexpected object: {object_name}")
        filters = source.split(" WHERE ", 1)
        if len(filters) == 2 and object_name not in {"NamedCredential", "CronTrigger", "EntityDefinition"}:
            field, predicate = filters[1].split(" ", 1) if " " in filters[1] else filters[1].split("=")
            values = [item.strip("'") for item in predicate.split("(", 1)[-1].strip(")").split(",")]
            if predicate.startswith("NOT IN"):
                rows = [r for r in rows if r[field] not in values]
            else:
                rows = [r for r in rows if r[field] in values]
        allowed = {field.split(".")[0] for field in fields}
        return {"done": self.complete, "totalSize": len(rows),
                "records": [{k: v for k, v in row.items() if k in allowed} for row in rows]}

    def run(self, args):
        self.calls.append(args)
        if args[:3] == ["api", "request", "rest"]:
            self.test.assertEqual(args[3:], ["/services/oauth2/userinfo", "--method", "GET"])
            body = {"organization_id": self.info_org_id, "user_id": self.info_user_id,
                    "preferred_username": self.data["target"]["username"], "ignored": "RAW_SECRET_FIXTURE"}
            return {"statusCode": 200, "body": json.dumps(body), "headers": {"ignored": "RAW_SECRET_FIXTURE"}}
        if args[:2] == ["data", "query"]:
            query = args[args.index("--query") + 1]
            if query.split(" FROM ")[1] in self.custom:
                self.test.assertIn("--all-rows", args)
            return self.query(query)
        if args[:3] == ["org", "list", "metadata"]:
            return self.metadata[args[args.index("--metadata-type") + 1]]
        if args[:3] == ["project", "deploy", "report"]:
            return self.deploys[args[args.index("--job-id") + 1]]
        if args[:3] == ["project", "deploy", "start"]:
            path = Path(args[args.index("--post-destructive-changes") + 1])
            manifest = ET.parse(path)
            prefix = "{http://soap.sforce.com/2006/04/metadata}"
            names = {group.findtext(prefix + "name"): {x.text for x in group.findall(prefix + "members")}
                     for group in manifest.findall(prefix + "types")}
            self.mutations.append(("destructive", names))
            status = "Failed" if self.fail_deletion else "Succeeded"
            if status == "Succeeded":
                for kind, members in names.items():
                    self.metadata[kind] = [r for r in self.metadata[kind] if r["fullName"] not in members]
            self.deploys[DESTRUCTIVE] = {"id": DESTRUCTIVE, "status": status, "done": True,
                                         "success": status == "Succeeded"}
            if self.lose_destructive_response:
                raise TimeoutError("simulated interruption after submission")
            return {"id": DESTRUCTIVE, "status": "Pending"}
        if args[:2] == ["apex", "run"]:
            import re

            script = Path(args[args.index("--file") + 1]).read_text()
            ids = [re.fullmatch(r"System\.abortJob\('([A-Za-z0-9]{18})'\);", line)[1]
                   for line in script.splitlines()]
            self.mutations.append(("abort", ids))
            for job_id in ids:
                self.jobs[job_id]["Status"] = "Aborted"
            return {"compiled": True, "success": True, "logs": "RAW_SECRET_FIXTURE"}
        if args[:3] == ["data", "delete", "record"]:
            rid = args[args.index("--record-id") + 1]
            self.test.assertEqual(args[args.index("--sobject") + 1], "PermissionSetAssignment")
            self.mutations.append(("delete-assignment", rid))
            del self.assignments[rid]
            return {"id": rid, "success": True}
        self.test.fail(f"unexpected CLI args: {args}")


class Layout:
    def __init__(self, test, root, identity, *, interrupt=False):
        self.test, self.root, self.interrupt = test, root, interrupt
        root.mkdir()
        self.output = root / "output"
        self.config_path = root / "config.json"
        sf, codex = root / "sf", root / "codex"
        for tool in (sf, codex):
            tool.write_text("#!/bin/sh\nexit 97\n")
            tool.chmod(0o700)
        self.provider = f"Provider{identity}"
        self.named_id = sid(f"0XA{identity:012d}")
        self.namespace = f"App{identity}Try"
        self.external = {"reference": f"ExternalProvider{identity}", "id": sid(f"0pt{identity:012d}")}
        self.cron = [{"Id": sid(f"08e{identity * 10 + job:012d}")} for job in range(identity - 1)]
        self.target = {"org_id": sid(f"00D{identity:012d}"), "user_id": sid(f"005{identity:012d}"),
                       "selector": f"alias{identity}", "username": f"operator{identity}@example.test"}
        scenario = b.HERE / "scenarios" / b.CASE
        self.prompt = (scenario / "BUILDER_PROMPT.md").read_bytes()
        self.binding = {
            "case": b.CASE, "run_kind": "create", "product_cwd": str(self.output / "work"),
            "target": self.target, "namespace": self.namespace, "legacy_prefixes": [f"Retired{identity}"],
            "provider": {"reference": self.provider, "endpoint": "https://api.x.ai", "model": "grok-offline"},
            "synthetic_label": f"Fixture {identity}", "sf_bin": str(sf), "tool_dirs": [str(root)],
            "prompt_sha256": b.sha(self.prompt), "source_readiness_sha256": b.sha((scenario / "READINESS.json").read_bytes()),
        }
        self.now = time.time()
        digest = b.sha(b.encoded(self.binding))
        self.binding["receipts"] = {
            kind: self.evidence(f"{kind}-receipt.json", {"kind": kind, "identity_sha256": digest,
                                                        "status": "VERIFIED", "checked_at": self.now})
            for kind in ("authority", "retirement", "observer")
        }
        pages = []
        for idx, url in enumerate(sorted(op.REFERENCE_URLS)):
            archive = self.evidence(f"page-{idx}.json", {"offline_reference": url})
            pages.append(dict(archive, url=url, http_status=200, bytes=Path(archive["path"]).stat().st_size))
        self.catalog = {"fetched_at": datetime.fromtimestamp(self.now, timezone.utc).isoformat(), "models": [
            {"slug": "gpt-6.9-sol", "visibility": "list", "supported_reasoning_levels": [{"effort": "medium"}]},
            {"slug": "gpt-6.10-sol", "visibility": "list", "supported_reasoning_levels": [{"effort": "medium"}]},
            {"slug": "gpt-9.0-sol", "visibility": "hide", "supported_reasoning_levels": [{"effort": "medium"}]},
        ]}
        self.config = {
            "schema": "hosted-outcome-operator/1", "binding": self.evidence("binding.json", self.binding),
            "retirement_plan": self.evidence("retirement-plan.json", {
                "org_id": self.target["org_id"], "initiating_user_id": self.target["user_id"],
                "members": {"ApexClass": [{"name": f"LegacyExact{identity}", "id": sid("01p000000000003")}]},
                "assignment_ids": [],
            }),
            "retirement_verification": self.evidence("retirement-verification.json", {
                "verified": True, "org": {"Id": self.target["org_id"], "OrganizationType": "Developer Edition",
                                          "IsSandbox": False}, "remaining_owned_entities": [], "remaining_app_assignments": [],
                "active_async": [], "active_deploy": [], "scheduled": self.cron,
                "provider": [{"Id": self.named_id, "DeveloperName": self.provider}],
            }),
            "reference_snapshot": self.evidence("references.json", {"pages": pages}),
            "named_credential_id": self.named_id, "external_credential": self.external,
            "sf_bin_sha256": ref(sf)["sha256"], "codex_bin": ref(codex),
            "model_catalog": self.evidence("catalog.json", self.catalog),
            "campaign": str(root), "build": "a" * 40, "baseline": str(root / "baselines.jsonl"),
            "deadline": self.now + 90, "observation_seconds": 20, "teardown_seconds": 20,
        }
        op.write(self.config_path, self.config)
        self.authorized = ref(self.config_path)["sha256"]
        self.sf = FakeSalesforce(test, {**self.binding, "named_id": self.named_id}, self.external, self.cron)
        self.class_name = self.namespace + "Queue"
        self.object = self.namespace + "Records__c"
        self.permission = self.namespace + "Access"
        self.launches, self.events = [], []
        self.state = None
        self.key = None

    def evidence(self, name, value):
        path = self.root / name
        op.write(path, value)
        return ref(path)

    def command(self, command, *extra, authorized=True, after_build=False):
        argv = [command, "--config", str(self.config_path), *extra]
        if authorized:
            argv += ["--expected-sha256", self.authorized]
        ExplainCall.cli = self.sf
        fake_cli = SimpleNamespace(Popen=ExplainCall, DEVNULL=subprocess.DEVNULL,
                                   PIPE=subprocess.PIPE, TimeoutExpired=subprocess.TimeoutExpired)
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.ExitStack() as stack:
            for patcher in (patch.object(op, "subprocess", fake_cli), patch.object(attempt, "builder", self.builder),
                            patch.object(op.Phase, "pause", lambda phase: self.publish(phase)),
                            contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors)):
                stack.enter_context(patcher)
            if after_build:
                stack.enter_context(patch.object(cli, "time", SimpleNamespace(time=lambda: self.config["deadline"] - 1)))
            code = cli.main(argv)
        raw = output.getvalue()
        return code, json.loads(raw) if raw else {}, errors.getvalue()

    def builder(self, argv, env, log, cutoff, state):
        self.test.assertEqual(state, self.state)
        self.test.assertTrue(op.read(state / "reset.json")["empty_noop"])
        self.test.assertEqual((state / "operator-model-catalog.json").read_bytes(),
                              Path(self.config["model_catalog"]["path"]).read_bytes())
        self.events.append("build")
        work = self.output / "work"
        work.mkdir(parents=True)
        model = argv[argv.index("--model") + 1]
        opening = b.opening(self.prompt.decode(), self.binding)
        cmd = hosts.CodexHost(self.config["codex_bin"]["path"]).argv(
            prompt=opening, prompt_file=self.output / "opening.txt", cwd=work,
            model=model, effort=argv[argv.index("--effort") + 1], permission_mode=None, max_turns=None)
        self.launches.append(cmd)
        self.test.assertEqual(model, "gpt-6.10-sol")
        self.test.assertIn("model_reasoning_effort=medium", cmd)
        self.test.assertIn("agents.default_subagent_reasoning_effort=medium", cmd)
        self.test.assertIn('agents.default_subagent_model="gpt-6.10-sol"', cmd)
        self.test.assertTrue(cmd[-1].encode().startswith(self.prompt))
        self.test.assertEqual(cmd[-1].count("$skill-craft:shiploop"), 1)
        self.test.assertIn(self.provider, cmd[-1])
        self.test.assertNotIn(self.external["reference"], cmd[-1])
        self.test.assertNotIn(str(self.config_path), cmd[-1])
        log.write(b"offline builder\n")
        self.deploy(state, work)
        if self.interrupt:
            raise KeyboardInterrupt
        return 0

    def bound(self, phase, **details):
        return dict(binding_sha256=self.config["binding"]["sha256"], target=self.target,
                    phase=phase, verified=True, **details)

    def deploy(self, state, work):
        intent = {"root": str(work), "binding_sha256": self.config["binding"]["sha256"],
                  "target": self.target, "force_app_sha256": "a" * 64, "project_sha256": "b" * 64}
        self.key = key = b.sha(b.encoded(intent))
        op.write(state / f"{key}.intent", intent)
        members = {"ApexClass": (self.class_name, CLASS), "PermissionSet": (self.permission, PERMISSION),
                   "CustomObject": (self.object, OBJ)}
        approval = state / f"{key}.approved"
        evidence = self.evidence("review.json", {"review": "offline source and grants"})
        op.write(approval, {"intent_sha256": key, "approved": True,
                            **{name: intent[name] for name in ("binding_sha256", "force_app_sha256", "project_sha256")},
                            "review_evidence": evidence,
                            "members": {kind: [name] for kind, (name, _) in members.items()}})
        op.write(state / f"{key}.submitted",
                 {"intent_sha256": key, "approval_sha256": ref(approval)["sha256"],
                  "forward_target": {"requested": self.target["selector"], "effective": self.target["username"]}})
        components = []
        for kind, (name, mid) in members.items():
            self.sf.metadata[kind].append(entry(name, mid))
            components.append({"componentType": kind, "fullName": name, "id": mid, "success": True, "created": True})
        self.sf.deploys[DEPLOY] = {"id": DEPLOY, "status": "Succeeded", "done": True, "success": True,
                                  "details": {"componentSuccesses": components}}
        self.sf.custom[self.object] = [ROW]
        self.sf.assignments[ASSIGNMENT] = {"Id": ASSIGNMENT, "AssigneeId": self.target["user_id"],
                                           "PermissionSetId": PERMISSION}
        op.write(state / "app-access.json", self.bound("app-access", assignment_ids=[ASSIGNMENT]))
        self.sf.add_job(JOB, CLASS, self.class_name)
        self.sf.add_job(FOREIGN_JOB, FOREIGN_CLASS, "ForeignClass")
        if not self.interrupt:
            op.write(state / f"{key}.returned", {"remote_id": DEPLOY})

    def publish(self, phase):
        if phase.phase == "observe" and not self.interrupt:
            self.test.assertTrue((phase.state / "observe-request.json").is_file())
            self.test.assertFalse(self.sf.mutations)
            self.events.append("observe")
            links = [{"intent_sha256": self.key, "source_sha256": "a" * 64, "deployment_id": DEPLOY}]
            routes = {kind: dict(self.evidence(f"{kind}-evidence.json", {"observed": kind}), status="OBSERVED")
                      for kind in ("browser", "provider", "native", "records")}
            op.write(phase.state / "observations.json", self.bound("observe", checked_at=time.time(),
                     status="OBSERVED", deployments=links, routes=routes))
        elif phase.phase == "observe":
            raise op.Refusal("FIXTURE_OBSERVER_INTERRUPTED")
        elif (phase.state / "cleanup-records.json").exists() and not (phase.state / "cleanup-synthetic.json").exists():
            request = op.read(phase.state / "cleanup-records.json")
            self.test.assertEqual(request["objects"], {self.object: {"count": 1, "ids": [ROW]}})
            evidence = self.evidence("synthetic.json", {"scope": self.binding["synthetic_label"], "rows": [ROW]})
            op.write(phase.state / "cleanup-synthetic.json",
                     self.bound("synthetic-records", objects=request["objects"], evidence=evidence))


class OperatorFixtures(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.root = Path(work.name).resolve()
        self.enterContext(patch.dict(os.environ, {lifecycle.LEASES_ENV: str(self.root / "leases")}))

    def layout(self, identity, **kwargs):
        fixture = Layout(self, self.root / f"layout-{identity}", identity, **kwargs)
        code, data, err = fixture.command("preflight", authorized=False)
        self.assertEqual(code, 0, (data, err))
        self.assertEqual(data["config_sha256"], fixture.authorized)
        self.assertFalse(fixture.sf.calls)
        fixture.state = Path(data["state_dir"])
        self.assertFalse(fixture.state.exists())
        return fixture

    def verify_cleanup(self, fixture, result):
        self.assertEqual(result["state"], "SETTLED", result)
        self.assertEqual(result["product_acceptance"], "UNKNOWN")
        self.assertEqual(result["cleanup"]["reconciled_intents"], [fixture.key])
        self.assertTrue(attempt.reusable(fixture.state))
        self.assertEqual(len(list(fixture.state.glob("operator-reset-*"))), 1)
        self.assertEqual(len(fixture.launches), 1)
        self.assertEqual(fixture.sf.mutations, [
            ("delete-assignment", ASSIGNMENT), ("abort", [JOB]),
            ("destructive", {"ApexClass": {fixture.class_name}, "PermissionSet": {fixture.permission},
                             "CustomObject": {fixture.object}}),
        ])
        self.assertEqual([row["fullName"] for row in fixture.sf.metadata["ApexClass"]], ["ForeignClass"])
        self.assertEqual(fixture.sf.jobs[FOREIGN_JOB]["Status"], "Queued")

    def test_two_fresh_layouts_with_distinct_targets_and_preserved_sets_then_replay(self):
        for identity in (1, 3):
            with self.subTest(identity=identity):
                fixture = self.layout(identity)
                code, result, err = fixture.command("run")
                self.assertEqual(code, 0, (result, err))
                self.verify_cleanup(fixture, result)
                self.assertEqual(result["observations"]["status"], "OBSERVED")
                self.assertEqual(fixture.events, ["build", "observe"])
                frozen = op.read(fixture.state / "operator-baseline.json")["preserved"]
                self.assertEqual(frozen["cron"], sorted(row["Id"] for row in fixture.cron))
                self.assertEqual(frozen["external"]["id"], fixture.external["id"])
                before = len(fixture.sf.calls)
                self.assertEqual(fixture.command("run"), (0, result, ""))
                self.assertEqual(len(fixture.sf.calls), before)
                self.assertEqual(len(fixture.launches), 1)

    def test_verified_cleanup_allows_a_fresh_binding_on_same_target(self):
        fixture = self.layout(1)
        code, result, err = fixture.command("run")
        self.assertEqual(code, 0, (result, err))
        self.verify_cleanup(fixture, result)
        later = Layout(self, self.root / "later-attempt", 1)
        code, prepared, err = later.command("preflight")
        self.assertEqual(code, 0, (prepared, err))
        later.state = Path(prepared["state_dir"])
        self.assertEqual(later.state.parent, fixture.state.parent)
        self.assertNotEqual(later.state, fixture.state)
        code, result, err = later.command("run")
        self.assertEqual(code, 0, (result, err))
        self.verify_cleanup(later, result)
        self.assertTrue(attempt.reusable(fixture.state))

    def interrupted_submission_with_independent_id(self):
        fixture = self.layout(2, interrupt=True)
        code, result, err = fixture.command("run")
        self.assertEqual(code, 1, (result, err))
        self.assertEqual(result["build_error"], "KeyboardInterrupt")
        self.assertEqual(result["state"], "RECONCILIATION_REQUIRED")
        self.assertFalse(fixture.sf.mutations)
        self.assertFalse((fixture.state / f"{fixture.key}.returned").exists())
        start = attempt.read(fixture.state / "start.json")
        self.assertGreater(start["build_until"], time.time())
        self.assertEqual(attempt.read(fixture.state / "build-closed.json"), attempt.phase_receipt(fixture.state))
        evidence = fixture.evidence("deploy-id.json", {"id": DEPLOY})
        op.write(fixture.state / f"{fixture.key}.reconciled", fixture.bound(
            "reconciliation", intent_sha256=fixture.key, disposition="REMOTE_ID", remote_id=DEPLOY, evidence=evidence))
        return fixture

    def test_interrupted_submission_requires_post_cutoff_cleanup_only_reconciliation(self):
        fixture = self.interrupted_submission_with_independent_id()
        # Simulate a crash that left the attempt without its closure receipt.
        (fixture.state / "build-closed.json").unlink()
        options = ("--state", str(fixture.state))
        self.assertIn("BUILD_CUTOFF_NOT_REACHED", fixture.command("reconcile", *options)[2])
        code, recovered, err = fixture.command("reconcile", *options, after_build=True)
        self.assertEqual(code, 0, (recovered, err))
        self.verify_cleanup(fixture, recovered)
        self.assertEqual(fixture.events, ["build"])

    def test_interrupted_closed_build_allows_early_cleanup_only_reconciliation(self):
        fixture = self.interrupted_submission_with_independent_id()
        state = fixture.state
        original = {name: (state / name).read_bytes() for name in
                    ("start.json", "build-closed.json", "settled.json")}
        submissions = attempt.submission_evidence(state)
        self.assertEqual(set(submissions), {f"{fixture.key}.submitted"})
        code, recovered, err = fixture.command("reconcile", "--state", str(state))
        self.assertEqual(code, 0, (recovered, err))
        self.assertGreater(attempt.read(state / "start.json")["build_until"], time.time())
        self.verify_cleanup(fixture, recovered)
        self.assertEqual(fixture.events, ["build"])
        self.assertEqual(attempt.submission_evidence(state), submissions)
        self.assertEqual({name: (state / name).read_bytes() for name in original}, original)

    def test_invalid_build_closure_cannot_authorize_early_reconciliation(self):
        fixture = self.interrupted_submission_with_independent_id()
        state = fixture.state
        closure = state / "build-closed.json"
        receipt = attempt.phase_receipt(state)
        closure.unlink()
        calls_before = list(fixture.sf.calls)
        for raw in (b"{", b.encoded({**receipt, "phase": "observe"}),
                    b.encoded({**receipt, "start_sha256": "0" * 64})):
            with self.subTest(closure=raw), patch.object(attempt, "reconcile", wraps=attempt.reconcile) as recover:
                closure.write_bytes(raw)
                self.assertGreater(attempt.read(state / "start.json")["build_until"], time.time())
                code, recovered, err = fixture.command("reconcile", "--state", str(state))
                self.assertEqual(code, 1, (recovered, err))
                recover.assert_not_called()
        self.assertEqual(fixture.sf.calls, calls_before)
        self.assertFalse(fixture.sf.mutations)
        self.assertEqual(fixture.events, ["build"])
        self.assertFalse((state / "reconciled.json").exists())

    def test_mutated_pinned_input_and_wrong_config_digest_have_zero_effects(self):
        fixture = self.layout(1)
        files = [Path(fixture.config[field]["path"]) for field in
                 ("binding", "retirement_plan", "retirement_verification", "model_catalog",
                  "reference_snapshot", "codex_bin")]
        files.extend(fixture.root / name for name in ("sf", "authority-receipt.json", "page-0.json"))
        for path in files:
            with self.subTest(file=path.name):
                original = path.read_bytes()
                path.write_bytes(original + b" ")
                self.assertEqual(fixture.command("run")[0], 1)
                path.write_bytes(original)
        fixture.config_path.write_bytes(fixture.config_path.read_bytes() + b" ")
        self.assertIn("CONFIG_DIGEST_MISMATCH", fixture.command("run")[2])
        self.assertFalse(fixture.sf.calls)
        self.assertFalse(fixture.launches)
        self.assertFalse(fixture.state.exists())

    def test_changed_preserved_set_of_same_size_refuses_reset_and_builder(self):
        fixture = self.layout(2)
        fixture.sf.cron = [{"Id": sid("08e000000000099")}]
        code, result, err = fixture.command("run")
        self.assertEqual(code, 1, (result, err))
        receipt, = fixture.state.glob("operator-reset-*/receipt.json")
        self.assertEqual(op.read(receipt)["reason"], "CRON_INVENTORY_AMBIGUOUS")
        self.assertFalse(fixture.launches)
        self.assertFalse(fixture.sf.mutations)

    def test_missing_stale_or_unavailable_catalog_route_refuses_before_effects(self):
        for identity, reason in enumerate(("SOL_MEDIUM_ROUTE_UNAVAILABLE", "MODEL_CATALOG_STALE",
                                           "SOL_ROUTE_UNAVAILABLE"), start=1):
            with self.subTest(reason=reason):
                fixture = self.layout(identity)
                if identity == 1:
                    fixture.catalog["models"][1]["supported_reasoning_levels"] = [{"effort": "high"}]
                elif identity == 2:
                    stamp = datetime.fromtimestamp(fixture.now - 28801, timezone.utc)
                    fixture.catalog["fetched_at"] = stamp.isoformat()
                else:
                    fixture.catalog["models"] = []
                (fixture.root / "catalog.json").unlink()
                fixture.config["model_catalog"] = fixture.evidence("catalog.json", fixture.catalog)
                fixture.config_path.unlink()
                op.write(fixture.config_path, fixture.config)
                fixture.authorized = ref(fixture.config_path)["sha256"]
                self.assertIn(reason, fixture.command("run")[2])
                self.assertFalse(fixture.sf.calls)
                self.assertFalse(fixture.launches)


if __name__ == "__main__":
    unittest.main()
