"""Operator callbacks for attended Salesforce discovery attempts."""
import os
import re
import signal
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from checks.sf_guard import force_app_sha256, hosted_payload_members
from hosted_outcome import attempt, binding as hosted_binding

TYPES = hosted_binding.TRACKED_METADATA
DEPLOY_TERMINAL = ("Succeeded", "SucceededPartial", "Failed", "Canceled", "FinalizingFailed")
JOB_TERMINAL = ("Completed", "Failed", "Aborted")
JOB_FIELDS = "Id,ApexClassId,ApexClass.Name,ParentJobId,Status"
DIGEST = r"[0-9a-f]{64}"
NAME = r"[A-Za-z0-9_./ -]{1,255}"
REF_NAME = r"[A-Za-z][A-Za-z0-9_]{0,79}"
REFERENCE_URLS = {
    "https://x.ai/news/designing-grok-bot",
    "https://docs.x.ai/grok-bot/bots",
    "https://docs.x.ai/grok-bot/chat-and-collaboration",
}


class Refusal(Exception):
    """Contains only fixed operational codes."""


def require(condition, code):
    if not condition:
        raise Refusal(code)


def matches(pattern, value):
    return isinstance(value, str) and re.fullmatch(pattern, value, re.ASCII) is not None


def sfid(value, prefix=""):
    require(matches(prefix + rf"[A-Za-z0-9]{{{15 - len(prefix)}}}(?:[A-Za-z0-9]{{3}})?", value),
            "INVALID_SALESFORCE_ID")
    base = value[:15]
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"
    suffix = "".join(alphabet[sum(1 << i for i, char in enumerate(base[start:start + 5])
                                  if char.isupper())] for start in (0, 5, 10))
    require(len(value) == 15 or value[15:] == suffix, "INVALID_SALESFORCE_ID_CHECKSUM")
    return base + suffix


sha = hosted_binding.sha
strict_json = hosted_binding.decoded


def read(path):
    require(path.is_file() and not path.is_symlink(), "EVIDENCE_FILE_MISSING")
    result = strict_json(path.read_bytes())
    require(isinstance(result, dict), "INVALID_EVIDENCE")
    return result


def write(path, value):
    write_raw(path, hosted_binding.encoded(value))


def artifact(path):
    return {"path": str(path), "sha256": sha(path.read_bytes())}


def write_raw(path, raw):
    with open(path, "xb", opener=lambda name, flags: os.open(name, flags, 0o600)) as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def records(value, empty=False):
    if empty and value is None:
        return []
    rows = value if isinstance(value, list) else [value]
    require(all(isinstance(row, dict) for row in rows), "INVALID_RECORDS")
    return rows


def quoted(items):
    return "(" + ",".join("'" + item + "'" for item in sorted(items)) + ")"


def timestamp(value):
    require(isinstance(value, str), "MISSING_REMOTE_TIMESTAMP")
    stamp = datetime.fromisoformat(value)
    require(stamp.utcoffset() is not None, "INVALID_REMOTE_TIMESTAMP")
    return stamp.timestamp()


