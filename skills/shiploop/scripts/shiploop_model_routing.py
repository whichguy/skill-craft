"""Optional harness-to-model routing for ShipLoop (planning vs. execution profiles)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any

import shiploop_stage_spec as stage_spec

HOST_ALIASES = {"agy": "antigravity"}
KNOWN_HOSTS = ("antigravity", "claude", "codex", "cursor", "grok", "opencode")
EFFORT_SUFFIXES = ("-low", "-medium", "-high", "-xhigh", "-max")
RESUME_MODES = ("warm", "fresh")
DEFAULT_RESUME = "warm"

_TOP_KEYS = frozenset({"planning", "execution", "review", "stages", "resume"})
_ENTRY_KEYS = frozenset({"host", "model", "effort", "args", "resume"})

# Default built-in per-host profiles applied by `shiploop-drive` unless opted out (`--no-routing`,
# explicit routing config/flags, or an explicit model flag after `--`). Antigravity assigns both
# planning and execution to `gemini-pro-orchestrator-neon` so Orchestrator runs unbroken in one session
# while switching Neon (plan) <-> Carbon (execute) internally.
DEFAULT_ROUTING: dict[str, dict[str, dict[str, str]]] = {
    "planning": {
        "claude": {"model": "claude-opus-5-5", "effort": "high"},
        "codex": {"model": "gpt-6.2-astra", "effort": "high"},
        "antigravity": {"model": "gemini-pro-orchestrator-neon"},
    },
    "execution": {
        "claude": {"model": "claude-sonnet-5-5", "effort": "high"},
        "codex": {"model": "gpt-6.2-sol", "effort": "xhigh"},
        "antigravity": {"model": "gemini-pro-orchestrator-neon"},
    },
}


@dataclass(frozen=True)
class RouteTarget:
    """Resolved execution target for one ShipLoop stage."""

    host: str
    profile: str
    model: str | None = None
    effort: str | None = None
    args: tuple[str, ...] = ()
    resume: str = DEFAULT_RESUME

    @property
    def target_key(self) -> str:
        """Canonical identity of (host, model, effort, args) for boundary detection."""
        return json.dumps([self.host, self.model, self.effort, list(self.args)], separators=(",", ":"))

    @property
    def label(self) -> str:
        """Human-readable label for traces, boundary notices, and logs."""
        if self.model and self.effort:
            return f"{self.host}:{self.model}/{self.effort}"
        if self.model:
            return f"{self.host}:{self.model}"
        if self.effort:
            return f"{self.host}:default/{self.effort}"
        return f"{self.host}:default"


def normalize_host(host: str) -> str:
    """Normalize known host aliases (for example ``agy`` -> ``antigravity``)."""
    cleaned = str(host or "").strip().lower()
    return HOST_ALIASES.get(cleaned, cleaned)


def _normalize_entry(raw: Any, *, where: str) -> dict[str, Any]:
    if isinstance(raw, str):
        model = raw.strip()
        if not model:
            raise ValueError(f"{where}: model string must not be empty")
        return {"model": model}
    if not isinstance(raw, Mapping):
        raise ValueError(f"{where}: expected model string or object, got {type(raw).__name__}")
    unknown = set(raw) - _ENTRY_KEYS
    if unknown:
        raise ValueError(f"{where}: unknown keys {sorted(unknown)}")
    out: dict[str, Any] = {}
    if "host" in raw and raw["host"] is not None:
        if not isinstance(raw["host"], str) or not raw["host"].strip():
            raise ValueError(f"{where}.host must be a non-empty string")
        host = normalize_host(raw["host"])
        if host not in KNOWN_HOSTS:
            raise ValueError(f"{where}.host: unknown host {raw['host']!r}")
        out["host"] = host
    if "model" in raw and raw["model"] is not None:
        if not isinstance(raw["model"], str) or not raw["model"].strip():
            raise ValueError(f"{where}.model must be a non-empty string")
        out["model"] = raw["model"].strip()
    if "effort" in raw and raw["effort"] is not None:
        if not isinstance(raw["effort"], str) or not raw["effort"].strip():
            raise ValueError(f"{where}.effort must be a non-empty string")
        out["effort"] = raw["effort"].strip()
    if "args" in raw and raw["args"] is not None:
        if not isinstance(raw["args"], (list, tuple)) or not all(isinstance(x, str) for x in raw["args"]):
            raise ValueError(f"{where}.args must be a list of strings")
        out["args"] = list(raw["args"])
    if "resume" in raw and raw["resume"] is not None:
        if raw["resume"] not in RESUME_MODES:
            raise ValueError(f"{where}.resume must be one of {RESUME_MODES}")
        out["resume"] = raw["resume"]
    return out


def _normalize_bucket(raw: Any, *, where: str) -> Any:
    if isinstance(raw, str):
        return _normalize_entry(raw, where=where)
    if not isinstance(raw, Mapping):
        raise ValueError(f"{where}: expected string or mapping, got {type(raw).__name__}")
    if any(key in _ENTRY_KEYS for key in raw):
        return _normalize_entry(raw, where=where)
    bucket: dict[str, Any] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"{where}: harness keys must be non-empty strings")
        norm = "default" if key.strip().lower() == "default" else normalize_host(key)
        if norm != "default" and norm not in KNOWN_HOSTS:
            raise ValueError(f"{where}: unknown host key {key!r}")
        if norm in bucket:
            raise ValueError(f"{where}: duplicate host key {key!r}")
        bucket[norm] = _normalize_entry(value, where=f"{where}.{key}")
    return bucket


def load_config(source: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    """Load and validate a routing configuration from a mapping, JSON path, JSON text, or ``'default'`` preset."""
    if isinstance(source, Mapping):
        data = dict(source)
    elif isinstance(source, str) and source.strip().lower() == "default":
        data = dict(DEFAULT_ROUTING)
    else:
        raw_text: str
        if isinstance(source, Path):
            raw_text = source.read_text(encoding="utf-8")
        elif isinstance(source, str):
            stripped = source.strip()
            raw_text = stripped if stripped.startswith("{") else Path(source).expanduser().read_text(encoding="utf-8")
        else:
            raise ValueError(f"unsupported routing source type: {type(source).__name__}")
        loaded = json.loads(raw_text)
        if not isinstance(loaded, dict):
            raise ValueError("routing configuration must be a JSON object")
        data = loaded

    unknown = set(data) - _TOP_KEYS
    if unknown:
        raise ValueError(f"routing config has unknown keys {sorted(unknown)}")
    normalized: dict[str, Any] = {}
    if "resume" in data and data["resume"] is not None:
        if data["resume"] not in RESUME_MODES:
            raise ValueError(f"routing config resume must be one of {RESUME_MODES}")
        normalized["resume"] = data["resume"]
    for bucket_name in ("planning", "execution", "review"):
        if bucket_name in data and data[bucket_name] is not None:
            normalized[bucket_name] = _normalize_bucket(data[bucket_name], where=bucket_name)
    if "stages" in data and data["stages"] is not None:
        if not isinstance(data["stages"], Mapping):
            raise ValueError("stages must be an object mapping stage name to entry")
        stages_out: dict[str, Any] = {}
        for stage_name, spec in data["stages"].items():
            if stage_name != "improve" and stage_name not in stage_spec.STAGE_SPEC:
                raise ValueError(f"stages: unknown stage {stage_name!r}")
            stages_out[stage_name] = _normalize_bucket(spec, where=f"stages.{stage_name}")
        normalized["stages"] = stages_out
    return normalized


def from_cli_flags(
    *,
    planning_model: str | None = None,
    planning_effort: str | None = None,
    planning_host: str | None = None,
    execution_model: str | None = None,
    execution_effort: str | None = None,
    execution_host: str | None = None,
    review_model: str | None = None,
    review_effort: str | None = None,
    review_host: str | None = None,
    resume_mode: str | None = None,
) -> dict[str, Any] | None:
    """Build a normalized routing config from CLI shorthand flags, or None when none are set."""
    raw: dict[str, Any] = {}
    for bucket, host, model, effort in (
        ("planning", planning_host, planning_model, planning_effort),
        ("execution", execution_host, execution_model, execution_effort),
        ("review", review_host, review_model, review_effort),
    ):
        entry: dict[str, Any] = {}
        if host:
            entry["host"] = host
        if model:
            entry["model"] = model
        if effort:
            entry["effort"] = effort
        if entry:
            raw[bucket] = entry
    if not raw and not resume_mode:
        return None
    if resume_mode:
        raw["resume"] = resume_mode
    return load_config(raw)


def default_routing(host: str | None = None) -> dict[str, Any] | None:
    """Return the built-in routing config for ``host``, or None if ``host`` has no built-in default."""
    if host is None:
        return load_config(DEFAULT_ROUTING)
    norm = normalize_host(host)
    if norm in DEFAULT_ROUTING["planning"] or norm in DEFAULT_ROUTING["execution"]:
        return load_config(DEFAULT_ROUTING)
    return None


def extra_sets_model(extra: list[str] | tuple[str, ...]) -> bool:
    """True when pass-through CLI arguments after ``--`` explicitly select a model."""
    expect_config_value = False
    for arg in extra:
        if expect_config_value:
            expect_config_value = False
            if arg.split("=", 1)[0].strip() == "model":
                return True
            continue
        if arg in ("--model", "-m") or arg.startswith(("--model=", "-m=")):
            return True
        if arg in ("-c", "--config"):
            expect_config_value = True
            continue
        if arg.startswith("--config="):
            value = arg.split("=", 1)[1]
            if value.split("=", 1)[0].strip() == "model":
                return True
        elif arg.startswith("-c") and len(arg) > 2:
            if arg[2:].split("=", 1)[0].strip() == "model":
                return True
    return False


def _select_entry(bucket: Any, default_host: str) -> Mapping[str, Any] | None:
    if bucket is None:
        return None
    if isinstance(bucket, Mapping):
        if any(key in _ENTRY_KEYS for key in bucket):
            return bucket
        if default_host in bucket:
            return bucket[default_host]
        if "default" in bucket:
            return bucket["default"]
        return None
    return None


def resolve(
    config: Mapping[str, Any] | None,
    stage: str | None,
    default_host: str,
) -> RouteTarget | None:
    """Resolve the effective RouteTarget for ``stage`` under ``default_host``."""
    if not stage:
        return None
    norm_host = normalize_host(default_host)
    profile = stage_spec.stage_profile(stage)
    if profile is None:
        return None
    default_resume = str((config or {}).get("resume") or DEFAULT_RESUME)
    if not config:
        return RouteTarget(host=norm_host, profile=profile, resume=default_resume)

    bucket = None
    stages_map = config.get("stages")
    if isinstance(stages_map, Mapping) and stage in stages_map:
        bucket = stages_map[stage]
    elif stage == "improve" and "review" in config:
        bucket = config["review"]
    else:
        bucket = config.get(profile)

    entry = _select_entry(bucket, norm_host)
    if entry is None:
        return RouteTarget(host=norm_host, profile=profile, resume=default_resume)
    target_host = normalize_host(str(entry.get("host") or norm_host))
    model = entry.get("model")
    effort = entry.get("effort")
    args = tuple(entry.get("args") or ())
    resume = str(entry.get("resume") or default_resume)
    return RouteTarget(host=target_host, profile=profile, model=model, effort=effort, args=args, resume=resume)


def host_model_args(host: str, target: RouteTarget) -> list[str]:
    """Translate ``target`` into host-specific CLI arguments."""
    norm_host = normalize_host(host)
    out: list[str] = []
    if norm_host == "antigravity":
        if target.model:
            out += ["--model", target.model]
        # Antigravity CLI rejects --effort when the model slug already carries an effort suffix.
        if target.effort and (not target.model or not target.model.endswith(EFFORT_SUFFIXES)):
            out += ["--effort", target.effort]
    elif norm_host == "codex":
        if target.model:
            out += ["-m", target.model]
        if target.effort:
            out += ["-c", f"model_reasoning_effort={target.effort}"]
    elif norm_host == "claude":
        if target.model:
            out += ["--model", target.model]
        if target.effort:
            out += ["--effort", target.effort]
    elif norm_host == "grok":
        if target.model:
            out += ["--model", target.model]
        if target.effort:
            out += ["--reasoning-effort", target.effort]
    elif norm_host in ("cursor", "opencode"):
        if target.model:
            out += ["--model", target.model]
    out.extend(target.args)
    return out


def active_boundary(
    stage: str | None,
    run_id: str | None,
    env: Mapping[str, str] | None = None,
) -> dict[str, str] | None:
    """Return boundary metadata when an active driver session crossed into a different target."""
    env = os.environ if env is None else env
    routing_path = env.get("SHIPLOOP_DRIVE_ROUTING", "").strip()
    default_host = env.get("SHIPLOOP_DRIVE_HOST", "").strip()
    assigned_key = env.get("SHIPLOOP_DRIVE_TARGET", "").strip()
    if not routing_path or not default_host or not assigned_key or not stage:
        return None
    expected_run_id = env.get("SHIPLOOP_DRIVE_RUN_ID", "").strip()
    if expected_run_id and run_id and expected_run_id != run_id:
        return None
    try:
        config = load_config(Path(routing_path))
        next_target = resolve(config, stage, default_host)
    except (OSError, ValueError, TypeError):
        return None
    if next_target is None or next_target.target_key == assigned_key:
        return None
    return {
        "from_label": env.get("SHIPLOOP_DRIVE_LABEL", "").strip() or assigned_key,
        "to_label": next_target.label,
        "stage": stage,
        "profile": next_target.profile,
    }
