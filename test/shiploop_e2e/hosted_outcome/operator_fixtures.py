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
from checks import sf_guard
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
        self.metadata["NamedCredential"] = [entry(data["provider"]["reference"], data["named_id"])]
        self.metadata["ExternalCredential"] = [entry(external["reference"], external["id"])]
        self.jobs, self.deploys, self.assignments, self.custom = {}, {}, {}, {}
        self.fields, self.record_stamps = [], {}
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
            rows = [{"CronJobDetail": {"Name": "Unrelated"}, "CronJobDetailId": sid(f"08a{index:012d}"),
                     "CronExpression": "0 0 7 * * ?", "TimeZoneSidKey": "America/Los_Angeles", **row}
                    for index, row in enumerate(self.cron)]
        elif object_name == "PermissionSetAssignment":
            rows = list(self.assignments.values())
        elif object_name == "EntityDefinition":
            rows = []
        elif object_name == "CustomField":
            rows = self.fields
        elif object_name in self.custom:
            rows = [{"Id": value, "SystemModstamp": self.record_stamps.get(value, STAMP)}
                    for value in self.custom[object_name]]
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
                removed_objects = {r["id"] for r in self.metadata["CustomObject"]
                                   if r["fullName"] in names.get("CustomObject", set())}
                self.fields = [row for row in self.fields if row["TableEnumOrId"] not in removed_objects]
                for kind, members in names.items():
                    self.metadata[kind] = [r for r in self.metadata[kind] if r["fullName"] not in members]
            rid = DESTRUCTIVE
            if rid in self.deploys:
                rid = sid(f"0Af{len(self.deploys) + 100:012d}")
            self.deploys[rid] = {"id": rid, "status": status, "done": True, "success": status == "Succeeded"}
            if self.lose_destructive_response:
                raise TimeoutError("simulated interruption after submission")
            return {"id": rid, "status": "Pending"}
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
    def __init__(self, test, root, identity, *, interrupt=False, review_hold=None,
                 namespace=None, legacy_prefixes=None, synthetic_label=None, generation=1):
        self.test, self.root, self.interrupt = test, root, interrupt
        self.builder_error, self.observer_lost, self.clear_work = None, False, True
        self.generation = generation
        root.mkdir()
        self.output = root / "output"
        self.config_path = root / "config.json"
        sf, codex = root / "sf", root / "codex"
        for tool in (sf, codex):
            tool.write_text("#!/bin/sh\nexit 97\n")
            tool.chmod(0o700)
        self.provider = f"Provider{identity}"
        self.named_id = sid(f"0XA{identity:012d}")
        self.namespace = namespace or f"App{identity}Try"
        self.external = {"reference": f"ExternalProvider{identity}", "id": sid(f"0pt{identity:012d}")}
        self.cron = [{"Id": sid(f"08e{identity * 10 + job:012d}")} for job in range(identity - 1)]
        self.target = {"org_id": sid(f"00D{identity:012d}"), "user_id": sid(f"005{identity:012d}"),
                       "selector": f"alias{identity}", "username": f"operator{identity}@example.test"}
        scenario = b.HERE / "scenarios" / b.CASE
        self.prompt = (scenario / "BUILDER_PROMPT.md").read_bytes()
        self.binding = {
            "case": b.CASE, "run_kind": "create", "product_cwd": str(self.output / "work"),
            "target": self.target, "namespace": self.namespace,
            "legacy_prefixes": [f"Retired{identity}"] if legacy_prefixes is None else legacy_prefixes,
            "provider": {"reference": self.provider, "endpoint": "https://api.x.ai", "model": "grok-offline"},
            "synthetic_label": synthetic_label or f"Fixture {identity}", "sf_bin": str(sf), "tool_dirs": [str(root)],
            "prompt_sha256": b.sha(self.prompt), "source_readiness_sha256": b.sha((scenario / "READINESS.json").read_bytes()),
        }
        if review_hold is not None:
            self.binding["review_hold"] = review_hold
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
            for patcher in (patch.dict(self.sf.data, {"sf_bin": self.binding["sf_bin"]}),
                            patch.object(op, "subprocess", fake_cli), patch.object(attempt, "builder", self.builder),
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
        if self.binding.get("review_hold"):
            self.test.assertIs(attempt.read(state / "start.json")["review_hold"], True)
            self.deploy_exact(state, work)
        else:
            self.deploy(state, work)
        if self.builder_error:
            raise self.builder_error
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

    def deploy_exact(self, state, work):
        serial = self.generation
        self.class_id, self.permission_id, self.object_id, self.field_id, self.deploy_id, self.assignment_id, self.job_id = (
            sid(f"{prefix}{serial:012d}") for prefix in ("01p", "0PS", "01I", "00N", "0Af", "0Pa", "707"))
        files = {
            f"classes/{self.class_name}.cls": "public class AppQueue {}",
            f"classes/{self.class_name}.cls-meta.xml": "<ApexClass/>",
            f"permissionsets/{self.permission}.permissionset-meta.xml": "<PermissionSet/>",
            f"objects/{self.object}/{self.object}.object-meta.xml": "<CustomObject/>",
            f"objects/{self.object}/fields/State__c.field-meta.xml": "<CustomField><fullName>State__c</fullName></CustomField>",
        }
        for name, contents in files.items():
            path = work / "force-app/main/default" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents)
        op.write(work / "sfdx-project.json", {"packageDirectories": [{"path": "force-app", "default": True}]})
        record = op.read(state / "start.json")
        org = self.target["selector"]
        argv = ["project", "deploy", "start", "--source-dir", "force-app", "--target-org", org, "--json"]
        members = {"ApexClass": (self.class_name, self.class_id), "PermissionSet": (self.permission, self.permission_id),
                   "CustomObject": (self.object, self.object_id), "CustomField": (f"{self.object}.State__c", self.field_id)}
        with (patch.object(sf_guard.Path, "cwd", return_value=work),
              patch.object(sf_guard, "deploy_source_root", return_value=work),
              patch.object(attempt, "assert_open", return_value=record)):
            with self.test.assertRaisesRegex(ValueError, "awaiting operator inspection"):
                sf_guard.hosted_forward(state, argv, org, record)
            intent_path, = state.glob("*.intent")
            self.key = intent_path.stem
            intent = op.read(intent_path)
            evidence = self.evidence("review.json", {"review": "offline source and grants"})
            op.write(intent_path.with_suffix(".approved"), {
                "intent_sha256": self.key, "approved": True, "binding_sha256": record["binding_sha256"],
                **{name: intent[name] for name in ("force_app_sha256", "project_sha256")}, "review_evidence": evidence,
                "members": {kind: [name] for kind, (name, _) in members.items()},
            })
            submitted, self.payload_path = sf_guard.hosted_forward(state, argv, org, record)
        def stamp():
            return datetime.now(timezone.utc).isoformat(timespec="milliseconds")

        created = stamp()
        components = []
        for kind, (name, mid) in members.items():
            if kind != "CustomField":
                self.sf.metadata[kind].append(dict(entry(name, mid), lastModifiedDate=stamp()))
            components.append({"componentType": kind, "fullName": name, "id": mid, "success": True, "created": True})
        self.sf.fields.append({"Id": self.field_id, "TableEnumOrId": self.object_id,
                               "DeveloperName": "State", "NamespacePrefix": None, "LastModifiedDate": stamp()})
        report = {"id": self.deploy_id, "status": "Succeeded", "done": True, "success": True,
                  "createdDate": created, "completedDate": stamp(), "details": {"componentSuccesses": components}}
        self.sf.deploys[self.deploy_id] = report
        self.row_id = sid(f"a01{serial:012d}")
        self.sf.custom[self.object] = [self.row_id]
        self.sf.assignments[self.assignment_id] = {"Id": self.assignment_id, "AssigneeId": self.target["user_id"],
                                                   "PermissionSetId": self.permission_id}
        op.write(state / "app-access.json", self.bound("app-access", assignment_ids=[self.assignment_id]))
        self.sf.add_job(self.job_id, self.class_id, self.class_name)
        if not self.interrupt:
            sf_guard.hosted_deploy_result(submitted, json.dumps({"result": report}), 0, False)

    def publish(self, phase):
        request_path = phase.journal / "app-work-request.json"
        if request_path.is_file():
            if not self.clear_work:
                raise op.Refusal("FIXTURE_APP_WORK_UNPROVEN")
            request = op.read(request_path)
            evidence = self.evidence(f"app-work-{phase.journal.name}.json", {"cleared": request["generation_id"]})
            op.write(phase.journal / "app-work-cleared.json", dict(
                phase.bound("app-work"), verified=True, pending=False, checked_at=time.time(), evidence=evidence,
                generation_id=request["generation_id"], request_sha256=ref(request_path)["sha256"],
                app_url=f"https://example.lightning.force.com/lightning/n/{request['prefix']}"))
        elif phase.phase == "observe" and not (self.interrupt or self.observer_lost):
            self.test.assertTrue((phase.state / "observe-request.json").is_file())
            if not self.binding.get("review_hold"):
                self.test.assertFalse(self.sf.mutations)
            self.events.append("observe")
            intent = op.read(phase.state / f"{self.key}.intent")
            links = [{"intent_sha256": self.key, "source_sha256": intent["force_app_sha256"],
                      "deployment_id": getattr(self, "deploy_id", DEPLOY)}]
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