class Operator:
    """Use independently authorized inputs for the existing leased attempt callbacks."""

    def __init__(self, config_path, expected_sha256):
        b = hosted_binding
        self.config_path = b.absolute(config_path)
        raw = self.config_path.read_bytes()
        require(matches(DIGEST, expected_sha256) and sha(raw) == expected_sha256, "CONFIG_DIGEST_MISMATCH")
        self.config_sha256 = expected_sha256
        c = strict_json(raw)
        b.fields(c, "schema binding retirement_plan retirement_verification reference_snapshot "
                    "named_credential_id external_credential sf_bin_sha256 codex_bin "
                    "model_catalog campaign build baseline deadline observation_seconds teardown_seconds")
        require(c["schema"] == "hosted-outcome-operator/1", "INVALID_CONFIG_SCHEMA")
        b.fields(c["binding"], "path sha256")
        self.binding_path = b.absolute(c["binding"]["path"])
        require(matches(DIGEST, c["binding"]["sha256"]) and self.binding_path.is_file()
                and sha(self.binding_path.read_bytes()) == c["binding"]["sha256"], "BINDING_DIGEST_MISMATCH")
        self.binding, self.binding_sha256, self.receipts = b.load(self.binding_path, fresh=False)
        require(self.binding_sha256 == c["binding"]["sha256"], "BINDING_DIGEST_MISMATCH")
        self.output = Path(self.binding["product_cwd"]).parent
        self.external_path(self.config_path)
        self.external_path(self.binding_path)
        self.campaign = self.external_path(c["campaign"])
        self.baseline = self.external_path(c["baseline"])
        require(self.campaign.is_dir() and self.baseline.parent.is_dir()
                and (not self.baseline.exists() or self.baseline.is_file()), "INVALID_CAMPAIGN_PATH")
        self.build = c["build"]
        require(matches(r"[0-9a-f]{40}", self.build), "INVALID_MARKETPLACE_REVISION")
        self.deadline, self.observation_seconds, self.teardown_seconds = (
            c["deadline"], c["observation_seconds"], c["teardown_seconds"])
        require(all(type(item) in (int, float) and 0 < item < 10**12 for item in
                    (self.deadline, self.observation_seconds, self.teardown_seconds)), "INVALID_PHASE_BUDGET")
        self.build_until = self.deadline - self.observation_seconds - self.teardown_seconds

        self.codex_ref = c["codex_bin"]
        self.pinned(self.codex_ref)
        self.codex_bin = self.external_path(self.codex_ref["path"])
        require(os.access(self.codex_bin, os.X_OK), "CODEX_BINARY_UNAVAILABLE")
        self.sf_bin_ref = {"path": self.binding["sf_bin"], "sha256": c["sf_bin_sha256"]}
        self.pinned(self.sf_bin_ref)
        self.catalog_raw = self.pinned(c["model_catalog"])
        self.catalog = strict_json(self.catalog_raw)
        snapshot = strict_json(self.pinned(c["reference_snapshot"]))
        pages = snapshot["pages"]
        require(len(pages) == len(REFERENCE_URLS) and {page["url"] for page in pages} == REFERENCE_URLS,
                "INVALID_REFERENCE_SNAPSHOT")
        for page in pages:
            content = self.pinned({key: page[key] for key in ("path", "sha256")})
            require(page["http_status"] == 200 and len(content) == page["bytes"], "INVALID_REFERENCE_SNAPSHOT")
        self.reference_snapshot = c["reference_snapshot"]

        self.named = {"reference": self.binding["provider"]["reference"],
                      "id": sfid(c["named_credential_id"], "0XA")}
        b.fields(c["external_credential"], "reference id")
        require(matches(REF_NAME, c["external_credential"]["reference"]), "INVALID_EXTERNAL_CREDENTIAL")
        self.external = {"reference": c["external_credential"]["reference"],
                         "id": sfid(c["external_credential"]["id"])}
        self.load_retirement(strict_json(self.pinned(c["retirement_plan"])),
                             strict_json(self.pinned(c["retirement_verification"])))

    def external_path(self, value):
        path = hosted_binding.absolute(value)
        require(not path.is_relative_to(self.output) and not path.is_relative_to(hosted_binding.HERE.parents[1]),
                "OPERATOR_INPUT_MUST_BE_EXTERNAL")
        return path

    def pinned(self, ref):
        hosted_binding.fields(ref, "path sha256")
        path = self.external_path(ref["path"])
        require(path.is_file() and matches(DIGEST, ref["sha256"]), "INVALID_PINNED_FILE")
        raw = path.read_bytes()
        require(raw and sha(raw) == ref["sha256"], "PINNED_FILE_DIGEST_MISMATCH")
        return raw

    def load_retirement(self, plan, verified):
        target = self.binding["target"]
        org = verified["org"]
        require(sfid(plan["org_id"], "00D") == sfid(org["Id"], "00D") == target["org_id"]
                and sfid(plan["initiating_user_id"], "005") == target["user_id"]
                and isinstance(org["OrganizationType"], str) and org["OrganizationType"]
                and type(org["IsSandbox"]) is bool and verified["verified"] is True
                and all(verified[key] == [] for key in ("remaining_owned_entities", "remaining_app_assignments",
                                                       "active_async", "active_deploy")), "RETIREMENT_UNVERIFIED")
        self.retired_org = {key: org[key] for key in ("Id", "OrganizationType", "IsSandbox")}
        provider = verified["provider"]
        require(len(provider) == 1 and provider[0]["DeveloperName"] == self.named["reference"]
                and sfid(provider[0]["Id"], "0XA") == self.named["id"], "RETIREMENT_PROVIDER_MISMATCH")
        members = plan["members"]
        require(isinstance(members, dict) and set(members) <= set(TYPES), "INVALID_RETIREMENT_MEMBERS")
        names, ids = set(), set()
        for rows in members.values():
            require(isinstance(rows, list), "INVALID_RETIREMENT_MEMBERS")
            for row in rows:
                name = row["name"]
                require(matches(NAME, name), "INVALID_RETIREMENT_MEMBER")
                names.add(name.casefold())
                ids.add(sfid(row["id"]))
        self.legacy_names, self.legacy_ids = names, ids
        self.legacy_entities = {row["name"] for row in members.get("CustomObject", [])}
        self.legacy_assignments = {sfid(value, "0Pa") for value in plan["assignment_ids"]}
        self.foreign_cron = {sfid(row["Id"], "08e") for row in verified["scheduled"]}
        require(len(self.foreign_cron) == len(verified["scheduled"]), "DUPLICATE_PRESERVED_CRON")
        namespace = self.binding["namespace"].casefold()
        self.legacy_prefixes = tuple(prefix.casefold() for prefix in self.binding["legacy_prefixes"])
        require(all(not (prefix.startswith(namespace) or namespace.startswith(prefix))
                    for prefix in self.legacy_prefixes) and not any(name.startswith(namespace) for name in names),
                "INVALID_ATTEMPT_SCOPE")

    def latest_sol(self, now):
        stamp = datetime.fromisoformat(self.catalog["fetched_at"])
        require(stamp.utcoffset() is not None and
                hosted_binding.recent(stamp.timestamp(), 28800, now), "MODEL_CATALOG_STALE")
        available = {}
        for row in self.catalog["models"]:
            slug = row["slug"]
            match = re.fullmatch(r"gpt-([0-9]+(?:\.[0-9]+)*)-sol", slug)
            if match and row["visibility"] == "list":
                version = tuple(map(int, match[1].split(".")))
                require(version not in available, "AMBIGUOUS_SOL_CATALOG")
                available[version] = row
        require(available, "SOL_ROUTE_UNAVAILABLE")
        latest = available[max(available)]
        require(latest.get("available", True) is True and latest.get("supported_in_api", True) is True
                and any(row["effort"] == "medium" for row in latest.get("supported_reasoning_levels", [])),
                "SOL_MEDIUM_ROUTE_UNAVAILABLE")
        return latest["slug"]

    def preflight(self, now=None):
        now = time.time() if now is None else now
        require(now < self.build_until < self.deadline <= now + attempt.MAX_CAMPAIGN_SECONDS,
                "OUTSIDE_LAUNCH_BUDGET")
        require(all(hosted_binding.recent(stamp, age, now) for stamp, age in self.receipts.values()),
                "BINDING_RECEIPTS_STALE")
        model = self.latest_sol(now)
        return {"case": hosted_binding.CASE, "config_sha256": self.config_sha256,
                "binding_sha256": self.binding_sha256, "model": model, "effort": "medium",
                "build_until": self.build_until, "deadline": self.deadline}

    def check_context(self, context):
        require(all(context.get(key) == value for key, value in {
            "binding_sha256": self.binding_sha256, "target": self.binding["target"],
            "namespace": self.binding["namespace"], "legacy_prefixes": self.binding["legacy_prefixes"],
            "campaign": str(self.campaign), "build": self.build, "output": str(self.output),
            "build_until": self.build_until, "deadline": self.deadline,
        }.items()), "OPERATOR_CONTEXT_MISMATCH")
        require(context.get("review_hold", False) is self.binding.get("review_hold", False)
                and (not self.binding.get("review_hold")
                     or context.get("synthetic_label") == self.binding["synthetic_label"]),
                "OPERATOR_REVIEW_HOLD_MISMATCH")

    def check_phase(self, context, phase):
        self.check_context(context)
        self.pinned(self.sf_bin_ref)
        state = Path(context["state_dir"])
        if context.get("review_hold") is True:
            require(context["lease_keys"] == attempt.lease_keys(self.binding), "HOSTED_LEASE_KEYS_UNVERIFIED")
            attempt.assert_leased(state, context)
        pin = state / "operator-config.json"
        marker = {"config_sha256": self.config_sha256, "binding_sha256": self.binding_sha256}
        if phase == "reset":
            self.pinned(self.codex_ref)
            model = self.preflight()["model"]
            argv = context["argv"]
            flags = {"--model": model, "--effort": "medium", "--codex-bin": str(self.codex_bin),
                     "--baseline": str(self.baseline), "--environment-binding": str(self.binding_path)}
            require(all(argv.count(key) == 1 and argv[argv.index(key) + 1] == value
                        for key, value in flags.items()), "OPERATOR_LAUNCH_ARGUMENT_MISMATCH")
            write(pin, marker)
            write_raw(state / "operator-model-catalog.json", self.catalog_raw)
            write(state / "operator-model-route.json",
                  {"model": model, "effort": "medium", "sha256": sha(self.catalog_raw),
                   "reference_snapshot": self.reference_snapshot})
        elif os.path.lexists(pin):
            require(read(pin) == marker, "OPERATOR_ATTEMPT_CONFIG_MISMATCH")
        elif not (phase in {"cleanup", "retain"} and context.get("reconcile_prelaunch_noop") is True):
            require(phase == "retirement-plan" and attempt.retained(state)
                    and read(state / "retained.json")["retention"].get("prelaunch_noop") is True,
                    "EVIDENCE_FILE_MISSING")

    def reset(self, context, absolute_cutoff):
        return _reset(self, context, absolute_cutoff)

    def observe(self, context, absolute_cutoff):
        return _observe(self, context, absolute_cutoff)

    def cleanup(self, context, absolute_cutoff):
        return _cleanup(self, context, absolute_cutoff)

    def retain(self, context, absolute_cutoff):
        return _retain(self, context, absolute_cutoff)

    def plan_retirement(self, context, absolute_cutoff):
        return _plan_retirement(self, context, absolute_cutoff)

    def retire(self, context, absolute_cutoff):
        return _retire(self, context, absolute_cutoff)


class Salesforce:
    def __init__(self, username, cutoff, directory, binding):
        self.username, self.cutoff, self.directory = username, cutoff, directory
        self.bin = binding["sf_bin"]
        self.path = os.pathsep.join([*binding["tool_dirs"], *hosted_binding.SYSTEM_DIRS])

    def call(self, *args, cwd=None, report=False):
        remaining = self.cutoff - time.time()
        require(remaining > 0, "PHASE_CUTOFF")
        keys = ("HOME", "USER", "LOGNAME", "TMPDIR", "LANG", "LC_ALL", "SF_USE_GENERIC_UNIX_KEYCHAIN")
        env = {key: os.environ[key] for key in keys if key in os.environ}
        env.update(PATH=self.path,
                   SF_DISABLE_LOG_FILE="true", SF_AUTOUPDATE_DISABLE="true", SF_DISABLE_TELEMETRY="true")
        with subprocess.Popen([self.bin, *args, "--target-org", self.username, "--json"],
                              cwd=cwd or self.directory, env=env, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              start_new_session=True) as child:
            try:
                raw, _ = child.communicate(timeout=max(0, self.cutoff - time.time()))
            except BaseException:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                raise
        doc = strict_json(raw)
        require(isinstance(doc, dict) and type(doc.get("status")) is int, "INVALID_CLI_ENVELOPE")
        if child.returncode == doc["status"] == 0 and "result" in doc:
            return doc["result"]
        if report and child.returncode > 0 and doc["status"] > 0:
            result = doc.get("result") or doc.get("data")
            if isinstance(result, dict) and result.get("status") in DEPLOY_TERMINAL:
                return result
        raise Refusal("SALESFORCE_COMMAND_FAILED")

    def query(self, fields, source, *, tooling=False, all_rows=False):
        args = ["data", "query", "--query", f"SELECT {fields} FROM {source}"]
        if tooling:
            args.append("--use-tooling-api")
        if all_rows:
            args.append("--all-rows")
        result = self.call(*args)
        rows = result.get("records")
        require(result.get("done") is True and not result.get("nextRecordsUrl") and isinstance(rows, list)
                and type(result.get("totalSize")) is int and result["totalSize"] == len(rows),
                "INCOMPLETE_QUERY")
        return records(rows)


