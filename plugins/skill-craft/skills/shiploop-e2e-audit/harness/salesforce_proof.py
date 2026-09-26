"""Pure, offline validation for Salesforce Lightning evaluation evidence.

This module validates normalized, retained proof records.  It never invokes
Salesforce, opens a browser, reads credentials, or makes a deployment.  The
composite verifier supplies already-pinned JSON artifacts from an independent
review and uses these helpers to keep Salesforce evidence distinct from the
Google Apps Script receipt schema.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
from typing import Any, Mapping
from urllib.parse import urlparse


TARGET_PREFLIGHT_SCHEMA = "shiploop-e2e-salesforce-target-preflight/1"
DEPLOYMENT_OBSERVATION_SCHEMA = "shiploop-e2e-salesforce-deployment-observation/1"
DEPLOYMENT_RECEIPT_SCHEMA = "shiploop-e2e-salesforce-dx-receipt/1"
SOURCE_MAPPING_SCHEMA = "shiploop-e2e-salesforce-source-candidate-mapping/1"
HOSTED_OBSERVATION_SCHEMA = "shiploop-e2e-salesforce-hosted-lightning-observation/1"
LIGHTNING_BROWSER_TRACE_SCHEMA = "shiploop-e2e-salesforce-lightning-browser-trace/1"

_ORG_ID = re.compile(r"00D[A-Za-z0-9]{12}(?:[A-Za-z0-9]{3})?\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_COMPONENT_KINDS = frozenset((
    "lightning-app",
    "lightning-web-component",
    "apex-class",
    "custom-application",
    "metadata",
))
_LIGHTNING_COMPONENT_KINDS = frozenset(("lightning-app", "lightning-web-component"))
_MY_DOMAIN = re.compile(r"[A-Za-z0-9-]+\Z")


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _valid_digest(value: Any) -> bool:
    return isinstance(value, str) and _DIGEST.fullmatch(value.lower()) is not None


def _valid_org_id(value: Any) -> bool:
    return isinstance(value, str) and _ORG_ID.fullmatch(value) is not None


def _valid_relative_path(value: Any) -> bool:
    if not _nonempty_string(value):
        return False
    path = Path(str(value))
    return not path.is_absolute() and ".." not in path.parts and path != Path(".")


def instance_url_errors(value: Any, *, label: str = "salesforce-instance-url") -> list[str]:
    """Return errors unless ``value`` is an HTTPS Salesforce instance root."""
    if not _nonempty_string(value):
        return [f"{label}-invalid"]
    try:
        parsed = urlparse(str(value))
        port = parsed.port
    except ValueError:
        return [f"{label}-invalid"]
    hostname = parsed.hostname
    if (
        parsed.scheme != "https"
        or not hostname
        or not hostname.lower().endswith(".salesforce.com")
        or port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        return [f"{label}-invalid"]
    return []


def _derived_lightning_host(instance_url: Any) -> str | None:
    """Derive the normal Lightning host for a My Domain instance URL."""
    if instance_url_errors(instance_url):
        return None
    try:
        hostname = urlparse(str(instance_url)).hostname
    except ValueError:
        return None
    if hostname is None:
        return None
    suffix = ".my.salesforce.com"
    normalized = hostname.lower()
    if not normalized.endswith(suffix):
        return None
    prefix = normalized[:-len(suffix)]
    return f"{prefix}.lightning.force.com" if prefix else None


def lightning_host_errors(value: Any, *, label: str = "salesforce-lightning-host") -> list[str]:
    """Return errors unless ``value`` is a bare Salesforce Lightning host."""
    if not _nonempty_string(value):
        return [f"{label}-invalid"]
    try:
        parsed = urlparse(f"https://{value}")
        port = parsed.port
    except ValueError:
        return [f"{label}-invalid"]
    hostname = parsed.hostname
    if (
        hostname is None
        or hostname.lower() != str(value).lower()
        or not hostname.lower().endswith(".lightning.force.com")
        or port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        return [f"{label}-invalid"]
    return []


def lightning_route_errors(
    value: Any, *, expected_host: Any = None, label: str = "salesforce-lightning-route",
) -> list[str]:
    """Return errors unless ``value`` is a routed, HTTPS Lightning navigation URL."""
    if not _nonempty_string(value):
        return [f"{label}-invalid"]
    try:
        parsed = urlparse(str(value))
        port = parsed.port
    except ValueError:
        return [f"{label}-invalid"]
    hostname = parsed.hostname
    if (
        parsed.scheme != "https"
        or not hostname
        or not hostname.lower().endswith(".lightning.force.com")
        or port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.params
        or not any(
            parsed.path.startswith(prefix) and parsed.path[len(prefix):]
            for prefix in ("/lightning/n/", "/lightning/app/")
        )
    ):
        return [f"{label}-invalid"]
    if expected_host is not None and hostname.lower() != str(expected_host).lower():
        return [f"{label}-host-mismatch"]
    return []


def _identity_errors(
    value: Mapping[str, Any], expected: Mapping[str, Any], *, label: str,
) -> list[str]:
    errors: list[str] = []
    for field in ("trial_id", "candidate_digest"):
        if value.get(field) != expected.get(field):
            errors.append(f"{label}-{field}-mismatch")
    return errors


def target_preflight_errors(value: Mapping[str, Any]) -> list[str]:
    """Validate an independently captured default-developer-org preflight."""
    errors: list[str] = []
    if value.get("schema") != TARGET_PREFLIGHT_SCHEMA:
        errors.append("salesforce-target-preflight-schema-invalid")
    if value.get("status") != "connected":
        errors.append("salesforce-target-preflight-not-connected")
    if value.get("org_type") != "developer":
        errors.append("salesforce-target-preflight-not-developer-org")
    expected_org_id = value.get("expected_org_id")
    observed_org_id = value.get("observed_org_id")
    if not _valid_org_id(expected_org_id):
        errors.append("salesforce-target-preflight-expected-org-id-invalid")
    if not _valid_org_id(observed_org_id):
        errors.append("salesforce-target-preflight-observed-org-id-invalid")
    elif observed_org_id != expected_org_id:
        errors.append("salesforce-target-preflight-org-id-mismatch")
    expected_instance_url = value.get("expected_instance_url")
    observed_instance_url = value.get("observed_instance_url")
    errors.extend(instance_url_errors(
        expected_instance_url, label="salesforce-target-preflight-expected-instance-url",
    ))
    errors.extend(instance_url_errors(
        observed_instance_url, label="salesforce-target-preflight-observed-instance-url",
    ))
    if _nonempty_string(expected_instance_url) and observed_instance_url != expected_instance_url:
        errors.append("salesforce-target-preflight-instance-url-mismatch")
    expected_lightning_host = value.get("expected_lightning_host")
    observed_lightning_host = value.get("observed_lightning_host")
    errors.extend(lightning_host_errors(
        expected_lightning_host, label="salesforce-target-preflight-expected-lightning-host",
    ))
    errors.extend(lightning_host_errors(
        observed_lightning_host, label="salesforce-target-preflight-observed-lightning-host",
    ))
    if _nonempty_string(expected_lightning_host) and observed_lightning_host != expected_lightning_host:
        errors.append("salesforce-target-preflight-lightning-host-mismatch")
    derived_lightning_host = _derived_lightning_host(expected_instance_url)
    if (
        derived_lightning_host is not None
        and str(expected_lightning_host).lower() != derived_lightning_host
    ):
        errors.append("salesforce-target-preflight-instance-lightning-host-mismatch")
    my_domain = value.get("my_domain")
    if my_domain is not None:
        if not _nonempty_string(my_domain) or _MY_DOMAIN.fullmatch(str(my_domain)) is None:
            errors.append("salesforce-target-preflight-my-domain-invalid")
        elif not str(expected_lightning_host).lower().startswith(f"{my_domain}.".lower()):
            errors.append("salesforce-target-preflight-my-domain-lightning-host-mismatch")
    return sorted(set(errors))


def source_mapping_errors(
    value: Mapping[str, Any], *, expected: Mapping[str, Any], candidate_root: Path,
) -> list[str]:
    """Validate retained candidate components against the local source tree."""
    errors: list[str] = []
    if value.get("schema") != SOURCE_MAPPING_SCHEMA:
        errors.append("salesforce-source-mapping-schema-invalid")
    errors.extend(_identity_errors(value, expected, label="salesforce-source-mapping"))
    if not _valid_org_id(value.get("org_id")):
        errors.append("salesforce-source-mapping-org-id-invalid")
    errors.extend(instance_url_errors(value.get("instance_url"), label="salesforce-source-mapping-instance-url"))
    if not _nonempty_string(value.get("deployment_id")):
        errors.append("salesforce-source-mapping-deployment-id-invalid")
    for field in ("org_id", "instance_url", "deployment_id"):
        if field in expected and value.get(field) != expected.get(field):
            errors.append(f"salesforce-source-mapping-{field}-mismatch")
    if not _nonempty_string(value.get("rationale")):
        errors.append("salesforce-source-mapping-rationale-invalid")
    components = value.get("components")
    if not isinstance(components, list) or not components:
        return sorted(set([*errors, "salesforce-source-mapping-components-invalid"]))
    lightning_component = False
    resolved_root = candidate_root.resolve()
    for component in components:
        if not isinstance(component, Mapping):
            errors.append("salesforce-source-mapping-component-invalid")
            continue
        path_value = component.get("path")
        digest = component.get("sha256")
        kind = component.get("kind")
        component_type = component.get("component_type")
        full_name = component.get("full_name")
        if (
            not _valid_relative_path(path_value)
            or not _valid_digest(digest)
            or kind not in _COMPONENT_KINDS
            or not _nonempty_string(component_type)
            or not _nonempty_string(full_name)
        ):
            errors.append("salesforce-source-mapping-component-invalid")
            continue
        if kind in _LIGHTNING_COMPONENT_KINDS:
            lightning_component = True
        source = candidate_root / str(path_value)
        try:
            resolved = source.resolve(strict=True)
            if source.is_symlink() or not resolved.is_file() or resolved_root not in (resolved, *resolved.parents):
                errors.append("salesforce-source-mapping-component-not-candidate-source")
                continue
            digest_value = hashlib.sha256(resolved.read_bytes()).hexdigest()
            if digest_value != str(digest).lower():
                errors.append("salesforce-source-mapping-component-digest-mismatch")
        except OSError:
            errors.append("salesforce-source-mapping-component-unavailable")
    if not lightning_component:
        errors.append("salesforce-source-mapping-lightning-component-missing")
    return sorted(set(errors))


def _raw_deployment_payload(value: Mapping[str, Any]) -> tuple[Mapping[str, Any] | None, list[str]]:
    """Extract either a Salesforce CLI envelope or its retained raw result."""
    result = value.get("result")
    if result is not None:
        if value.get("status") != 0:
            return None, ["salesforce-raw-deployment-result-cli-status-invalid"]
        if not isinstance(result, Mapping):
            return None, ["salesforce-raw-deployment-result-payload-invalid"]
        return result, []
    if not isinstance(value, Mapping) or not _nonempty_string(value.get("id")):
        return None, ["salesforce-raw-deployment-result-payload-invalid"]
    return value, []


def _component_successes(value: Any) -> list[Mapping[str, Any]] | None:
    if isinstance(value, Mapping):
        return [value]
    if isinstance(value, list) and all(isinstance(item, Mapping) for item in value):
        return list(value)
    return None


def _source_component_members(mapping: Mapping[str, Any]) -> set[tuple[str, str]]:
    components = mapping.get("components")
    if not isinstance(components, list):
        return set()
    return {
        (str(component.get("component_type")), str(component.get("full_name")))
        for component in components
        if isinstance(component, Mapping)
        and _nonempty_string(component.get("component_type"))
        and _nonempty_string(component.get("full_name"))
    }


def _raw_deployment_component_errors(raw_payload: Mapping[str, Any], mapping: Mapping[str, Any]) -> list[str]:
    """Require every retained source metadata member in raw DX successes."""
    errors: list[str] = []
    if raw_payload.get("checkOnly") is not False:
        errors.append("salesforce-raw-deployment-result-check-only")
    details = raw_payload.get("details")
    if not isinstance(details, Mapping):
        return [*errors, "salesforce-raw-deployment-result-details-invalid"]
    failures = details.get("componentFailures")
    if failures not in (None, [], {}):
        errors.append("salesforce-raw-deployment-result-component-failures-present")
    successes = _component_successes(details.get("componentSuccesses"))
    if not successes:
        return [*errors, "salesforce-raw-deployment-result-component-successes-invalid"]
    successful_members: set[tuple[str, str]] = set()
    failed_members: set[tuple[str, str]] = set()
    for success in successes:
        member = (success.get("componentType"), success.get("fullName"))
        if not all(_nonempty_string(part) for part in member):
            continue
        normalized = (str(member[0]), str(member[1]))
        if success.get("success") is False:
            failed_members.add(normalized)
            errors.append("salesforce-raw-deployment-result-component-failed")
        elif success.get("success") is True:
            successful_members.add(normalized)
        else:
            errors.append("salesforce-raw-deployment-result-component-success-invalid")
    for member in _source_component_members(mapping):
        if member in failed_members:
            errors.append("salesforce-raw-deployment-result-component-failed")
        elif member not in successful_members:
            errors.append("salesforce-raw-deployment-result-component-missing")
    return errors


def deployment_errors(
    observation: Mapping[str, Any], *, expected: Mapping[str, Any], preflight: Mapping[str, Any],
    receipt: Mapping[str, Any], raw_result: Mapping[str, Any], mapping: Mapping[str, Any],
    raw_result_sha256: Any, mapping_sha256: Any, candidate_root: Path,
) -> list[str]:
    """Validate a Salesforce DX deployment and bind it to target and source proof."""
    errors: list[str] = []
    if observation.get("schema") != DEPLOYMENT_OBSERVATION_SCHEMA:
        errors.append("salesforce-deployment-schema-invalid")
    errors.extend(_identity_errors(observation, expected, label="salesforce-deployment"))
    if observation.get("provider") != "salesforce-dx":
        errors.append("salesforce-deployment-provider-invalid")
    if observation.get("status") != "succeeded":
        errors.append("salesforce-deployment-not-succeeded")
    if not _valid_org_id(observation.get("org_id")):
        errors.append("salesforce-deployment-org-id-invalid")
    errors.extend(instance_url_errors(observation.get("instance_url"), label="salesforce-deployment-instance-url"))
    if not _nonempty_string(observation.get("deployment_id")):
        errors.append("salesforce-deployment-id-invalid")
    errors.extend(target_preflight_errors(preflight))
    target_fields = {
        "org_id": "expected_org_id",
        "instance_url": "expected_instance_url",
        "lightning_host": "expected_lightning_host",
    }
    for field, target_field in target_fields.items():
        if observation.get(field) != preflight.get(target_field):
            errors.append(f"salesforce-deployment-target-preflight-{field}-mismatch")

    if receipt.get("schema") != DEPLOYMENT_RECEIPT_SCHEMA:
        errors.append("salesforce-deployment-receipt-schema-invalid")
    if receipt.get("provider") != "salesforce-dx":
        errors.append("salesforce-deployment-receipt-provider-invalid")
    if receipt.get("status") != "succeeded":
        errors.append("salesforce-deployment-receipt-not-succeeded")
    for field in ("candidate_digest", "org_id", "instance_url"):
        expected_value = observation.get(field) if field != "candidate_digest" else expected.get(field)
        if receipt.get(field) != expected_value:
            errors.append(f"salesforce-deployment-receipt-{field}-mismatch")
    if receipt.get("job_id") != observation.get("deployment_id"):
        errors.append("salesforce-deployment-receipt-job-id-mismatch")
    if receipt.get("raw_deployment_result_sha256") != raw_result_sha256:
        errors.append("salesforce-deployment-receipt-raw-result-mismatch")
    if receipt.get("component_mapping_sha256") != mapping_sha256:
        errors.append("salesforce-deployment-receipt-component-mapping-mismatch")

    raw_payload, raw_errors = _raw_deployment_payload(raw_result)
    errors.extend(raw_errors)
    if raw_payload is not None:
        if raw_payload.get("id") != observation.get("deployment_id"):
            errors.append("salesforce-raw-deployment-result-job-id-mismatch")
        if raw_payload.get("status") != "Succeeded":
            errors.append("salesforce-raw-deployment-result-status-invalid")
        errors.extend(_raw_deployment_component_errors(raw_payload, mapping))

    mapping_expected = {
        "trial_id": expected.get("trial_id"),
        "candidate_digest": expected.get("candidate_digest"),
        "org_id": observation.get("org_id"),
        "instance_url": observation.get("instance_url"),
        "deployment_id": observation.get("deployment_id"),
    }
    errors.extend(source_mapping_errors(mapping, expected=mapping_expected, candidate_root=candidate_root))
    return sorted(set(errors))


def hosted_errors(
    observation: Mapping[str, Any], *, expected: Mapping[str, Any], deployment: Mapping[str, Any],
    trace: Mapping[str, Any],
) -> list[str]:
    """Validate authenticated Lightning browser proof bound to a deployment."""
    errors: list[str] = []
    if observation.get("schema") != HOSTED_OBSERVATION_SCHEMA:
        errors.append("salesforce-hosted-observation-schema-invalid")
    errors.extend(_identity_errors(observation, expected, label="salesforce-hosted-observation"))
    for field in ("org_id", "instance_url", "deployment_id"):
        if observation.get(field) != deployment.get(field):
            errors.append(f"salesforce-hosted-observation-{field}-mismatch")
    errors.extend(lightning_host_errors(
        observation.get("lightning_host"), label="salesforce-hosted-observation-lightning-host",
    ))
    errors.extend(lightning_route_errors(
        observation.get("lightning_route"), expected_host=observation.get("lightning_host"),
        label="salesforce-hosted-observation-lightning-route",
    ))
    if observation.get("authenticated") is not True:
        errors.append("salesforce-hosted-observation-not-authenticated")

    if trace.get("schema") != LIGHTNING_BROWSER_TRACE_SCHEMA:
        errors.append("salesforce-lightning-browser-trace-schema-invalid")
    errors.extend(_identity_errors(trace, expected, label="salesforce-lightning-browser-trace"))
    for field in ("org_id", "instance_url", "deployment_id", "lightning_host", "lightning_route", "authenticated"):
        if trace.get(field) != observation.get(field):
            errors.append(f"salesforce-lightning-browser-trace-{field}-mismatch")
    errors.extend(lightning_route_errors(
        trace.get("lightning_route"), expected_host=observation.get("lightning_host"),
        label="salesforce-lightning-browser-trace-lightning-route",
    ))
    return sorted(set(errors))


def cross_binding_errors(
    deployment: Mapping[str, Any], hosted: Mapping[str, Any], mapping: Mapping[str, Any],
) -> list[str]:
    """Ensure the three independently retained records name one candidate/target."""
    errors: list[str] = []
    for field in ("trial_id", "candidate_digest", "org_id", "instance_url", "deployment_id"):
        expected = deployment.get(field)
        if hosted.get(field) != expected:
            errors.append(f"salesforce-deployment-hosted-{field}-mismatch")
        if mapping.get(field) != expected:
            errors.append(f"salesforce-deployment-source-{field}-mismatch")
    if hosted.get("lightning_host") != deployment.get("lightning_host"):
        errors.append("salesforce-deployment-hosted-lightning-host-mismatch")
    return sorted(set(errors))