class FixtureCase(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.root = Path(work.name).resolve()
        self.enterContext(patch.dict(os.environ, {lifecycle.LEASES_ENV: str(self.root / "leases")}))


class OperatorFixtures(FixtureCase):
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


class RetentionFixtures(FixtureCase):
    def layout(self, identity, *, peer=None, review_hold=True, **kwargs):
        root = Path(tempfile.mkdtemp(dir=self.root)) / "generation"
        options = {} if peer is None else {"namespace": "FreshApp", "synthetic_label": "Fresh records",
                                           "generation": 10}
        fixture = Layout(self, root, identity, review_hold=review_hold, **(options | kwargs))
        if peer is not None:
            fixture.sf = peer.sf
        code, prepared, err = fixture.command("preflight")
        self.assertEqual(code, 0, (prepared, err))
        fixture.state = Path(prepared["state_dir"])
        return fixture

    def settle(self, fixture):
        code, result, err = fixture.command("run")
        self.assertEqual(code, 0, (result, err))
        self.assertEqual(result["state"], "RETAINED_QUIESCENT")
        self.assertTrue(attempt.retained(fixture.state, result))
        self.assertFalse(attempt.reusable(fixture.state))
        self.assertIn(fixture.assignment_id, fixture.sf.assignments)
        return result

    def plan(self, fixture):
        code, result, err = fixture.command("plan-retirement", "--state", str(fixture.state))
        self.assertEqual(code, 0, (result, err))
        self.assertEqual(result["state"], "RETIREMENT_PLANNED")
        self.assertEqual(result["plan"]["generation_id"], fixture.state.name)
        return result

    def approve(self, fixture, plan, *, name="approval.json", **overwrite):
        review = fixture.evidence(name + ".review", {"reviewed": plan["plan_sha256"]})
        data = {"schema": "hosted-outcome-retirement-approval/1", "approved": True,
                "generation_id": fixture.state.name, "plan_sha256": plan["plan_sha256"], "evidence": review}
        approval = fixture.evidence(name, data | overwrite)
        return ["--state", str(fixture.state), "--approval", approval["path"], "--approval-sha256", approval["sha256"]]

    def test_retention_binding_requires_json_boolean_and_matching_identity_receipts(self):
        invalid = Layout(self, self.root / "invalid", 1, review_hold=1)
        self.assertEqual(invalid.command("run")[0], 1)
        self.assertFalse(invalid.sf.calls)
        self.assertFalse(invalid.launches)
        fixture = self.layout(1)
        self.assertTrue(b.load(fixture.config["binding"]["path"])[0]["review_hold"])
        changed = fixture.evidence("changed-binding.json", fixture.binding | {"review_hold": False})
        with self.assertRaisesRegex(ValueError, "receipt does not verify this binding"):
            b.load(changed["path"])

    def test_retention_hold_survives_success_failure_timeout_observer_loss_and_replay(self):
        self.enterContext(patch.object(op.Operator, "cleanup", side_effect=AssertionError("cleanup called on held state")))
        for identity, error in enumerate((None, RuntimeError(), subprocess.TimeoutExpired("offline", 0),
                                          KeyboardInterrupt(), None), start=1):
            with self.subTest(identity=identity):
                fixture = self.layout(identity)
                fixture.builder_error = error
                fixture.observer_lost = identity == 5
                result = self.settle(fixture)
                seal = result["retention"]
                self.assertEqual(seal["app_url"], f"https://example.lightning.force.com/lightning/n/{fixture.namespace}")
                self.assertEqual(seal["prefix"], fixture.namespace)
                self.assertEqual(seal["inventory"]["assignments"], [{"id": fixture.assignment_id,
                                  "user_id": fixture.target["user_id"], "permission_set_id": fixture.permission_id}])
                self.assertEqual(result.get("build_error"), type(error).__name__ if error else None)
                self.assertEqual(result["observations"]["verified"], not fixture.observer_lost)
                self.assertEqual(fixture.sf.mutations, [("abort", [fixture.job_id])])
                calls = list(fixture.sf.calls)
                self.assertEqual(fixture.command("run", after_build=True), (0, result, ""))
                self.assertEqual(fixture.command("reconcile", "--state", str(fixture.state)), (0, result, ""))
                self.assertEqual(fixture.sf.calls, calls)
                self.assertFalse((fixture.state / "retirement-started.json").exists())

    def test_retention_missing_proof_blocks_new_run_and_recovers_without_destruction(self):
        for identity, interrupt in enumerate((False, True), start=1):
            with self.subTest(interrupt=interrupt):
                fixture = self.layout(identity, interrupt=interrupt)
                fixture.clear_work = interrupt
                code, result, err = fixture.command("run")
                self.assertEqual(code, 1, (result, err))
                self.assertEqual(result["state"], "RETENTION_PENDING")
                self.assertEqual(result["retention_check"]["reason"],
                                 "UNRESOLVED_SUBMISSION" if interrupt else "FIXTURE_APP_WORK_UNPROVEN")
                self.assertFalse(attempt.retained(fixture.state))
                (fixture.state / "settled.json").unlink()  # crash before the result was saved
                self.assertEqual(fixture.command("run")[1]["state"], "RETENTION_PENDING")
                later = self.layout(identity, peer=fixture)
                self.assertEqual(later.command("run")[0], 1)
                self.assertFalse(later.state.exists())
                self.assertFalse(later.launches)
                code, pending, err = fixture.command("reconcile", "--state", str(fixture.state),
                                                     "--cleanup-deadline", str(time.time() + 100))
                self.assertEqual(code, 1, (pending, err))
                self.assertEqual(pending["state"], "RETENTION_PENDING")
                self.assertIn(fixture.assignment_id, fixture.sf.assignments)
                fixture.clear_work = True
                expected_mutations = [("abort", [fixture.job_id])]
                if interrupt:
                    evidence = fixture.evidence("recover-id.json", {"verified_id": fixture.deploy_id})
                    op.write(fixture.state / f"{fixture.key}.reconciled", fixture.bound(
                        "reconciliation", intent_sha256=fixture.key, disposition="REMOTE_ID",
                        remote_id=fixture.deploy_id, evidence=evidence))
                    expected_mutations = []
                    code, active, err = fixture.command("reconcile", "--state", str(fixture.state))
                    self.assertEqual(code, 1, (active, err))
                    self.assertEqual(active["retention_check"]["reason"], "RETAINED_WORK_ACTIVE")
                    self.assertEqual(fixture.sf.mutations, expected_mutations)
                    fixture.sf.jobs[fixture.job_id]["Status"] = "Completed"
                code, sealed, err = fixture.command("reconcile", "--state", str(fixture.state))
                self.assertEqual(code, 0, (sealed, err))
                self.assertTrue(attempt.retained(fixture.state, sealed))
                self.assertEqual(fixture.sf.mutations, expected_mutations)

    def test_retention_reconcile_leaves_new_same_class_owner_work_running(self):
        fixture = self.layout(1)
        fixture.clear_work = False
        code, pending, err = fixture.command("run")
        self.assertEqual(code, 1, (pending, err))
        self.assertEqual(pending["state"], "RETENTION_PENDING")
        self.assertEqual(pending["retention_check"]["reason"], "FIXTURE_APP_WORK_UNPROVEN")
        initial = [("abort", [fixture.job_id])]
        self.assertEqual(fixture.sf.mutations, initial)

        owner_job = sid("707000000000777")
        fixture.sf.add_job(owner_job, fixture.class_id, fixture.class_name)
        fixture.sf.jobs[owner_job]["Status"] = "Processing"
        fixture.clear_work = True
        args = ["--state", str(fixture.state)]
        code, pending, err = fixture.command("reconcile", *args)
        self.assertEqual(fixture.sf.jobs[owner_job]["Status"], "Processing")
        self.assertEqual(fixture.sf.mutations, initial)
        self.assertEqual(code, 1, (pending, err))
        self.assertEqual(pending["state"], "RETENTION_PENDING")
        self.assertEqual(pending["retention_check"]["reason"], "RETAINED_WORK_ACTIVE")
        self.assertFalse(attempt.retained(fixture.state))
        self.assertFalse(attempt.reusable(fixture.state))
        self.assertIn(fixture.assignment_id, fixture.sf.assignments)

        fixture.sf.jobs[owner_job]["Status"] = "Completed"
        code, sealed, err = fixture.command("reconcile", *args)
        self.assertEqual(code, 0, (sealed, err))
        self.assertTrue(attempt.retained(fixture.state, sealed))
        self.assertEqual(fixture.sf.mutations, initial)

    def test_retention_retirement_after_reset_interrupted_before_config_pin(self):
        fixture = self.layout(1)
        args = ["--state", str(fixture.state)]
        pin = fixture.state / "operator-config.json"
        with patch.object(op.Operator, "reset", side_effect=KeyboardInterrupt()):
            code, pending, err = fixture.command("run")
        self.assertEqual(code, 1, (pending, err))
        self.assertEqual(pending["state"], "RETENTION_PENDING")
        self.assertFalse(pin.exists())
        self.assertFalse(fixture.launches)
        self.assertFalse(fixture.sf.mutations)

        code, recovered, err = fixture.command("reconcile", *args)
        self.assertEqual(code, 0, (recovered, err))
        self.assertEqual(recovered["state"], "RETAINED_QUIESCENT")
        self.assertIs(recovered["retention"]["prelaunch_noop"], True)
        self.assertTrue(attempt.retained(fixture.state, recovered))
        self.assertFalse(attempt.reusable(fixture.state))
        seal_path = fixture.state / "retained.json"
        seal = seal_path.read_bytes()

        baseline = fixture.state / "operator-baseline.json"
        op.write(baseline, {})
        code, denied, err = fixture.command("plan-retirement", *args)
        self.assertEqual(code, 1, (denied, err))
        self.assertEqual(denied["retirement_check"]["reason"], "RISKY_MISSING_RESET_PROOF")
        self.assertFalse(pin.exists())
        baseline.unlink()

        metadata = fixture.sf.metadata["ApexClass"]
        metadata.append(entry(fixture.class_name, sid("01p000000000777")))
        code, denied, err = fixture.command("plan-retirement", *args)
        self.assertEqual(code, 1, (denied, err))
        self.assertEqual(denied["retirement_check"]["reason"], "NAMESPACE_NOT_EMPTY")
        self.assertFalse(pin.exists())
        metadata.pop()

        plan = self.plan(fixture)
        self.assertEqual(plan["plan"]["inventory"],
                         {"metadata": {}, "component_sources": {}, "assignments": [], "records": {}})
        self.assertEqual(op.read(pin), {"config_sha256": fixture.authorized,
                                       "binding_sha256": recovered["retention"]["binding_sha256"]})
        wrong = self.approve(fixture, plan, name="unapproved.json", approved=False)
        code, denied, err = fixture.command("retire", *wrong)
        self.assertEqual(code, 1, (denied, err))
        self.assertEqual(denied["retirement_check"]["reason"], "RETIREMENT_APPROVAL_UNVERIFIED")
        self.assertFalse(attempt.reusable(fixture.state))
        self.assertFalse((fixture.state / "retirement-started.json").exists())

        approved = self.approve(fixture, plan)
        alternate = fixture.evidence("alternate-config.json", fixture.config | {
            "observation_seconds": fixture.config["observation_seconds"] + 1,
            "teardown_seconds": fixture.config["teardown_seconds"] - 1,
        })
        with (patch.object(fixture, "config_path", Path(alternate["path"])),
              patch.object(fixture, "authorized", alternate["sha256"])):
            code, denied, err = fixture.command("retire", *approved)
        self.assertEqual(code, 1, (denied, err))
        self.assertIn("OPERATOR_ATTEMPT_CONFIG_MISMATCH", err)
        self.assertFalse((fixture.state / "retirement-started.json").exists())

        self.enterContext(patch.object(op.Phase, "remove_assignments",
                                       side_effect=AssertionError("empty retirement attempted to remove assignments")))
        self.enterContext(patch.object(op.Phase, "destructive_deploy",
                                       side_effect=AssertionError("empty retirement attempted a destructive deploy")))
        with patch.object(op.Phase, "verify_absence", side_effect=op.Refusal("FIXTURE_INTERRUPTED_RETIREMENT")):
            code, interrupted, err = fixture.command("retire", *approved)
        self.assertEqual(code, 1, (interrupted, err))
        self.assertEqual(interrupted["retirement_check"]["reason"], "FIXTURE_INTERRUPTED_RETIREMENT")
        self.assertTrue((fixture.state / "retirement-started.json").is_file())
        self.assertFalse(attempt.reusable(fixture.state))

        code, retired, err = fixture.command("retire", *approved)
        self.assertEqual(code, 0, (retired, err))
        self.assertEqual(retired["state"], "SETTLED")
        self.assertIs(retired["cleanup"]["empty_noop"], True)
        self.assertTrue(attempt.reusable(fixture.state, retired))
        self.assertTrue(attempt.retained(fixture.state, recovered))
        self.assertEqual(seal_path.read_bytes(), seal)
        self.assertEqual(fixture.command("retire", *approved), (0, retired, ""))
        self.assertFalse(fixture.launches)
        self.assertFalse(fixture.sf.mutations)

    def test_retention_missing_reset_after_launch_cannot_be_reconciled_as_empty(self):
        fixture = self.layout(1)
        fixture.clear_work = False
        self.assertEqual(fixture.command("run")[1]["state"], "RETENTION_PENDING")
        (fixture.state / "reset.json").unlink()
        fixture.clear_work = True
        code, result, err = fixture.command("reconcile", "--state", str(fixture.state),
                                           "--cleanup-deadline", str(time.time() + 100))
        self.assertEqual(code, 1, (result, err))
        self.assertEqual(result["state"], "RETENTION_PENDING")
        self.assertIn(fixture.assignment_id, fixture.sf.assignments)
        self.assertEqual(fixture.sf.mutations, [("abort", [fixture.job_id])])
        self.assertFalse((fixture.state / "retained.json").exists())

    def test_retention_fresh_scope_and_exact_deployed_source(self):
        a = self.layout(1)
        result = self.settle(a)
        proof = result["retention"]
        payload, = proof["deployments"]
        self.assertEqual(payload["payload_path"], str(a.payload_path))
        self.assertEqual(payload["source_sha256"], sf_guard.force_app_sha256(a.payload_path))
        self.assertEqual(payload["project_sha256"], ref(a.payload_path / "sfdx-project.json")["sha256"])
        self.assertEqual(proof["inventory"]["component_sources"]["CustomField"], {
            a.object + ".State__c": {"intent_sha256": a.key, "deployment_id": a.deploy_id},
        })
        for kwargs in ({"namespace": "APP1tryMore"}, {"legacy_prefixes": ["APP1try"]},
                       {"namespace": "Retired1New", "legacy_prefixes": ["OtherLegacy"]},
                       {"synthetic_label": "fixture 1 Next"}):
            blocked = self.layout(1, peer=a, **kwargs)
            self.assertEqual(blocked.command("run")[0], 1)
            self.assertFalse(blocked.state.exists())
            self.assertFalse(blocked.launches)
        generated = next((a.output / "work/force-app").rglob("*.cls"))
        generated.write_text("edited only the working tree")
        b_side = self.layout(1, peer=a)
        self.settle(b_side)
        reset = op.read(b_side.state / "reset.json")
        self.assertEqual(reset["retained_generations"], [{"state_dir": str(a.state),
                         "retention_sha256": result["retention_sha256"]}])
        journals = list(a.state.glob("operator-retained-recheck-*/receipt.json"))
        self.assertEqual(len(journals), 1)
        self.assertEqual(op.read(journals[0])["inventory"], proof["inventory"])
        self.assertEqual(a.sf.mutations, [("abort", [a.job_id]), ("abort", [b_side.job_id])])
        self.assertIn(a.assignment_id, a.sf.assignments)

    def owner_inspection(self, fixture):
        new_row = sid("a01000000000777")
        fixture.sf.custom[fixture.object].append(new_row)
        fixture.sf.record_stamps[fixture.row_id] = datetime.now(timezone.utc).isoformat()
        return {fixture.object: {fixture.row_id: fixture.sf.record_stamps[fixture.row_id], new_row: STAMP}}

    def test_retention_fresh_admission_after_owner_inspection(self):
        a = self.layout(1)
        retained = self.settle(a)["retention"]
        historical = {a.state / name: (a.state / name).read_bytes()
                      for name in ("retained.json", "settled.json", "observations.json", "app-access.json")}
        assignment = dict(a.sf.assignments[a.assignment_id])
        records = self.owner_inspection(a)
        self.assertNotEqual(records, retained["inventory"]["records"])
        b_side = self.layout(1, peer=a)
        self.settle(b_side)
        self.assertEqual(len(b_side.launches), 1)
        recheck, = a.state.glob("operator-retained-recheck-*/receipt.json")
        refreshed = op.read(recheck)
        self.assertIs(refreshed["verified"], True)
        self.assertEqual(refreshed["inventory"], dict(retained["inventory"], records=records))
        self.assertEqual(refreshed["deployments"], retained["deployments"])
        self.assertEqual(refreshed["preserved"], retained["preserved"])
        request_ref = refreshed["app_work_clearance"]["request"]
        self.assertNotEqual(request_ref, retained["app_work_clearance"]["request"])
        self.assertEqual(ref(Path(request_ref["path"])), request_ref)
        request = op.read(Path(request_ref["path"]))
        self.assertEqual(request["action"], "retained-recheck")
        self.assertEqual(request["generation_id"], a.state.name)
        self.assertEqual(request["inventory"], refreshed["inventory"])
        self.assertEqual(set(a.sf.custom[a.object]), records[a.object].keys())
        self.assertEqual(a.sf.record_stamps[a.row_id], records[a.object][a.row_id])
        self.assertEqual(a.sf.assignments[a.assignment_id], assignment)
        self.assertEqual(a.sf.mutations, [("abort", [a.job_id]), ("abort", [b_side.job_id])])
        self.assertEqual({path: path.read_bytes() for path in historical}, historical)

    def test_retention_owner_inspection_does_not_allow_metadata_access_or_active_work_drift(self):
        reasons = {"metadata": "DEPLOYED_COMPONENT_SOURCE_AMBIGUOUS", "access": "UNOWNED_APP_ASSIGNMENT",
                   "work": "RETAINED_WORK_ACTIVE"}
        for identity, (fault, reason) in enumerate(reasons.items(), 1):
            with self.subTest(fault=fault):
                a = self.layout(identity)
                self.settle(a)
                self.owner_inspection(a)
                if fault == "metadata":
                    a.sf.metadata["PermissionSet"][0]["lastModifiedDate"] = STAMP
                elif fault == "access":
                    extra = sid("0Pa000000000777")
                    a.sf.assignments[extra] = dict(a.sf.assignments[a.assignment_id], Id=extra)
                else:
                    a.sf.jobs[a.job_id]["Status"] = "Queued"
                b_side = self.layout(identity, peer=a)
                code, result, err = b_side.command("run")
                self.assertEqual(code, 1, (result, err))
                refusal, = b_side.state.glob("operator-reset-*/receipt.json")
                self.assertEqual(op.read(refusal)["reason"], reason)
                self.assertFalse(b_side.launches)
                self.assertFalse((b_side.state / "reset.json").exists())
                self.assertEqual(a.sf.mutations, [("abort", [a.job_id])])

    def test_retention_fresh_admission_blocks_record_changes_during_clearance(self):
        a = self.layout(1)
        self.settle(a)
        self.owner_inspection(a)
        b_side = self.layout(1, peer=a)
        publish = b_side.publish

        def publish_then_change_record(phase):
            publish(phase)
            if phase.phase == "retained-recheck":
                # The clearance already binds the earlier inventory.
                a.sf.record_stamps[a.row_id] = "2026-11-18T20:29:00.000Z"

        with patch.object(b_side, "publish", publish_then_change_record):
            code, result, err = b_side.command("run")
        self.assertEqual(code, 1, (result, err))
        refusal, = b_side.state.glob("operator-reset-*/receipt.json")
        self.assertEqual(op.read(refusal)["reason"], "RETENTION_CHECK_CHANGED")
        self.assertFalse(b_side.launches)
        self.assertFalse((b_side.state / "reset.json").exists())
        self.assertEqual(a.sf.mutations, [("abort", [a.job_id])])

    def test_retention_fresh_admission_blocks_live_or_source_drift(self):
        faults = ("work", "access", "provider", "provider-metadata", "schedule", "schedule-definition",
                  "payload", "metadata", "app-work", "clearance-evidence")
        for identity, fault in enumerate(faults, 1):
            with self.subTest(fault=fault):
                a = self.layout(identity)
                retained = self.settle(a)["retention"]
                b_side = self.layout(identity, peer=a)
                if fault == "work":
                    a.sf.jobs[a.job_id]["Status"] = "Queued"
                elif fault == "access":
                    extra = sid("0Pa000000000777")
                    a.sf.assignments[extra] = dict(a.sf.assignments[a.assignment_id], Id=extra)
                elif fault == "provider":
                    a.sf.data["named_id"] = sid("0XA000000000777")
                elif fault == "provider-metadata":
                    a.sf.metadata["NamedCredential"][0]["lastModifiedDate"] = "2026-11-18T15:28:07.000Z"
                elif fault == "schedule":
                    a.sf.cron.append({"Id": sid("08e000000000777")})
                elif fault == "schedule-definition":
                    a.sf.cron[0]["CronExpression"] = "0 0 8 * * ?"
                elif fault == "payload":
                    (a.payload_path / "sfdx-project.json").write_text("{}")
                elif fault == "metadata":
                    a.sf.metadata["PermissionSet"][0]["lastModifiedDate"] = STAMP
                elif fault == "clearance-evidence":
                    Path(retained["app_work_clearance"]["evidence"]["path"]).write_text("tampered")
                    self.assertFalse(attempt.retained(a.state))
                else:
                    b_side.clear_work = False
                code, result, err = b_side.command("run")
                self.assertEqual(code, 1, (result, err))
                self.assertFalse(b_side.launches)
                self.assertFalse((b_side.state / "reset.json").exists())
                self.assertEqual(a.sf.mutations, [("abort", [a.job_id])])

    def test_retention_retirement_requires_fresh_authority_and_preserves_historical_proof(self):
        fixture = self.layout(1)
        result = self.settle(fixture)
        seal = (fixture.state / "retained.json").read_bytes()
        initial = self.plan(fixture)
        wrong = self.approve(fixture, initial, name="wrong.json", generation_id="f" * 64)
        code, denied, err = fixture.command("retire", *wrong)
        self.assertEqual(code, 1, (denied, err))
        self.assertEqual(denied["retirement_check"]["reason"], "RETIREMENT_APPROVAL_UNVERIFIED")
        stale = self.approve(fixture, initial, name="stale.json")
        new_row = sid("a01000000000777")
        fixture.sf.custom[fixture.object].append(new_row)
        fixture.sf.record_stamps[fixture.row_id] = datetime.now(timezone.utc).isoformat()
        code, denied, err = fixture.command("retire", *stale)
        self.assertEqual(code, 1, (denied, err))
        self.assertEqual(denied["retirement_check"]["reason"], "RETAINED_INVENTORY_CHANGED")
        self.assertEqual(fixture.sf.mutations, [("abort", [fixture.job_id])])
        self.assertFalse((fixture.state / "retirement-started.json").exists())
        fresh = self.plan(fixture)
        self.assertEqual(set(fresh["plan"]["inventory"]["records"][fixture.object]), {fixture.row_id, new_row})
        args = self.approve(fixture, fresh)
        code, retired, err = fixture.command("retire", *args)
        self.assertEqual(code, 0, (retired, err))
        self.assertEqual(retired["state"], "SETTLED")
        self.assertTrue(attempt.reusable(fixture.state, retired))
        self.assertTrue(attempt.retained(fixture.state, result))
        self.assertEqual((fixture.state / "retained.json").read_bytes(), seal)
        self.assertNotIn(fixture.assignment_id, fixture.sf.assignments)
        self.assertEqual(fixture.command("retire", *args), (0, retired, ""))
        self.assertEqual([kind for kind, _ in fixture.sf.mutations], ["abort", "delete-assignment", "destructive"])
        reused_scope = self.layout(1, peer=fixture, namespace="APP1TRY")
        self.assertEqual(reused_scope.command("run")[0], 1)
        self.assertFalse(reused_scope.state.exists())

    def test_retention_retirement_respects_frozen_baseline_dependency(self):
        a = self.layout(1)
        self.settle(a)
        early = self.approve(a, self.plan(a), name="early.json")
        b_side = self.layout(1, peer=a)
        self.settle(b_side)
        mutations = list(a.sf.mutations)
        for command, args in (("plan-retirement", ["--state", str(a.state)]), ("retire", early)):
            code, result, err = a.command(command, *args)
            self.assertEqual(code, 1, (result, err))
            self.assertEqual(result["retirement_check"]["reason"], "RETIRE_DEPENDENT_GENERATION_FIRST")
            self.assertEqual(a.sf.mutations, mutations)
        code, result, err = b_side.command("retire", *self.approve(b_side, self.plan(b_side)))
        self.assertEqual(code, 0, (result, err))
        self.assertTrue(attempt.reusable(b_side.state))
        self.assertIn(a.assignment_id, a.sf.assignments)
        code, result, err = a.command("retire", *self.approve(a, self.plan(a)))
        self.assertEqual(code, 0, (result, err))
        self.assertTrue(attempt.reusable(a.state))
        self.assertTrue(attempt.retained(a.state))

    def test_retention_unresolved_retirement_requires_the_original_explicit_approval(self):
        fixture = self.layout(1)
        result = self.settle(fixture)
        args = self.approve(fixture, self.plan(fixture))
        fixture.sf.lose_destructive_response = True
        code, refused, err = fixture.command("retire", *args)
        self.assertEqual(code, 1, (refused, err))
        self.assertTrue((fixture.state / "retirement-started.json").is_file())
        self.assertTrue(attempt.retained(fixture.state, result))
        self.assertFalse(attempt.reusable(fixture.state))
        mutations = list(fixture.sf.mutations)
        calls = list(fixture.sf.calls)
        code, pending, err = fixture.command("reconcile", "--state", str(fixture.state),
                                             "--cleanup-deadline", str(time.time() + 100))
        self.assertEqual(code, 1, (pending, err))
        self.assertEqual(pending["retention_error"], "RETIREMENT_UNRESOLVED")
        self.assertEqual(fixture.sf.calls, calls)
        intent, = fixture.state.glob("operator-retire-*/*-destructive-submitted.json")
        key = ref(intent)["sha256"]
        evidence = fixture.evidence("recovered-retirement-id.json", {"id": DESTRUCTIVE})
        op.write(fixture.state / f"{key}.destructive-reconciled", fixture.bound(
            "retire", intent_sha256=key, remote_id=DESTRUCTIVE, evidence=evidence))
        code, retired, err = fixture.command("retire", *args)
        self.assertEqual(code, 0, (retired, err))
        self.assertTrue(attempt.reusable(fixture.state, retired))
        self.assertEqual(fixture.sf.mutations, mutations)


if __name__ == "__main__":
    unittest.main()