class Phase:
    def __init__(self, operator, context, cutoff, phase):
        self.operator = operator
        self.context, self.cutoff, self.phase = context, cutoff, phase
        self.state = Path(context["state_dir"])
        self.target = context["target"]
        self.binding = context["binding_sha256"]
        self.namespace = context["namespace"].casefold()
        self.sf = Salesforce(self.target["username"], cutoff, self.state, operator.binding)
        self.legacy_prefixes = tuple(sorted({*operator.legacy_prefixes,
                                             *(p.casefold() for p in context["legacy_prefixes"])}))
        self.journal = Path(tempfile.mkdtemp(prefix=f"operator-{phase}-", dir=self.state))
        self.index = 0

    def bound(self, phase=None):
        value = {"binding_sha256": self.binding, "target": self.target}
        return dict(value, phase=phase) if phase else value

    def linked(self, value, phase):
        return all(value.get(key) == expected for key, expected in self.bound(phase).items())

    def log(self, event, **fields):
        self.index += 1
        write(self.journal / f"{self.index:04d}-{event}.json",
              dict(self.bound(self.phase), checked_at=time.time(), **fields))

    def receipt(self, **fields):
        value = dict(self.bound(self.phase), checked_at=time.time(), evidence_path=str(self.journal), **fields)
        write(self.journal / "receipt.json", value)
        return value

    def pause(self):
        remaining = self.cutoff - time.time()
        require(remaining > 0, "PHASE_CUTOFF")
        time.sleep(min(1, remaining))

    def verify_identity(self):
        org_id, user_id = self.target["org_id"], self.target["user_id"]
        response = self.sf.call("api", "request", "rest", "/services/oauth2/userinfo", "--method", "GET")
        require(response.get("statusCode") == 200, "USERINFO_HTTP_FAILURE")
        identity = response.get("body")
        if isinstance(identity, str):
            identity = strict_json(identity.encode())
        require(isinstance(identity, dict) and identity.get("organization_id") in (org_id, org_id[:15])
                and identity.get("user_id") in (user_id, user_id[:15])
                and identity.get("preferred_username") == self.target["username"], "USERINFO_TARGET_MISMATCH")
        org = self.sf.query("Id,OrganizationType,IsSandbox", "Organization")
        require(len(org) == 1 and all(org[0].get(key) == value for key, value in self.operator.retired_org.items()),
                "ORG_IDENTITY_MISMATCH")
        self.log("identity")

    def metadata(self, kind):
        raw = self.sf.call("org", "list", "metadata", "--metadata-type", kind)
        result = {}
        for row in records(raw, empty=True):
            name = row.get("fullName")
            require(matches(NAME, name) and name not in result, "INVALID_METADATA_NAME")
            mid, stamp = row.get("id"), row.get("lastModifiedDate")
            require(stamp is None or matches(r"[0-9T:+.Z-]{10,40}", stamp), "INVALID_METADATA_TIMESTAMP")
            result[name] = {"id": sfid(mid) if mid else None, "last_modified": stamp}
        return result

    def inventory(self):
        return {kind: self.metadata(kind) for kind in TYPES}

    def legacy(self, name):
        folded = name.casefold()
        return folded.startswith(self.legacy_prefixes) or folded in self.operator.legacy_names

    def scoped(self, name):
        return name.casefold().startswith(self.namespace) or self.legacy(name)

    def preserved(self):
        named = self.operator.named
        credential = self.operator.external
        held = self.context.get("review_hold") is True
        provider = self.sf.query("Id,DeveloperName", f"NamedCredential WHERE DeveloperName='{named['reference']}'",
                                 tooling=True)
        require(len(provider) == 1 and sfid(provider[0]["Id"]) == named["id"]
                and provider[0]["DeveloperName"] == named["reference"], "NAMED_CREDENTIAL_CHANGED")
        external = self.metadata("ExternalCredential").get(credential["reference"])
        require(external and external["id"] == credential["id"], "EXTERNAL_CREDENTIAL_UNVERIFIED")
        if held:
            named_metadata = self.metadata("NamedCredential").get(named["reference"])
            require(named_metadata and named_metadata["id"] == named["id"], "NAMED_CREDENTIAL_METADATA_UNVERIFIED")
            timestamp(named_metadata["last_modified"])
            timestamp(external["last_modified"])
            named = dict(named, last_modified=named_metadata["last_modified"])
        cron_fields = "Id,State,CronJobDetailId,CronJobDetail.Name"
        if held:
            cron_fields += ",CronExpression,TimeZoneSidKey"
        cron = self.sf.query(cron_fields,
                             "CronTrigger WHERE State NOT IN ('COMPLETE','DELETED','ERROR')")
        for row in cron:
            name = row["CronJobDetail"]["Name"]
            require(isinstance(name, str) and not self.scoped(name), "SCOPED_SCHEDULE_PRESENT")
        cron_ids = {sfid(row["Id"], "08e") for row in cron}
        require(len(cron) == len(cron_ids) and self.operator.foreign_cron == cron_ids, "CRON_INVENTORY_AMBIGUOUS")
        if self.operator.legacy_assignments:
            retired = self.sf.query("Id", "PermissionSetAssignment WHERE Id IN "
                                    + quoted(self.operator.legacy_assignments))
            require(not retired, "LEGACY_ASSIGNMENT_PRESENT")
        preserved = {"named": named, "external": dict(external, reference=credential["reference"]),
                     "cron": sorted(cron_ids)}
        if held:
            require(all(isinstance(row[key], str) and row[key] for row in cron
                        for key in ("CronExpression", "TimeZoneSidKey")), "CRON_DEFINITION_UNVERIFIED")
            preserved["cron_definitions"] = {sfid(row["Id"], "08e"): {
                "detail_id": sfid(row["CronJobDetailId"]), "name": row["CronJobDetail"]["Name"],
                "expression": row["CronExpression"], "timezone": row["TimeZoneSidKey"],
            } for row in cron}
        return preserved

    def no_scoped_entities(self):
        names = {self.namespace, *self.legacy_prefixes}
        clause = " OR ".join(f"QualifiedApiName LIKE '{prefix}%'" for prefix in sorted(names))
        if self.operator.legacy_entities:
            clause += " OR QualifiedApiName IN " + quoted(self.operator.legacy_entities)
        rows = self.sf.query("QualifiedApiName", "EntityDefinition WHERE " + clause)
        require(not any(self.scoped(row["QualifiedApiName"]) for row in rows), "SCOPED_ENTITY_REMAINS")

    def empty_inventory(self):
        inventory = self.inventory()
        require(not any(self.scoped(name) or row["id"] in self.operator.legacy_ids
                        for rows in inventory.values() for name, row in rows.items()), "NAMESPACE_NOT_EMPTY")
        self.no_scoped_entities()
        self.active_deployments()
        require(not self.active_jobs(set()), "OWNED_JOB_PRESENT")
        return inventory, self.preserved()

    def active_deployments(self):
        result = self.sf.query("Id,Status", "DeployRequest WHERE Status NOT IN " + quoted(DEPLOY_TERMINAL), tooling=True)
        require(not result, "ACTIVE_OR_AMBIGUOUS_DEPLOYMENT")

    def deploy_report(self, remote_id):
        rid = sfid(remote_id, "0Af")
        while True:
            row = self.sf.query("Id,Status", f"DeployRequest WHERE Id='{rid}'", tooling=True)
            require(len(row) == 1 and sfid(row[0]["Id"], "0Af") == rid, "DEPLOYMENT_TARGET_UNVERIFIED")
            report = self.sf.call("project", "deploy", "report", "--job-id", remote_id, report=True)
            status = report.get("status")
            require(sfid(report.get("id"), "0Af") == rid, "DEPLOYMENT_REPORT_ID_MISMATCH")
            if status in DEPLOY_TERMINAL and report.get("done") is True and row[0]["Status"] == status:
                return report
            require(status in (*DEPLOY_TERMINAL, "Pending", "InProgress", "Canceling", "Finalizing"),
                    "UNKNOWN_DEPLOYMENT_STATUS")
            self.pause()

    def active_jobs(self, classes):
        active = self.sf.query(JOB_FIELDS, "AsyncApexJob WHERE Status NOT IN " + quoted(JOB_TERMINAL))
        indexed = {sfid(row["Id"], "707"): row for row in active}
        require(len(indexed) == len(active), "DUPLICATE_JOB_ID")
        seen = dict(indexed)
        parents = {sfid(row["ParentJobId"], "707") for row in active if row["ParentJobId"]}
        while missing := parents - seen.keys():
            rows = self.sf.query(JOB_FIELDS, "AsyncApexJob WHERE Id IN " + quoted(missing))
            added = {sfid(row["Id"], "707"): row for row in rows}
            require(added.keys() == missing, "JOB_LINEAGE_UNVERIFIED")
            seen.update(added)
            parents = {sfid(row["ParentJobId"], "707") for row in rows if row["ParentJobId"]}
        owned = set()
        for job_id, job in indexed.items():
            own_class = job["ApexClassId"] and sfid(job["ApexClassId"], "01p") in classes
            visited = set()
            related = False
            node = job
            while True:
                aid = node["ApexClassId"]
                name = (node.get("ApexClass") or {}).get("Name")
                require(aid is None or (isinstance(name, str) and (not self.scoped(name)
                        or sfid(aid, "01p") in classes) and sfid(aid, "01p") not in self.operator.legacy_ids),
                        "UNATTRIBUTED_SCOPED_JOB")
                related |= bool(aid and sfid(aid, "01p") in classes)
                if not node["ParentJobId"]:
                    break
                pid = sfid(node["ParentJobId"], "707")
                require(pid not in visited, "JOB_LINEAGE_CYCLE")
                visited.add(pid)
                node = seen[pid]
            require(not related or own_class, "FOREIGN_CLASS_ON_OWNED_JOB_LINEAGE")
            if own_class:
                owned.add(job_id)
        self.log("jobs", owned=sorted(owned), unrelated=sorted(indexed.keys() - owned))
        return owned

    def evidence_ref(self, ref):
        require(isinstance(ref, dict) and matches(DIGEST, ref.get("sha256"))
                and isinstance(ref.get("path"), str), "INVALID_EVIDENCE_REFERENCE")
        path = Path(ref["path"])
        require(path.is_absolute() and path.resolve() == path and path.is_file()
                and self.state / "observations.json" != path
                and not path.is_relative_to(Path(self.context["output"])), "EVIDENCE_REFERENCE_UNVERIFIED")
        raw = path.read_bytes()
        require(raw and sha(raw) == ref["sha256"], "EVIDENCE_REFERENCE_UNVERIFIED")
        return {"path": str(path), "sha256": ref["sha256"]}

    def intent(self, key):
        require(matches(DIGEST, key), "INVALID_INTENT_KEY")
        path = self.state / f"{key}.intent"
        require(path.is_file() and not path.is_symlink(), "EVIDENCE_FILE_MISSING")
        intent_raw = path.read_bytes()
        intent = strict_json(intent_raw)
        submitted = read(self.state / f"{key}.submitted")
        try:
            members, approval_hash = hosted_binding.approval(self.state / f"{key}.approved", key,
                                                             intent_raw, self.context)
        except (OSError, ValueError, KeyError, TypeError):
            raise Refusal("INTENT_APPROVAL_MISMATCH") from None
        root = Path(intent["root"])
        output = Path(self.context["output"])
        source_ok = root == output / "work" or (output / "work") in root.parents or (
            root.name == "worktree" and root.parent.name.startswith("work-")
            and root.parent.parent == output / ".shiploop-runs")
        require(root.is_absolute() and ".." not in root.parts and source_ok
                and submitted.get("intent_sha256") == key and submitted.get("approval_sha256") == approval_hash
                and submitted.get("forward_target") == {"requested": self.target["selector"],
                                                        "effective": self.target["username"]},
                "INTENT_APPROVAL_MISMATCH")
        return intent, members

    def payload(self, key, intent):
        submitted = read(self.state / f"{key}.submitted")
        path = hosted_binding.absolute(submitted.get("payload"))
        require(path.parent == self.state and path.name.startswith(f"{key}.payload-"), "PAYLOAD_PATH_MISMATCH")
        project = path / "sfdx-project.json"
        require(project.is_file() and not project.is_symlink() and sha(project.read_bytes()) == intent["project_sha256"]
                and force_app_sha256(path) == intent["force_app_sha256"], "DEPLOYED_PAYLOAD_CHANGED")
        hosted_binding.approval(self.state / f"{key}.approved", key, (self.state / f"{key}.intent").read_bytes(),
                                self.context, payload_members=hosted_payload_members(path, self.context["namespace"]))
        return {"payload_path": str(path), "project_sha256": intent["project_sha256"],
                "approval_sha256": submitted["approval_sha256"]}

    def deployments(self, *, exact=False):
        keys = {path.stem for path in self.state.glob("*.submitted")}
        require({path.stem for path in self.state.glob("*.returned")} <= keys, "ORPHANED_DEPLOYMENT_RETURN")
        deployed, components, used, sources = [], {}, set(), {}
        for key in sorted(keys):
            intent, members = self.intent(key)
            payload = self.payload(key, intent) if exact else {}
            returned = self.state / f"{key}.returned"
            remote_id = read(returned).get("remote_id") if returned.exists() else None
            if remote_id is None:
                self.log("unidentified-submission", intent_sha256=key)
                path = self.state / f"{key}.reconciled"
                require(path.exists(), "UNRESOLVED_SUBMISSION")
                reconciliation = read(path)
                require(self.linked(reconciliation, "reconciliation") and reconciliation.get("intent_sha256") == key
                        and reconciliation.get("verified") is True, "UNRESOLVED_SUBMISSION")
                reference = self.evidence_ref(reconciliation.get("evidence"))
                disposition = reconciliation.get("disposition")
                self.log("reconciliation", intent_sha256=key, evidence=reference,
                         disposition=disposition if disposition in {"NOT_SUBMITTED", "REMOTE_ID"} else "UNKNOWN")
                if disposition == "NOT_SUBMITTED":
                    require(reconciliation.get("remote_id") is None
                            and reconciliation.get("basis") == "INDEPENDENT_PRE_SUBMIT_FAILURE_EVIDENCE",
                            "NO_SUBMISSION_EVIDENCE_UNVERIFIED")
                    continue
                require(disposition == "REMOTE_ID", "UNRESOLVED_SUBMISSION")
                remote_id = reconciliation.get("remote_id")
            rid = sfid(remote_id, "0Af")
            require(rid not in used, "AMBIGUOUS_DEPLOYMENT_LINK")
            used.add(rid)
            self.log("deployment-id", intent_sha256=key, remote_id=remote_id)
            report = self.deploy_report(remote_id)
            links = {"intent_sha256": key, "source_sha256": intent["force_app_sha256"], "deployment_id": rid}
            self.log("deployment-terminal", status=report["status"], **links)
            succeeded = report["status"] == "Succeeded" and report.get("success") is True
            if exact:
                require(report["status"] in {"Succeeded", "Failed", "Canceled"}
                        and (report["status"] != "Succeeded" or succeeded),
                        "DEPLOYMENT_RESULT_AMBIGUOUS")
                if succeeded:
                    created, completed = report.get("createdDate"), report.get("completedDate")
                    submitted_at = read(self.state / f"{key}.submitted").get("submitted_at")
                    require(type(submitted_at) in (int, float)
                            and int(submitted_at) <= timestamp(created) <= timestamp(completed) <= time.time(),
                            "DEPLOYED_PAYLOAD_WINDOW_UNVERIFIED")
                    links.update(payload, created_at=created, completed_at=completed)
            if succeeded:
                deployed.append(links)
            details = report.get("details") or {}
            reported = set()
            for part in records(details.get("componentSuccesses"), empty=True):
                kind, name = part.get("componentType"), part.get("fullName")
                if kind in (None, "") and name == "package.xml":
                    continue
                require(kind in members and name in members[kind] and part.get("success") is True
                        and part.get("deleted") is not True, "DEPLOYMENT_COMPONENT_OUT_OF_SCOPE")
                # Rolled back items are never ownership evidence.
                if report["status"] in {"Succeeded", "SucceededPartial"} and kind in TYPES:
                    mid = sfid(part.get("id"))
                    pair = kind, name
                    component = components.setdefault(pair, {})
                    component[mid] = component.get(mid, False) or part.get("created") is True
                if exact and succeeded:
                    pair = kind, name
                    require(pair not in reported, "DUPLICATE_DEPLOYMENT_MEMBER")
                    reported.add(pair)
                    sources.setdefault(pair, []).append({**links, "id": sfid(part.get("id"))})
            if exact and succeeded:
                require(reported == {(kind, name) for kind, names in members.items() for name in names},
                        "DEPLOYMENT_MEMBER_MAP_INCOMPLETE")
        self.active_deployments()
        return sorted(keys), deployed, components, sources

    def baseline(self):
        path = self.state / "operator-baseline.json"
        baseline = read(path)
        proof = read(self.state / "reset.json")
        require(self.linked(baseline, "reset") and self.linked(proof, "reset")
                and proof.get("verified") is True and proof.get("empty_noop") is True
                and attempt.reset_retained(proof, self.context)
                and sha(path.read_bytes()) == proof.get("baseline_sha256"), "RESET_BASELINE_UNVERIFIED")
        return baseline

    def ownership(self, *, exact=False):
        baseline = self.baseline()
        intents, deployed, components, sources = self.deployments(exact=exact)
        current = self.inventory()
        owned = self.owned(current, baseline["metadata"], components)
        preserved = self.preserved()
        require(preserved == baseline["preserved"], "PRESERVED_RESOURCES_CHANGED")
        self.log("owned-members", members=owned)
        return intents, deployed, sources, current, owned, preserved

    def checked_baseline(self, current, frozen):
        require(all(current[kind].get(name) == member for kind, rows in frozen.items()
                    for name, member in rows.items()), "BASELINE_METADATA_CHANGED")

    def owned(self, current, before, components):
        self.checked_baseline(current, before)
        result = {}
        for kind, rows in current.items():
            for name, row in rows.items():
                if self.scoped(name) or row["id"] in self.operator.legacy_ids:
                    require(not self.legacy(name) and row["id"] not in self.operator.legacy_ids
                            and name not in before[kind] and components.get((kind, name), {}).get(row["id"]) is True,
                            "UNPROVEN_SCOPED_COMPONENT")
                    result.setdefault(kind, {})[name] = row["id"]
        for (kind, name) in components:
            if kind in current and name in current[kind]:
                require(name in result.get(kind, {}), "DEPLOYMENT_MEMBER_NOT_OWNED")
        return result

    def assignments(self, permsets, *, exact=False):
        if not permsets:
            return []
        clause = "PermissionSetAssignment WHERE PermissionSetId IN " + quoted(permsets)
        fields = "Id,AssigneeId,PermissionSetId"
        rows = self.sf.query(fields, clause)
        if not rows and not exact:
            return []
        approved = read(self.state / "app-access.json")
        require(self.linked(approved, "app-access") and approved.get("verified") is True
                and isinstance(approved.get("assignment_ids"), list), "APP_ACCESS_EVIDENCE_UNVERIFIED")
        ids = {sfid(row["Id"], "0Pa") for row in rows}
        approved_ids = {sfid(x, "0Pa") for x in approved["assignment_ids"]}
        require(len(ids) == len(rows) and ids <= approved_ids
                and all(sfid(row["AssigneeId"], "005") == self.target["user_id"] and sfid(row["PermissionSetId"], "0PS") in permsets
                        for row in rows), "UNOWNED_APP_ASSIGNMENT")
        require(not exact or (ids and ids == approved_ids and len(approved_ids) == len(approved["assignment_ids"])),
                "APP_ACCESS_INVENTORY_CHANGED")
        return sorted((dict(id=sfid(row["Id"], "0Pa"), user_id=sfid(row["AssigneeId"], "005"),
                            permission_set_id=sfid(row["PermissionSetId"], "0PS")) for row in rows),
                      key=lambda row: row["id"])

    def remove_assignments(self, permsets, *, expected=None):
        rows = self.assignments(permsets, exact=expected is not None)
        require(expected is None or rows == expected, "APP_ACCESS_INVENTORY_CHANGED")
        if not rows:
            return
        ids = [row["id"] for row in rows]
        self.log("remove-assignments", assignment_ids=sorted(ids))
        for record_id in sorted(ids):
            self.sf.call("data", "delete", "record", "--sobject", "PermissionSetAssignment", "--record-id", record_id)
        self.require_no_assignments(permsets)

    def require_no_assignments(self, permsets):
        if permsets:
            require(not self.sf.query("Id", "PermissionSetAssignment WHERE PermissionSetId IN " + quoted(permsets)),
                    "APP_ACCESS_STILL_PRESENT")

    def retained_members(self, current, owned):
        metadata = {kind: {name: current[kind][name] for name in sorted(names)} for kind, names in owned.items()}
        for name, object_id in owned.get("CustomObject", {}).items():
            rows = self.sf.query("Id,DeveloperName,NamespacePrefix,LastModifiedDate",
                                 f"CustomField WHERE TableEnumOrId='{object_id}'", tooling=True)
            for row in rows:
                field_name = row["DeveloperName"]
                require(row["NamespacePrefix"] is None and matches(REF_NAME, field_name), "FOREIGN_CUSTOM_FIELD")
                full_name = f"{name}.{field_name}__c"
                fields = metadata.setdefault("CustomField", {})
                require(full_name not in fields, "AMBIGUOUS_CUSTOM_FIELD")
                fields[full_name] = {"id": sfid(row["Id"], "00N"), "last_modified": row["LastModifiedDate"]}
        require(all(len({name.casefold() for name in rows}) == len(rows) for rows in metadata.values()),
                "CASE_INSENSITIVE_METADATA_AMBIGUOUS")
        return metadata

    def source_links(self, metadata, sources):
        refs = {}
        require(set(sources) == {(kind, name) for kind, rows in metadata.items() for name in rows},
                "DEPLOYED_MEMBER_INVENTORY_CHANGED")
        for kind, rows in metadata.items():
            for name, row in rows.items():
                modified = timestamp(row["last_modified"])
                candidates = [source for source in sources[(kind, name)] if source["id"] == row["id"]
                              and int(timestamp(source["created_at"])) <= modified
                              and modified < int(timestamp(source["completed_at"])) + 1]
                require(len(candidates) == 1, "DEPLOYED_COMPONENT_SOURCE_AMBIGUOUS")
                refs.setdefault(kind, {})[name] = {key: candidates[0][key]
                                                   for key in ("intent_sha256", "deployment_id")}
        return refs

    def retained_records(self, objects):
        scope = {}
        for name in sorted(objects):
            require(matches(r"[A-Za-z][A-Za-z0-9_]*__c", name), "UNSUPPORTED_RECORD_SCOPE")
            rows = self.sf.query("Id,SystemModstamp", name, all_rows=True)
            ids = {sfid(row["Id"]): row["SystemModstamp"] for row in rows}
            require(len(ids) == len(rows), "DUPLICATE_RECORD_ID")
            for stamp in ids.values():
                timestamp(stamp)
            scope[name] = ids
        return scope

    def held_inventory(self, current, owned, sources):
        metadata = self.retained_members(current, owned)
        permsets = set(owned.get("PermissionSet", {}).values())
        require(not owned or permsets, "APP_ACCESS_NOT_PROVEN")
        return {"metadata": metadata, "component_sources": self.source_links(metadata, sources),
                "assignments": self.assignments(permsets, exact=True),
                "records": self.retained_records(owned.get("CustomObject", {}))}

    def app_work_clearance(self, inventory, deployed):
        request_path = self.journal / "app-work-request.json"
        response_path = self.journal / "app-work-cleared.json"
        started = time.time()
        write(request_path, dict(self.bound("app-work"), generation_id=self.state.name,
                                 prefix=self.context["namespace"], synthetic_label=self.context["synthetic_label"],
                                 action=self.phase, checked_at=started, cutoff=self.cutoff,
                                 inventory_sha256=sha(hosted_binding.encoded(inventory)), inventory=inventory,
                                 deployments=deployed))
        while not os.path.lexists(response_path):
            self.pause()
        clear = read(response_path)
        digest = sha(request_path.read_bytes())
        require(self.linked(clear, "app-work") and clear.get("generation_id") == self.state.name
                and clear.get("request_sha256") == digest and clear.get("verified") is True
                and clear.get("pending") is False and started <= clear["checked_at"] <= min(time.time(), self.cutoff),
                "APP_WORK_CLEARANCE_UNVERIFIED")
        evidence = self.evidence_ref(clear.get("evidence"))
        require(not Path(evidence["path"]).is_relative_to(self.journal), "APP_WORK_EVIDENCE_NOT_INDEPENDENT")
        url = clear.get("app_url")
        if url is not None:
            require(matches(r"https://[A-Za-z0-9.-]+/[A-Za-z0-9/_.%-]+", url), "INVALID_APP_URL")
            require(urlsplit(url).hostname.endswith((".salesforce.com", ".force.com")), "INVALID_APP_URL")
        self.log("app-work-cleared", evidence=evidence, app_url=url, request_sha256=digest)
        return url, {"request": {"path": str(request_path), "sha256": digest}, "evidence": evidence,
                     "receipt": artifact(response_path)}

    def quiesce(self, classes):
        aborted, quiet = set(), 0
        while quiet < 2:
            self.active_deployments()
            active = self.active_jobs(classes)
            fresh = active - aborted
            if fresh:
                self.log("abort-jobs", job_ids=sorted(fresh))
                script = self.journal / f"{self.index:04d}-abort.apex"
                with script.open("x") as stream:
                    for job_id in sorted(fresh):
                        stream.write(f"System.abortJob('{job_id}');\n")
                result = self.sf.call("apex", "run", "--file", str(script))
                require(result.get("compiled") is True and result.get("success") is True, "ABORT_NOT_CONFIRMED")
                aborted.update(fresh)
            quiet = 0 if active else quiet + 1
            if quiet < 2:
                self.pause()
        if aborted:
            rows = self.sf.query("Id,Status", "AsyncApexJob WHERE Id IN " + quoted(aborted))
            terminal = {sfid(row["Id"], "707"): row["Status"] for row in rows if row["Status"] in JOB_TERMINAL}
            require(terminal.keys() == aborted, "ABORTED_JOB_TERMINAL_STATUS_UNVERIFIED")
            self.log("aborted-jobs-terminal", jobs=terminal)

    def record_review(self, objects):
        scope = {}
        for name in sorted(objects):
            require(matches(r"[A-Za-z][A-Za-z0-9_]*__c", name), "UNSUPPORTED_RECORD_SCOPE")
            ids = [sfid(row["Id"]) for row in self.sf.query("Id", name, all_rows=True)]
            require(len(set(ids)) == len(ids), "DUPLICATE_RECORD_ID")
            scope[name] = {"count": len(ids), "ids": sorted(ids)}
        self.log("record-inventory", objects=scope)
        if any(row["count"] for row in scope.values()):
            request = dict(self.bound("synthetic-records"), objects=scope, cutoff=self.cutoff)
            request_path = self.state / "cleanup-records.json"
            if not request_path.exists():
                write(request_path, request)
            else:
                prior = read(request_path)
                require(self.linked(prior, "synthetic-records") and prior.get("objects") == scope,
                        "PRIOR_RECORD_REVIEW_DIFFERS")
            path = self.state / "cleanup-synthetic.json"
            while not path.exists():
                self.pause()
            review = read(path)
            require(self.linked(review, "synthetic-records") and review.get("verified") is True
                    and review.get("objects") == scope, "SYNTHETIC_RECORDS_UNVERIFIED")
            self.log("synthetic-review", evidence=self.evidence_ref(review.get("evidence")))
        return scope

    def reconcile_destructive(self, prior):
        submitted = read(prior)
        require(self.linked(submitted, self.phase), "DESTRUCTIVE_INTENT_MISMATCH")
        key = sha(prior.read_bytes())
        returned = list(prior.parent.glob("*-destructive-returned.json"))
        require(len(returned) <= 1, "AMBIGUOUS_DESTRUCTIVE_ID")
        if returned:
            receipt = read(returned[0])
            require(self.linked(receipt, self.phase) and receipt.get("intent_sha256") == key,
                    "DESTRUCTIVE_ID_MISMATCH")
        else:
            path = self.state / f"{key}.destructive-reconciled"
            require(path.exists(), "DESTRUCTIVE_ID_UNRESOLVED")
            receipt = read(path)
            require(self.linked(receipt, self.phase) and receipt.get("intent_sha256") == key
                    and receipt.get("verified") is True, "DESTRUCTIVE_ID_MISMATCH")
            self.log("destructive-reconciliation", evidence=self.evidence_ref(receipt.get("evidence")))
        self.destructive_terminal(receipt.get("remote_id"))
        return submitted

    def destructive_terminal(self, remote_id):
        final = self.deploy_report(remote_id)
        self.log("destructive-terminal", remote_id=remote_id, status=final["status"])
        require(final["status"] == "Succeeded" and final.get("success") is True, "DESTRUCTIVE_DEPLOY_FAILED")

    def destructive_deploy(self, owned, survivors):
        project = self.journal / "destructive"
        project.mkdir()
        (project / "force-app").mkdir()
        write(project / "sfdx-project.json", {"packageDirectories": [{"path": "force-app", "default": True}],
                                              "sourceApiVersion": "68.0"})
        package, changes = project / "package.xml", project / "destructiveChangesPost.xml"
        for path, selection in ((package, {}), (changes, owned)):
            root = ET.Element("Package", xmlns="http://soap.sforce.com/2006/04/metadata")
            for kind, members in sorted(selection.items()):
                types = ET.SubElement(root, "types")
                for name in sorted(members):
                    ET.SubElement(types, "members").text = name
                ET.SubElement(types, "name").text = kind
            ET.SubElement(root, "version").text = "68.0"
            ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
        self.log("destructive-submitted", members=owned, survivors=survivors, manifest_sha256=sha(changes.read_bytes()))
        intent = self.journal / f"{self.index:04d}-destructive-submitted.json"
        args = ["project", "deploy", "start", "--manifest", str(package),
                "--post-destructive-changes", str(changes), "--async"]
        if owned.get("CustomObject"):
            args.append("--purge-on-delete")
        response = self.sf.call(*args, cwd=project)
        remote_id = sfid(response.get("id"), "0Af")
        self.log("destructive-returned", remote_id=remote_id, intent_sha256=sha(intent.read_bytes()))
        self.destructive_terminal(remote_id)

    def verify_absence(self, classes, survivors, preserved):
        self.active_deployments()
        require(not self.active_jobs(classes), "OWNED_JOB_PRESENT_AFTER_TEARDOWN")
        final = self.inventory()
        self.checked_baseline(final, survivors)
        require(not any(self.scoped(name) or row["id"] in self.operator.legacy_ids
                        for rows in final.values() for name, row in rows.items()), "SCOPED_METADATA_REMAINS")
        self.no_scoped_entities()
        require(self.preserved() == preserved, "PRESERVED_RESOURCES_CHANGED")

    def hold_snapshot(self, *, quiesce=False, expected=None, allow_record_changes=False):
        self.verify_identity()
        deployment_evidence = attempt.deployment_evidence(self.state)
        submissions = attempt.submission_evidence(self.state)
        prelaunch = self.context.get("reconcile_prelaunch_noop") is True
        if prelaunch:
            require(hosted_binding.no_launch_without_reset(self.context), "RISKY_MISSING_RESET_PROOF")
            current, preserved = self.empty_inventory()
            intents, deployed, sources, owned = [], [], {}, {}
        else:
            intents, deployed, sources, current, owned, preserved = self.ownership(exact=True)
        classes = set(owned.get("ApexClass", {}).values())
        inventory = self.held_inventory(current, owned, sources)
        if expected is not None:
            if allow_record_changes:
                # Compare the sealed scope while clearing work against the current rows.
                require(inventory["records"].keys() == expected["records"].keys(), "RETAINED_INVENTORY_CHANGED")
                expected = dict(expected, records=inventory["records"])
            require(inventory == expected, "RETAINED_INVENTORY_CHANGED")
        if quiesce:
            self.quiesce(classes)
        else:
            require(not self.active_jobs(classes), "RETAINED_WORK_ACTIVE")
        url, app_work = self.app_work_clearance(inventory, deployed)
        self.verify_identity()
        self.active_deployments()
        if prelaunch:
            require(hosted_binding.no_launch_without_reset(self.context), "RISKY_MISSING_RESET_PROOF")
        require(not self.active_jobs(classes) and self.inventory() == current
                and self.held_inventory(current, owned, sources) == inventory and self.preserved() == preserved
                and attempt.deployment_evidence(self.state) == deployment_evidence
                and attempt.submission_evidence(self.state) == submissions,
                "RETENTION_CHECK_CHANGED")
        for link in deployed:
            key = link["intent_sha256"]
            require(all(link[name] == value for name, value in self.payload(key, read(self.state / f"{key}.intent")).items()),
                    "DEPLOYED_PAYLOAD_CHANGED")
        self.log("retained-inventory", inventory=inventory, preserved=preserved)
        return {"generation_id": self.state.name, "prefix": self.context["namespace"],
                "synthetic_label": self.context["synthetic_label"], "app_url": url,
                "reconciled_intents": intents, "deployments": deployed, "deployment_evidence": deployment_evidence,
                "inventory": inventory,
                "preserved": preserved, "app_work_clearance": app_work}, current, owned

    def recheck_retained(self, peer):
        state = hosted_binding.absolute(peer["state_dir"])
        require(state.parent == self.state.parent and attempt.retained(state)
                and not os.path.lexists(state / "retirement-started.json"), "RETAINED_GENERATION_UNVERIFIED")
        result = read(state / "retained.json")
        sealed = result["retention"]
        context = read(state / "start.json")
        require(result["retention_sha256"] == peer["retention_sha256"]
                and context["target"]["org_id"] == self.target["org_id"], "RETAINED_GENERATION_MISMATCH")
        check = Phase(self.operator, dict(context, reconcile_prelaunch_noop=sealed.get("prelaunch_noop") is True),
                      self.cutoff, "retained-recheck")
        require(attempt.local_clear(state, Path(context["output"]), stop=False), "RETAINED_LOCAL_PROCESS_PRESENT")
        snapshot, _, _ = check.hold_snapshot(expected=sealed["inventory"], allow_record_changes=True)
        require(all(snapshot[key] == sealed[key] for key in ("deployments", "preserved", "reconciled_intents"))
                and (sealed["app_url"] is None or snapshot["app_url"] == sealed["app_url"]),
                "RETAINED_GENERATION_CHANGED")
        receipt = check.receipt(verified=True, **snapshot)
        self.log("retained-generation-rechecked", **peer,
                 evidence={"path": str(check.journal / "receipt.json"), "sha256": sha(hosted_binding.encoded(receipt))})


