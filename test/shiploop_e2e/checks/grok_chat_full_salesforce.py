#!/usr/bin/env python3
"""Independent check-only Apex oracle for the full Grok chat acceptance case."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import uuid

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("grok_chat_full_lifecycle", HERE / "gym_membership_salesforce.py")
gym = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gym)
sfc = gym.sfc

ORG = "de"
PREFIX = "SLGrokChat"
EXPECTED_ORG_ID = "00Daj000018BzO3EAK"
ORACLE_CLASS = PREFIX + "OracleTest"
ORACLE_RULE = PREFIX + "OracleDmlFault"
ITEM_OBJECT = PREFIX + "Item__c"
CONFIG_OBJECT = PREFIX + "Config__c"
MODEL = "grok-4.7"
NAMED_CREDENTIAL = "Grok_Chat_Model"
ORACLE = HERE.parent / "fixtures" / "grok-chat-full-oracle"
ORACLE_ATTEMPT_LEDGER = "attempts.log"
ORACLE_CLASS_SOURCE = ORACLE / "force-app/main/default/classes" / (ORACLE_CLASS + ".cls")
ORACLE_CLASS_META = ORACLE / "force-app/main/default/classes" / (ORACLE_CLASS + ".cls-meta.xml")
ORACLE_RULE_SOURCE = (ORACLE / "force-app/main/default/objects" / ITEM_OBJECT /
                      "validationRules" / (ORACLE_RULE + ".validationRule-meta.xml"))
ORACLE_PROJECT = ORACLE / "sfdx-project.json"
CONTROLLER = PREFIX + "Controller"
CONTROLLER_SOURCE = Path("force-app/main/default/classes") / (CONTROLLER + ".cls")
RULE_RELATIVE = Path("force-app/main/default/objects") / ITEM_OBJECT / "validationRules" / (
    ORACLE_RULE + ".validationRule-meta.xml")
REQUIRED_METHODS = frozenset({
    "adminSavePersistsNonsecretConfiguration",
    "ordinaryUserCannotSaveConfiguration",
    "testConnectionUsesResponsesApiNamedCredential",
    "provider401IsRecoverable",
    "provider429IsRecoverable",
    "provider503IsRecoverable",
    "newConversationIsOwnedAndHistorySurvivesReload",
    "foreignUserCannotReadOrMutateConversation",
    "onlyDeclaredStructuredToolsAreRegistered",
    "nonceReadReturnsScopedResultToProvider",
    "createProposalAndConfirmUseExactStoredValues",
    "updateProposalUsesExactStoredOldAndNewValues",
    "cancelAndRepeatedCancelNeverWriteItem",
    "duplicateConfirmReplayDoesNotWriteTwice",
    "staleItemCannotBeConfirmedWithOldProposal",
    "contextAndSchemaResultsAreReturnedToProvider",
    "findItemsReturnsOnlyOwnedSyntheticItems",
    "malformedArgumentsAreRejected",
    "wronglyTypedArgumentsAreRejected",
    "unknownToolsAreRejected",
    "forbiddenObjectAndFieldArgumentsAreRejected",
    "recordTextCannotExpandToolAuthority",
    "crudAndFlsDenialsDoNotExposeRecords",
    "failedWriteLeavesNoPartialBusinessMutation",
    "demoSeedingIsSyntheticAndRepeatable",
})
INTERFACE = {
    "getSetup": (),
    "saveSetup": ("String namedCredential", "String model"),
    "testConnection": (),
    "newConversation": (),
    "getConversation": ("String conversationId",),
    "sendMessage": ("String conversationId", "String message"),
    "confirmAction": ("String actionId",),
    "cancelAction": ("String actionId",),
    "seedItems": (),
}


def _mask_apex(source: str) -> str:
    """Replace comments and literals before checking signatures so comments cannot satisfy the contract."""
    chars = list(source)
    i = 0
    while i < len(chars):
        if chars[i] == "/" and i + 1 < len(chars) and chars[i + 1] == "/":
            end = i
            while end < len(chars) and chars[end] not in "\r\n":
                end += 1
            for j in range(i, end):
                chars[j] = " "
            i = end
            continue
        if chars[i] == "/" and i + 1 < len(chars) and chars[i + 1] == "*":
            end = i + 2
            while end + 1 < len(chars) and not (chars[end] == "*" and chars[end + 1] == "/"):
                end += 1
            end = min(len(chars), end + 2)
            for j in range(i, end):
                if chars[j] not in "\r\n":
                    chars[j] = " "
            i = end
            continue
        if chars[i] in ("'", '"'):
            quote = chars[i]
            chars[i] = " "
            i += 1
            while i < len(chars):
                if chars[i] == "\\":
                    chars[i] = " "
                    if i + 1 < len(chars):
                        if chars[i + 1] not in "\r\n":
                            chars[i + 1] = " "
                        i += 2
                        continue
                if chars[i] == quote:
                    chars[i] = " "
                    if i + 1 < len(chars) and chars[i + 1] == quote:
                        chars[i + 1] = " "
                        i += 2
                        continue
                    i += 1
                    break
                if chars[i] not in "\r\n":
                    chars[i] = " "
                i += 1
            continue
        i += 1
    return "".join(chars)


def _normalise_apex(source: str) -> str:
    return source.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff").rstrip()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def source_tree_sha256(root: Path) -> str:
    app = root / "force-app"
    if not app.is_dir():
        raise sfc.SfError("candidate force-app source is missing")
    digest = hashlib.sha256()
    files = [root / "sfdx-project.json"]
    ignore = root / ".forceignore"
    if ignore.exists():
        files.append(ignore)
    for path in app.rglob("*"):
        if path.is_symlink():
            raise sfc.SfError("candidate source contains a symlink")
        if path.is_file():
            files.append(path)
    for path in sorted(files):
        if path.is_symlink() or not path.is_file():
            raise sfc.SfError("candidate project source/configuration is missing or a symlink")
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def prefix_apex_sha256(root: Path, prefix: str = PREFIX) -> dict[str, str]:
    files = sorted(path for path in (root / "force-app").rglob("*.cls") if path.is_file())
    if not files:
        raise sfc.SfError("candidate contains no Apex class sources")
    result = {}
    for path in files:
        name = path.stem
        if not name.startswith(prefix):
            raise sfc.SfError("candidate Apex class is outside the case prefix")
        if name in result:
            raise sfc.SfError("candidate has duplicate Apex class names")
        result[name] = _sha(_normalise_apex(path.read_text(encoding="utf-8")))
    return dict(sorted(result.items()))


def oracle_method_names(source: str) -> set[str]:
    masked = _mask_apex(source)
    return set(re.findall(r"@isTest\s+static\s+void\s+([A-Za-z]\w*)\s*\(", masked, re.IGNORECASE))


def _field(root: Path, object_name: str, field_name: str) -> dict | None:
    path = root / "force-app/main/default/objects" / object_name / "fields" / (field_name + ".field-meta.xml")
    if not path.is_file():
        return None
    return gym.xml(path)


def _object_meta(root: Path, object_name: str) -> dict | None:
    path = root / "force-app/main/default/objects" / object_name / (object_name + ".object-meta.xml")
    if not path.is_file():
        return None
    return gym.xml(path)


def source_problems(prefix: str = PREFIX, root: Path = Path(".")) -> list[str]:
    problems = []
    app = root / "force-app/main/default"
    controller = app / "classes" / (prefix + "Controller.cls")
    try:
        project = json.loads((root / "sfdx-project.json").read_text(encoding="utf-8"))
        package_directories = project.get("packageDirectories") if isinstance(project, dict) else None
        if (not isinstance(package_directories, list) or len(package_directories) != 1
                or not isinstance(package_directories[0], dict)
                or package_directories[0].get("path") != "force-app"):
            problems.append("sfdx-project.json must declare only the force-app package directory")
        if not controller.is_file():
            return ["missing public controller source " + controller.as_posix()]
        for path in (root / "force-app").rglob("*.cls"):
            if not path.stem.startswith(prefix):
                problems.append("Apex class is outside the case prefix: " + path.name)
        source = controller.read_text(encoding="utf-8")
        masked = _mask_apex(source)
        if not re.search(r"\bclass\s+" + re.escape(prefix + "Controller") + r"\b", masked, re.IGNORECASE):
            problems.append("controller class declaration is missing")
        for name, parameters in INTERFACE.items():
            pattern = (r"@AuraEnabled\s*(?:\([^)]*\)\s*)?public\s+static\s+String\s+" +
                       re.escape(name) + r"\s*\(([^)]*)\)")
            matches = re.findall(pattern, masked, re.IGNORECASE)
            expected = tuple(" ".join(param.split()).lower() for param in parameters)
            actual = []
            for match in matches:
                actual.append(tuple(" ".join(part.split()).lower() for part in match.split(",") if part.strip()))
            if len(matches) != 1 or actual != [expected]:
                problems.append(name + " must expose one @AuraEnabled public static String method with the declared parameters")

        item_meta = _object_meta(root, prefix + "Item__c")
        config_meta = _object_meta(root, prefix + "Config__c")
        if item_meta is None:
            problems.append("missing declared work-item object")
        elif gym.one(gym.one(item_meta, "nameField", {}), "type") != "Text":
            problems.append("work-item Name must be editable Text")
        if config_meta is None:
            problems.append("missing declared setup-config object")
        for object_name, expected in (
            (prefix + "Item__c", {"Status__c": ("Picklist",), "Notes__c": ("Text", "TextArea", "LongTextArea")}),
            (prefix + "Config__c", {"NamedCredential__c": ("Text",), "Model__c": ("Text",)}),
        ):
            for field_name, types in expected.items():
                field = _field(root, object_name, field_name)
                if field is None:
                    problems.append(object_name + "." + field_name + " is missing")
                    continue
                if gym.one(field, "fullName") != field_name or gym.one(field, "type") not in types:
                    problems.append(object_name + "." + field_name + " has the wrong declared type")
                if field_name == "Status__c":
                    values = gym.one(gym.one(field, "valueSet", {}), "valueSetDefinition", {})
                    declared = {gym.one(value, "fullName") for value in values.get("value", [])}
                    if gym.one(gym.one(field, "valueSet", {}), "restricted") != "true" or declared != {"Open", "Done"}:
                        problems.append("work-item Status__c must be a restricted Open/Done picklist")

        for path in app.rglob("*.cls"):
            if path.is_file() and path != controller:
                other = _mask_apex(path.read_text(encoding="utf-8"))
                if re.search(r"\bclass\s+" + re.escape(prefix + "OracleTest") + r"\b", other, re.IGNORECASE):
                    problems.append("reserved independent oracle class must not be app product code")
        reserved_class = app / "classes" / (prefix + "OracleTest.cls")
        if reserved_class.exists():
            problems.append("reserved independent oracle class must not be app product code")
        reserved_rule = app / "objects" / (prefix + "Item__c") / "validationRules" / (
            prefix + "OracleDmlFault.validationRule-meta.xml")
        if reserved_rule.exists():
            problems.append("reserved check-only DML fault rule must not be app product code")
    except (OSError, ValueError, TypeError, AttributeError, SyntaxError) as exc:
        problems.append("candidate source/layout unreadable: " + sfc.tail(str(exc), 200))
    return problems


def do_project(prefix: str = PREFIX, root: Path = Path(".")) -> tuple[bool, str]:
    problems = source_problems(prefix, root)
    if problems:
        return False, "; ".join(problems)
    try:
        candidate = source_tree_sha256(root)
        controller = (root / CONTROLLER_SOURCE).read_text(encoding="utf-8")
    except (OSError, sfc.SfError) as exc:
        return False, "candidate source/layout unreadable: " + sfc.tail(str(exc), 200)
    return True, "candidate contract satisfied; controller_sha256=%s; candidate_sha256=%s" % (
        _sha(_normalise_apex(controller)), candidate)


def deployed_prefix_apex_sha256(org: str, prefix: str, expected_names: set[str]) -> dict[str, str]:
    query = "SELECT Name, Body FROM ApexClass WHERE Name LIKE '%s%%'" % prefix
    rows = sfc.records(org, query, tooling=True)
    matching = [row for row in rows if isinstance(row.get("Name"), str)
                and row["Name"].lower().startswith(prefix.lower())]
    if any(not row["Name"].startswith(prefix) for row in matching):
        raise sfc.SfError("deployed Apex contains a case-variant prefix collision")
    names = [row["Name"] for row in matching]
    if len(names) != len(set(names)) or set(names) != expected_names:
        raise sfc.SfError("deployed prefix Apex class names do not exactly match candidate source")
    result = {}
    for row in matching:
        body = row.get("Body")
        if not isinstance(body, str):
            raise sfc.SfError("deployed Apex body is unavailable for " + row["Name"])
        result[row["Name"]] = _sha(_normalise_apex(body))
    return dict(sorted(result.items()))


def reserved_components(org: str = ORG) -> dict[str, bool]:
    classes = sfc.records(org, "SELECT Name FROM ApexClass WHERE Name = '%s'" % ORACLE_CLASS, tooling=True)
    rules = sfc.records(org, "SELECT ValidationName FROM ValidationRule WHERE ValidationName = '%s'" % ORACLE_RULE,
                        tooling=True)
    return {
        "class": any(row.get("Name") == ORACLE_CLASS for row in classes),
        "rule": any(row.get("ValidationName") == ORACLE_RULE for row in rules),
    }


def validation_observation(doc: object, expected_methods: set[str], oracle_class: str) -> dict:
    result = doc.get("result") if isinstance(doc, dict) else None
    details = result.get("details") if isinstance(result, dict) else None
    run = details.get("runTestResult") if isinstance(details, dict) else None
    successes = run.get("successes") if isinstance(run, dict) else None
    failures = run.get("failures") if isinstance(run, dict) else None
    observed = set()
    if isinstance(successes, list):
        observed = {
            row.get("methodName") for row in successes
            if isinstance(row, dict) and row.get("name") == oracle_class and isinstance(row.get("methodName"), str)
        }
    return {
        "status": doc.get("status") if isinstance(doc, dict) else None,
        "result_success": result.get("success") if isinstance(result, dict) else None,
        "num_tests_run": run.get("numTestsRun") if isinstance(run, dict) else None,
        "num_failures": run.get("numFailures") if isinstance(run, dict) else None,
        "successes_present": isinstance(successes, list),
        "failures_present": isinstance(failures, list),
        "success_count": len(successes) if isinstance(successes, list) else None,
        "failure_count": len(failures) if isinstance(failures, list) else None,
        "expected_count": len(expected_methods),
        "passed_methods": sorted(observed & expected_methods),
        "missing_methods": sorted(expected_methods - observed),
    }


def validation_verdict(doc: object, expected_methods: set[str], oracle_class: str = ORACLE_CLASS) -> tuple[bool, str]:
    observation = validation_observation(doc, expected_methods, oracle_class)
    run = None
    if isinstance(doc, dict):
        result = doc.get("result")
        details = result.get("details") if isinstance(result, dict) else None
        run = details.get("runTestResult") if isinstance(details, dict) else None
    def valid_count(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0
    ok = (
        bool(expected_methods)
        and isinstance(doc, dict)
        and type(observation["status"]) is int and observation["status"] == 0
        and observation["result_success"] is True
        and isinstance(run, dict)
        and observation["successes_present"] and observation["failures_present"]
        and valid_count(observation["num_tests_run"])
        and valid_count(observation["num_failures"])
        and observation["num_tests_run"] >= len(expected_methods)
        and observation["num_tests_run"] == observation["success_count"] + observation["failure_count"]
        and observation["num_failures"] == observation["failure_count"] == 0
        and not observation["missing_methods"]
    )
    summary = ("PASS" if ok else "FAIL/UNKNOWN") + (
        " check-only oracle: %d/%d named methods, %s failures, %s tests run" % (
            len(observation["passed_methods"]), len(expected_methods),
            observation["num_failures"] if observation["num_failures"] is not None else "missing",
            observation["num_tests_run"] if observation["num_tests_run"] is not None else "missing",
        )
    )
    return ok, summary


def fixture_problems() -> list[str]:
    problems = []
    try:
        if not ORACLE_PROJECT.is_file() or not ORACLE_CLASS_SOURCE.is_file() or not ORACLE_CLASS_META.is_file():
            return ["oracle project/class fixture is incomplete"]
        if not ORACLE_RULE_SOURCE.is_file():
            return ["check-only DML fault ValidationRule fixture is missing"]
        class_files = sorted(ORACLE.glob("force-app/**/classes/*.cls"))
        rule_files = sorted(ORACLE.glob("force-app/**/validationRules/*.validationRule-meta.xml"))
        if class_files != [ORACLE_CLASS_SOURCE] or rule_files != [ORACLE_RULE_SOURCE]:
            problems.append("oracle fixture must contain only the reserved test class and DML fault rule")
        expected_files = {
            ORACLE_CLASS_SOURCE,
            ORACLE_CLASS_META,
            ORACLE_RULE_SOURCE,
        }
        actual_files = {path for path in (ORACLE / "force-app").rglob("*") if path.is_file()}
        if actual_files != expected_files:
            problems.append("oracle deploy source contains files outside the reserved class and fault rule")
        class_source = ORACLE_CLASS_SOURCE.read_text(encoding="utf-8")
        methods = oracle_method_names(class_source)
        if not REQUIRED_METHODS <= methods:
            problems.append("oracle fixture is missing named required tests: " +
                            ", ".join(sorted(REQUIRED_METHODS - methods)))
        if len(methods) < len(REQUIRED_METHODS):
            problems.append("oracle fixture declares fewer test methods than the named required count")
        masked = _mask_apex(class_source)
        if re.search(r"\bSeeAllData\s*=\s*true", masked, re.IGNORECASE):
            problems.append("oracle tests must use isolated test data")
        rule = gym.xml(ORACLE_RULE_SOURCE)
        if (gym.one(rule, "fullName") != ORACLE_RULE or gym.one(rule, "active") != "true"
                or gym.one(rule, "errorConditionFormula") != 'BEGINS(Name, "E2E-OracleDmlFailure-")'):
            problems.append("check-only DML fault rule is not scoped to reserved failure names")
    except (OSError, ValueError, TypeError, AttributeError, SyntaxError) as exc:
        problems.append("oracle fixture unreadable: " + sfc.tail(str(exc), 200))
    return problems


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(json.dumps(sfc.scrub(value), indent=2) + "\n", encoding="utf-8")


def register_oracle_attempt(directory: Path, phase: str, check_id: str) -> Path:
    """Record start order so a later failed or interrupted oracle supersedes earlier proof."""
    attempts = directory / "grok-chat-full-oracle" / phase
    attempts.mkdir(parents=True, mode=0o700, exist_ok=True)
    artifact = attempts / check_id
    with (attempts / ORACLE_ATTEMPT_LEDGER).open("a", encoding="ascii") as ledger:
        fcntl.flock(ledger, fcntl.LOCK_EX)
        if artifact.exists():
            raise FileExistsError(artifact)
        ledger.write(check_id + "\n")
        ledger.flush()
        artifact.mkdir(mode=0o700)
    return artifact


def do_rules(directory: Path | None = None, root: Path = Path(".")) -> tuple[bool, str]:
    phase = os.environ.get("E2E_CHECK_PHASE")
    if phase not in {"builder", "final"}:
        return False, "UNKNOWN: the independent Apex oracle runs only in builder or final phase"
    directory = Path(directory) if directory is not None else sfc.platform_dir()
    # Register before any source or remote fallible work: a newer failed or
    # interrupted invocation must supersede an earlier passing receipt.
    artifact = register_oracle_attempt(directory, phase, uuid.uuid4().hex)
    ok, message = do_project(PREFIX, root)
    if not ok:
        return False, "FAIL/UNKNOWN: candidate source check failed: " + message
    problems = fixture_problems()
    if problems:
        return False, "FAIL/UNKNOWN: independent oracle fixture failed: " + "; ".join(problems)

    candidate_sha = source_tree_sha256(root)
    candidate_apex = prefix_apex_sha256(root, PREFIX)
    candidate_controller_sha = candidate_apex.get(CONTROLLER)
    if candidate_controller_sha is None:
        return False, "UNKNOWN: candidate controller is not in the prefix Apex source set"
    class_source = ORACLE_CLASS_SOURCE.read_text(encoding="utf-8")
    expected_methods = oracle_method_names(class_source)
    if not REQUIRED_METHODS <= expected_methods or len(expected_methods) < len(REQUIRED_METHODS):
        return False, "UNKNOWN: oracle fixture is below its named required method count"

    try:
        identity_before = gym.identity(ORG)
        if identity_before != {
            "Id": EXPECTED_ORG_ID,
            "OrganizationType": "Developer Edition",
            "IsSandbox": False,
        }:
            raise sfc.SfError("live org identity/type mismatch")
        reserved_before = reserved_components(ORG)
        if any(reserved_before.values()):
            raise sfc.SfError("reserved oracle class or validation rule already exists; refusing collision")
        remote_apex_before = deployed_prefix_apex_sha256(ORG, PREFIX, set(candidate_apex))
        if remote_apex_before != candidate_apex:
            raise sfc.SfError("deployed prefix Apex source does not exactly match the candidate")
    except (sfc.SfError, OSError, ValueError, TypeError, KeyError) as exc:
        return False, "FAIL/UNKNOWN: pre-validation identity/source/collision check failed: " + sfc.tail(str(exc), 300)

    doc = None
    cli_error = None
    with tempfile.TemporaryDirectory(prefix="grok-chat-oracle-") as temporary:
        work = Path(temporary)
        shutil.copyfile(ORACLE_PROJECT, work / "sfdx-project.json")
        shutil.copytree(ORACLE / "force-app", work / "force-app")
        class_files = sorted((work / "force-app").rglob("*.cls"))
        rule_files = sorted((work / "force-app").rglob("*.validationRule-meta.xml"))
        if class_files != [work / "force-app/main/default/classes" / (ORACLE_CLASS + ".cls")] or \
                rule_files != [work / "force-app/main/default/objects" / ITEM_OBJECT / "validationRules" /
                               (ORACLE_RULE + ".validationRule-meta.xml")]:
            return False, "FAIL/UNKNOWN: temporary validation source exceeded reserved oracle scope"
        try:
            doc = sfc.sf([
                "project", "deploy", "validate", "--source-dir", str(work / "force-app"),
                "--test-level", "RunSpecifiedTests", "--tests", ORACLE_CLASS, "--wait", "10",
            ], ORG, timeout=900, cwd=str(work))
        except (sfc.SfError, OSError, ValueError, TypeError) as exc:
            cli_error = sfc.tail(str(exc), 300)

    post_problems = []
    identity_after = None
    remote_apex_after = None
    reserved_after = None
    try:
        identity_after = gym.identity(ORG)
        if identity_after != identity_before:
            post_problems.append("actual target org identity changed during check-only validation")
    except (sfc.SfError, OSError, ValueError, TypeError, KeyError) as exc:
        post_problems.append("post-validation org identity unavailable: " + sfc.tail(str(exc), 200))
    try:
        remote_apex_after = deployed_prefix_apex_sha256(ORG, PREFIX, set(candidate_apex))
        if remote_apex_after != candidate_apex:
            post_problems.append("deployed prefix Apex no longer matches candidate source after validation")
    except (sfc.SfError, OSError, ValueError, TypeError) as exc:
        post_problems.append("post-validation prefix Apex inventory unavailable: " + sfc.tail(str(exc), 200))
    try:
        reserved_after = reserved_components(ORG)
        if any(reserved_after.values()):
            post_problems.append("oracle class or validation rule persisted after check-only validation")
    except (sfc.SfError, OSError, ValueError, TypeError) as exc:
        post_problems.append("post-validation reserved-component inventory unavailable: " + sfc.tail(str(exc), 200))
    try:
        if source_tree_sha256(root) != candidate_sha:
            post_problems.append("candidate source changed during check-only validation")
        if prefix_apex_sha256(root, PREFIX) != candidate_apex:
            post_problems.append("candidate prefix Apex source changed during check-only validation")
    except (sfc.SfError, OSError, ValueError) as exc:
        post_problems.append("post-validation candidate source unavailable: " + sfc.tail(str(exc), 200))

    verdict, summary = validation_verdict(doc, expected_methods, ORACLE_CLASS)
    if cli_error:
        verdict = False
        summary = "FAIL/UNKNOWN: check-only deploy validate did not complete: " + cli_error
    ok = verdict and not post_problems
    evidence = validation_observation(doc, expected_methods, ORACLE_CLASS)
    receipt = {
        "schema": "shiploop-grok-chat-full-oracle/1",
        "phase": phase,
        "org": ORG,
        "org_id": EXPECTED_ORG_ID,
        "identity_before": identity_before,
        "identity_after": identity_after,
        "candidate_sha256": candidate_sha,
        "candidate_controller_sha256": candidate_controller_sha,
        "candidate_prefix_apex_sha256": candidate_apex,
        "deployed_prefix_apex_sha256_before": remote_apex_before,
        "deployed_prefix_apex_sha256_after": remote_apex_after,
        "oracle_class": ORACLE_CLASS,
        "oracle_sha256": _sha(class_source),
        "validation_rule": ORACLE_RULE,
        "validation_rule_sha256": _sha(ORACLE_RULE_SOURCE.read_text(encoding="utf-8")),
        "required_method_count": len(REQUIRED_METHODS),
        "expected_methods": sorted(expected_methods),
        "validation": evidence,
        "check_only": True,
        "binding_scope": "all prefix Apex class names and bodies are compared to the candidate; force-app and project config are hashed locally; metadata and LWC are not retrieved here",
        "reserved_before": reserved_before,
        "reserved_after": reserved_after,
        "post_validation_problems": post_problems,
        "complete": ok,
    }
    _write_json(artifact / "validation.json", doc if doc is not None else {"error": cli_error})
    _write_json(artifact / "receipt.json", receipt)
    if post_problems:
        summary += "; " + "; ".join(post_problems)
    return ok, summary + "; receipt=" + str((artifact / "receipt.json").relative_to(Path(directory)))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("project", "rules"))
    args = parser.parse_args(argv)
    try:
        if args.action == "project":
            ok, message = do_project(PREFIX)
        elif args.action == "rules":
            ok, message = do_rules()
        else:
            raise sfc.SfError("unsupported full Grok chat checker action")
        sfc.say(message)
        return 0 if ok else 1
    except (sfc.SfError, OSError, ValueError, KeyError, TypeError) as exc:
        sfc.say("FAIL/UNKNOWN: " + sfc.tail(str(exc), 300), stream=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