def _run(operator, context, cutoff, phase, operation):
    run = Phase(operator, context, cutoff, phase)
    try:
        operator.check_phase(context, phase)
        return operation(run)
    except (Refusal, OSError, ValueError, TypeError, KeyError, IndexError, AttributeError,
            subprocess.TimeoutExpired) as exc:
        reason = str(exc) if isinstance(exc, Refusal) else type(exc).__name__
        return run.receipt(verified=False, status="UNKNOWN" if phase == "observe" else "RECONCILIATION_REQUIRED",
                           reason=reason)


def _reset(operator, context, cutoff):
    """Freeze the leased, currently empty namespace inventory."""
    def operation(run):
        run.verify_identity()
        peers = context.get("retained_generations", [])
        for peer in peers:
            run.recheck_retained(peer)
        inventory, preserved = run.empty_inventory()
        frozen = run.state / "operator-baseline.json"
        write(frozen, dict(run.bound("reset"), metadata=inventory, preserved=preserved))
        rechecked = {"retained_generations": peers} if context.get("review_hold") is True else {}
        return run.receipt(verified=True, empty_noop=True, baseline_path=str(frozen),
                           baseline_sha256=sha(frozen.read_bytes()), **rechecked)

    return _run(operator, context, cutoff, "reset", operation)


def _observe(operator, context, cutoff):
    """Wait for independently produced, attempt-bound observations while the app exists."""
    def operation(run):
        request = run.state / "observe-request.json"
        started = time.time()
        write(request, dict(context, phase="observe", checked_at=started, cutoff=cutoff))
        path = run.state / "observations.json"
        while not path.exists():
            run.pause()
        observation = read(path)
        require(run.linked(observation, "observe") and observation.get("verified") is True
                and started <= observation["checked_at"] <= min(time.time(), cutoff)
                and observation.get("status") in {"OBSERVED", "UNKNOWN"}, "OPERATOR_OBSERVATION_UNAVAILABLE")
        run.verify_identity()
        _, deployed, _, _ = run.deployments()
        require(deployed and observation.get("deployments") == deployed, "OBSERVATION_DEPLOYMENT_LINK_MISMATCH")
        routes = observation.get("routes")
        require(isinstance(routes, dict) and set(routes) == {"browser", "provider", "native", "records"},
                "OBSERVATION_ROUTE_UNAVAILABLE")
        safe = {}
        for name, reference in routes.items():
            safe[name] = {"status": "UNKNOWN"}
            if isinstance(reference, dict) and reference.get("status") == "OBSERVED":
                try:
                    safe[name] = run.evidence_ref(reference)
                except (Refusal, OSError, ValueError):
                    run.log("unverified-route", route=name)
        require(time.time() < cutoff, "PHASE_CUTOFF")
        observed = any("path" in ref for ref in safe.values())
        complete = observation["status"] == "OBSERVED" and all("path" in ref for ref in safe.values())
        return run.receipt(verified=observed, status="OBSERVED" if complete else "UNKNOWN",
                           deployments=deployed, routes=safe, product_acceptance="UNKNOWN")

    return _run(operator, context, cutoff, "observe", operation)


def _cleanup(operator, context, cutoff):
    """Settle all submissions and remove only resources attributed to this attempt."""
    require(not operator.binding.get("review_hold") and not context.get("review_hold"), "REVIEW_HOLD_ACTIVE")

    def operation(run):
        require(context.get("local_processes_clear") is True, "LOCAL_PROCESS_GROUPS_UNVERIFIED")
        if context.get("reconcile_prelaunch_noop") is True:
            require(hosted_binding.no_launch_without_reset(context), "RISKY_MISSING_RESET_PROOF")
            run.verify_identity()
            run.empty_inventory()
            require(hosted_binding.no_launch_without_reset(context), "RISKY_MISSING_RESET_PROOF")
            return run.receipt(verified=True, status="VERIFIED", reconciled_intents=[], empty_noop=True,
                               prelaunch_noop=True)
        run.verify_identity()
        prior = list(run.state.glob("operator-cleanup-*/*-destructive-submitted.json"))
        require(len(prior) <= 1, "AMBIGUOUS_DESTRUCTIVE_HISTORY")
        earlier = run.reconcile_destructive(prior[0]) if prior else None
        intents, _, _, current, owned, preserved = run.ownership()
        if earlier:
            require(not owned, "OWNED_COMPONENT_REMAINS_AFTER_DESTRUCTIVE")
            run.checked_baseline(current, earlier["survivors"])
        survivors = {kind: {name: row for name, row in rows.items() if name not in owned.get(kind, {})}
                     for kind, rows in current.items()}
        run.remove_assignments(set(owned.get("PermissionSet", {}).values()))
        try:
            result = read(run.state / "observations.json")
        except (Refusal, OSError, ValueError):
            result = {}
        if run.linked(result, "observe") and result.get("app_work_pending") is True:
            clear = read(run.state / "app-work-cleared.json")
            require(run.linked(clear, "cleanup") and clear.get("verified") is True, "APP_WORK_PENDING")
            run.log("app-work-cleared", evidence=run.evidence_ref(clear.get("evidence")))
        classes = set((earlier["members"] if earlier else owned).get("ApexClass", {}).values())
        run.quiesce(classes)
        if owned:
            scope = run.record_review(owned.get("CustomObject", {}))
            run.verify_identity()
            run.active_deployments()
            require(not run.active_jobs(classes) and run.inventory() == current
                    and all(sorted(sfid(row["Id"]) for row in run.sf.query("Id", name, all_rows=True)) == expected["ids"]
                            for name, expected in scope.items()), "TEARDOWN_INVENTORY_CHANGED")
            run.require_no_assignments(owned.get("PermissionSet", {}).values())
            run.destructive_deploy(owned, survivors)
        run.verify_absence(classes, survivors, preserved)
        return run.receipt(verified=True, status="VERIFIED", reconciled_intents=intents, empty_noop=not (owned or earlier))

    return _run(operator, context, cutoff, "cleanup", operation)


def _retain(operator, context, cutoff):
    def operation(run):
        require(context.get("review_hold") is True and context.get("local_processes_clear") is True
                and not os.path.lexists(run.state / "retirement-started.json"), "RETENTION_CONTEXT_UNVERIFIED")
        prelaunch = context.get("reconcile_prelaunch_noop") is True
        reset = None if prelaunch else {"reset": artifact(run.state / "reset.json"),
                                        "baseline": artifact(run.state / "operator-baseline.json")}
        # Only the original executing attempt may stop attributable builder jobs.
        snapshot, _, _ = run.hold_snapshot(quiesce=context.get("retention_quiesce_jobs") is True and not prelaunch)
        return run.receipt(verified=True, prelaunch_noop=prelaunch, reset_evidence=reset, **snapshot)

    return _run(operator, context, cutoff, "retain", operation)


def retirement_base(run):
    require(run.context.get("review_hold") is True and run.context.get("local_processes_clear") is True
            and attempt.retained(run.state), "RETAINED_GENERATION_UNVERIFIED")
    result = read(run.state / "retained.json")
    sealed = result["retention"]
    for peer in attempt.prior_states(run.operator.binding):
        if peer == run.state or attempt.reusable(peer):
            continue
        require(attempt.retained(peer) and not os.path.lexists(peer / "retirement-started.json"),
                "OTHER_GENERATION_UNRESOLVED")
        path = peer / "operator-baseline.json"
        if read(peer / "retained.json")["retention"].get("prelaunch_noop") is True:
            continue
        baseline = read(path)
        proof = read(peer / "reset.json")
        require(sha(path.read_bytes()) == proof["baseline_sha256"], "PEER_BASELINE_UNVERIFIED")
        require(not any(name in baseline["metadata"].get(kind, {})
                        for kind, rows in sealed["inventory"]["metadata"].items() for name in rows),
                "RETIRE_DEPENDENT_GENERATION_FIRST")
    run.context = dict(run.context, reconcile_prelaunch_noop=sealed.get("prelaunch_noop") is True)
    return result


def _plan_retirement(operator, context, cutoff):
    def operation(run):
        require(not os.path.lexists(run.state / "retirement-started.json"), "RETIREMENT_ALREADY_STARTED")
        result = retirement_base(run)
        snapshot, _, _ = run.hold_snapshot()
        sealed = result["retention"]
        require(all(snapshot[key] == sealed[key] for key in ("deployments", "preserved", "reconciled_intents"))
                and all(snapshot["inventory"][key] == sealed["inventory"][key]
                        for key in ("metadata", "component_sources", "assignments")), "RETAINED_ASSETS_CHANGED")
        pin = run.state / "operator-config.json"
        if not os.path.lexists(pin):
            # Reset was interrupted before pinning. Bind this positively checked plan to the
            # exact operator config so that retirement must supply the same authorized bytes.
            write(pin, {"config_sha256": operator.config_sha256, "binding_sha256": operator.binding_sha256})
        return run.receipt(verified=True, retention_sha256=result["retention_sha256"], cutoff=cutoff, **snapshot)

    return _run(operator, context, cutoff, "retirement-plan", operation)


def retirement_approval(run, retention_sha256):
    path = run.operator.external_path(run.context["retirement_approval"])
    digest = run.context["retirement_approval_sha256"]
    require(path.is_file() and not path.is_relative_to(run.state) and matches(DIGEST, digest),
            "RETIREMENT_APPROVAL_UNVERIFIED")
    raw = path.read_bytes()
    approval = strict_json(raw)
    hosted_binding.fields(approval, "schema approved generation_id plan_sha256 evidence")
    require(sha(raw) == digest and approval["schema"] == "hosted-outcome-retirement-approval/1"
            and approval["approved"] is True and approval["generation_id"] == run.state.name
            and matches(DIGEST, approval["plan_sha256"]), "RETIREMENT_APPROVAL_UNVERIFIED")
    evidence = run.evidence_ref(approval["evidence"])
    require(not Path(evidence["path"]).is_relative_to(run.state) and evidence["path"] != str(path),
            "RETIREMENT_REVIEW_NOT_INDEPENDENT")
    plans = [candidate for candidate in run.state.glob("operator-retirement-plan-*/receipt.json")
             if sha(candidate.read_bytes()) == approval["plan_sha256"]]
    require(len(plans) == 1, "RETIREMENT_PLAN_UNVERIFIED")
    plan = read(plans[0])
    require(run.linked(plan, "retirement-plan") and plan.get("verified") is True
            and plan["generation_id"] == run.state.name and plan["retention_sha256"] == retention_sha256,
            "RETIREMENT_PLAN_UNVERIFIED")
    return plan, {"generation_id": run.state.name, "approval_sha256": digest, "approval_path": str(path),
                  "plan_sha256": approval["plan_sha256"], "retention_sha256": retention_sha256, "evidence": evidence}


def _retire(operator, context, cutoff):
    def operation(run):
        result = retirement_base(run)
        plan, approved = retirement_approval(run, result["retention_sha256"])
        started = run.state / "retirement-started.json"
        metadata = plan["inventory"]["metadata"]
        classes = {row["id"] for row in metadata.get("ApexClass", {}).values()}
        permsets = {row["id"] for row in metadata.get("PermissionSet", {}).values()}
        prelaunch = run.context.get("reconcile_prelaunch_noop") is True
        resuming = os.path.lexists(started)
        if resuming:
            require(read(started) == approved, "ORIGINAL_RETIREMENT_APPROVAL_REQUIRED")
            if prelaunch:
                require(not any(run.state.glob("operator-retire-*/*-destructive-submitted.json")),
                        "RETIREMENT_EFFECTS_UNRESOLVED")
        if resuming and not prelaunch:
            prior = list(run.state.glob("operator-retire-*/*-destructive-submitted.json"))
            require(len(prior) == 1, "RETIREMENT_EFFECTS_UNRESOLVED")
            run.verify_identity()
            earlier = run.reconcile_destructive(prior[0])
            require(earlier["members"] == {kind: {name: row["id"] for name, row in rows.items()}
                                           for kind, rows in metadata.items() if kind in TYPES},
                    "RETIREMENT_MEMBERS_CHANGED")
            run.require_no_assignments(permsets)
            run.checked_baseline(earlier["survivors"], run.baseline()["metadata"])
            run.verify_absence(classes, earlier["survivors"], plan["preserved"])
        else:
            plan_cutoff = cutoff if resuming else min(cutoff, plan["cutoff"])
            require(time.time() < plan_cutoff, "RETIREMENT_PLAN_EXPIRED")
            snapshot, current, owned = run.hold_snapshot(expected=plan["inventory"])
            require(all(snapshot[key] == plan[key] for key in ("deployments", "preserved", "reconciled_intents"))
                    and time.time() < plan_cutoff, "RETIREMENT_PLAN_CHANGED")
            survivors = {kind: {name: row for name, row in rows.items() if name not in owned.get(kind, {})}
                         for kind, rows in current.items()}
            if not resuming:
                write(started, approved)
            if not prelaunch:
                run.remove_assignments(permsets, expected=plan["inventory"]["assignments"])
                if owned:
                    run.destructive_deploy(owned, survivors)
            run.verify_absence(classes, survivors, plan["preserved"])
        return run.receipt(verified=True, status="VERIFIED", reconciled_intents=plan["reconciled_intents"],
                           empty_noop=not metadata, retirement=approved)

    return _run(operator, context, cutoff, "retire", operation)
