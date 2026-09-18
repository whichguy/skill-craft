#!/usr/bin/env python3
"""Run one isolated, evidence-producing generic-discovery access probe.

This program deliberately keeps all acquired code, npm cache, synthetic files,
and the stdio MCP process inside a TemporaryDirectory.  It writes only compact,
redacted receipts to the requested evidence directory.  It never edits host MCP
configuration, skill homes, package configuration, or secrets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
MCP_PACKAGE = "@modelcontextprotocol/server-filesystem"
MCP_VERSION = "2026.8.31"
MCP_GIT_HEAD = "a40bc270fb5ece62673f8a1196f57116d885c5eb"
MCP_INTEGRITY = "sha512-kKaFkyAh6oipvc9+EAbJ552JafnMnOq5nzmzWkp1jJdBhTAAGpmIpWihUG1+rfNhmEFM98gUZDdCHCDD4v6a7Q=="

SKILL_REPOSITORY = "https://github.com/anthropics/skills.git"
SKILL_COMMIT = "34040c9c568585f6929bedeaad110ad08f079624"
SKILL_SUBTREE = Path("skills/webapp-testing")
EXISTING_WEB_FIXTURE = REPO_ROOT / "test/experiments/shiploop_delivery/browser_consumer/local-candidate/index.html"

ALLOWED_TEXT = "synthetic allowed target: filesystem MCP may read this only\n"
OUTSIDE_TEXT = "synthetic outside-root sentinel: this must not be returned\n"


class OutputDirectoryError(ValueError):
    """The requested evidence path cannot safely receive a new run."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def lexical_absolute(path: Path) -> Path:
    """Make an absolute path without resolving a possibly hostile symlink."""
    return Path(os.path.abspath(str(path.expanduser())))


def prepare_new_output_directory(requested: Path) -> Path:
    """Create one fresh output directory before any temporary process or network call."""
    candidate = lexical_absolute(requested)
    if candidate.exists() or candidate.is_symlink():
        raise OutputDirectoryError("output directory already exists or is a symlink")
    parent = candidate.parent
    if not parent.is_dir():
        raise OutputDirectoryError("output parent must already exist; do not create nested evidence paths implicitly")
    # macOS commonly exposes /tmp and /var through symlinks. Once the requested
    # leaf has been rejected as existing/symlinked, normalize its existing parent
    # and create the leaf exactly once in that real directory.
    resolved_parent = parent.resolve(strict=True)
    final_target = resolved_parent / candidate.name
    if final_target.exists() or final_target.is_symlink():
        raise OutputDirectoryError("resolved output directory already exists or is a symlink")
    final_target.mkdir(mode=0o700, exist_ok=False)
    return final_target


def compact_command(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout_seconds: int = 90,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(cwd) if cwd else None,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_seconds,
    )


def command_receipt(
    name: str,
    process: subprocess.CompletedProcess[str],
    *,
    started: float,
) -> dict[str, Any]:
    """Keep status and body hashes, but no transient paths or raw command output."""
    return {
        "name": name,
        "elapsed_ms": round((time.monotonic() - started) * 1000),
        "returncode": process.returncode,
        "stdout_sha256": sha256_bytes(process.stdout.encode("utf-8")),
        "stderr_sha256": sha256_bytes(process.stderr.encode("utf-8")),
        "stderr_nonempty": bool(process.stderr.strip()),
    }


# Deliberate experiment-only choice: retain this verified, bounded JSON-RPC
# client rather than add a second temporary Node helper around the server's
# dynamically resolved @modelcontextprotocol/sdk dependency. The archived run
# exercised this client and records direct process reaping. The package asks for
# a semver-range SDK, and validating a replacement against that resolved version
# would require another network acquisition run, which this hardening pass does
# not authorize. Current official SDK docs support the alternative, but that is
# not evidence that this exact archived package graph behaved identically.
class StdioMcpClient:
    """Small line-delimited JSON-RPC client for one bounded stdio MCP session."""

    def __init__(self, argv: list[str]) -> None:
        self.argv = argv
        self.process: subprocess.Popen[str] | None = None
        self._lines: queue.Queue[str | None] = queue.Queue()
        self._stderr: list[str] = []
        self._stdout_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None
        self.transcript: list[dict[str, Any]] = []

    def start(self) -> None:
        self.process = subprocess.Popen(
            self.argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        assert self.process.stdout is not None
        assert self.process.stderr is not None
        self._stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()

    def _read_stdout(self) -> None:
        assert self.process is not None and self.process.stdout is not None
        for line in self.process.stdout:
            self._lines.put(line)
        self._lines.put(None)

    def _read_stderr(self) -> None:
        assert self.process is not None and self.process.stderr is not None
        for line in self.process.stderr:
            self._stderr.append(line)

    def _send(self, message: dict[str, Any]) -> None:
        assert self.process is not None and self.process.stdin is not None
        self.process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self.process.stdin.flush()

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        message: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self._send(message)
        self.transcript.append({"direction": "request", "method": method, "notification": True})

    def request(
        self,
        request_id: int,
        method: str,
        params: dict[str, Any] | None,
        *,
        timeout_seconds: int = 20,
    ) -> dict[str, Any]:
        message: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        self._send(message)
        self.transcript.append({"direction": "request", "id": request_id, "method": method})
        deadline = time.monotonic() + timeout_seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"timed out waiting for MCP response to {method}")
            try:
                line = self._lines.get(timeout=remaining)
            except queue.Empty as error:
                raise TimeoutError(f"timed out waiting for MCP response to {method}") from error
            if line is None:
                exit_code = self.process.poll() if self.process else None
                raise RuntimeError(f"MCP process closed stdout before {method}; exit={exit_code}")
            try:
                response = json.loads(line)
            except json.JSONDecodeError:
                self.transcript.append({"direction": "server", "kind": "non_json_stdout"})
                continue
            if response.get("id") == request_id:
                self.transcript.append(
                    {
                        "direction": "response",
                        "id": request_id,
                        "method": method,
                        "has_result": "result" in response,
                        "has_error": "error" in response,
                    }
                )
                return response
            self.transcript.append({"direction": "server", "kind": "notification_or_other_response"})

    def close(self) -> dict[str, Any]:
        process = self.process
        if process is None:
            return {"owned_process_started": False, "owned_process_reaped": True}
        forced_kill = False
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                forced_kill = True
                process.kill()
                process.wait(timeout=5)
        if self._stdout_thread:
            self._stdout_thread.join(timeout=1)
        if self._stderr_thread:
            self._stderr_thread.join(timeout=1)
        return {
            "owned_process_started": True,
            "owned_process_reaped": process.poll() is not None,
            "exit_code": process.returncode,
            "forced_kill": forced_kill,
            "stderr_sha256": sha256_bytes("".join(self._stderr).encode("utf-8")),
            "stderr_nonempty": bool("".join(self._stderr).strip()),
        }


def relative_file_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            hashes[path.relative_to(root).as_posix()] = sha256_file(path)
    return hashes


def selected_skill_review(skill_root: Path, fixture_text: str, fixture_source_sha256: str) -> dict[str, Any]:
    """Read the installed card and apply its static-HTML reconnaissance branch."""
    card = skill_root / "SKILL.md"
    text = card.read_text(encoding="utf-8")
    headings = [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]
    decision_markers = [
        marker
        for marker in ("Decision Tree", "Playwright", "local web", "browser", "static HTML")
        if marker.casefold() in text.casefold()
    ]
    selector_ids = re.findall(r"\bid=[\"']([^\"']+)[\"']", fixture_text)
    has_click_handler = "addEventListener(\"click\"" in fixture_text or "addEventListener('click'" in fixture_text
    has_expected_state_change = 'dataset.result = "passed"' in fixture_text
    reconnaissance_complete = "move-piece" in selector_ids and has_click_handler and has_expected_state_change
    result = (
        "identified #move-piece and the source-visible pending-to-passed result transition; browser automation was intentionally not started"
        if reconnaissance_complete
        else "static HTML reconnaissance was incomplete; browser automation was intentionally not started"
    )
    # This is an existing repository fixture copied into the temporary allowed
    # root.  The relevant static-HTML reconnaissance branch identifies the user
    # action selector and the source-visible state transition without starting a
    # browser or claiming browser behavior.
    return {
        "skill_card_read": True,
        "skill_card_sha256": sha256_file(card),
        "top_level_sections": headings,
        "observed_decision_markers": decision_markers,
        "applied_reconnaissance": {
            "fixture_label": "allowed/existing-local-candidate/index.html",
            "fixture_source_sha256": fixture_source_sha256,
            "target_kind": "existing_static_local_html_fixture",
            "selector_ids_found": selector_ids,
            "click_handler_found": has_click_handler,
            "source_visible_result_transition_found": has_expected_state_change,
            "result": result,
            "reconnaissance_complete": reconnaissance_complete,
            "boundary": "This applies only static HTML reconnaissance through the downloaded card. It does not prove served behavior, a browser-visible click result, model skill selection, model execution, or comparative benefit.",
        },
    }


def tool_result_text(response: dict[str, Any]) -> str:
    result = response.get("result")
    if not isinstance(result, dict):
        return ""
    content = result.get("content")
    if not isinstance(content, list):
        return ""
    text_parts: list[str] = []
    for item in content:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            text_parts.append(item["text"])
    return "\n".join(text_parts)


def compact_transcript(
    transcript: list[dict[str, Any]],
    *,
    catalog: dict[str, Any],
    allowed_response: dict[str, Any],
    fixture_response: dict[str, Any],
    denied_response: dict[str, Any],
    read_tool: str,
) -> list[dict[str, Any]]:
    result = list(transcript)
    tool_names = []
    if isinstance(catalog.get("result"), dict):
        tools = catalog["result"].get("tools")
        if isinstance(tools, list):
            tool_names = [tool.get("name") for tool in tools if isinstance(tool, dict) and isinstance(tool.get("name"), str)]
    result.extend(
        [
            {"observation": "catalog", "tool_count": len(tool_names), "tool_names": tool_names},
            {
                "observation": "allowed_read",
                "tool": read_tool,
                "target": "allowed/target.txt",
                "has_jsonrpc_error": "error" in allowed_response,
                "result_is_error": bool(allowed_response.get("result", {}).get("isError")) if isinstance(allowed_response.get("result"), dict) else None,
                "returned_expected_text": ALLOWED_TEXT in tool_result_text(allowed_response),
            },
            {
                "observation": "outside_root_read",
                "tool": read_tool,
                "target": "outside/secret.txt",
                "has_jsonrpc_error": "error" in denied_response,
                "result_is_error": bool(denied_response.get("result", {}).get("isError")) if isinstance(denied_response.get("result"), dict) else None,
                "returned_outside_sentinel": OUTSIDE_TEXT in tool_result_text(denied_response),
                "response_text_sha256": sha256_bytes(tool_result_text(denied_response).encode("utf-8")),
            },
            {
                "observation": "existing_static_html_reconnaissance_read",
                "tool": read_tool,
                "target": "allowed/existing-local-candidate/index.html",
                "has_jsonrpc_error": "error" in fixture_response,
                "result_is_error": bool(fixture_response.get("result", {}).get("isError")) if isinstance(fixture_response.get("result"), dict) else None,
                "returned_html": "<html" in tool_result_text(fixture_response).casefold(),
                "returned_move_piece_selector": 'id="move-piece"' in tool_result_text(fixture_response),
            },
        ]
    )
    return result


def build_summary(receipts: dict[str, Any]) -> str:
    """Describe only the status actually recorded by this run."""
    status = receipts.get("status", "incomplete")
    lines = ["# Isolated acquisition/access follow-up", "", f"Status: `{status}`.", ""]
    if status == "completed":
        lines.extend(
            [
                "The probe completed in a newly created evidence directory using task-local acquisition only.",
                "",
                "It recorded MCP initialization, a tool catalog, an allowed synthetic-file read, static-HTML reconnaissance of the existing local fixture, and a denied sibling-path read. No browser or model context was launched.",
            ]
        )
    else:
        failure_types = [
            item.get("type", "UnknownFailure")
            for item in receipts.get("failures", [])
            if isinstance(item, dict)
        ]
        lines.extend(
            [
                "The probe did not complete. This directory records only observed partial setup and cleanup facts; it establishes no successful acquisition, MCP access, or skill-procedure outcome.",
                "",
                f"Observed failure types: {', '.join(failure_types) if failure_types else 'not recorded'}.",
            ]
        )
    lines.extend(
        [
            "",
            "See `receipt.json`, `mcp-transcript.json`, and `provenance.json` for compact redacted evidence. These receipts do not prove host-wide MCP configuration, model skill selection, or general production authorization.",
            "",
        ]
    )
    return "\n".join(lines)


def run_probe(out_dir: Path) -> dict[str, Any]:
    # Must happen before a temporary directory, network command, or MCP process.
    out_dir = prepare_new_output_directory(out_dir)
    started_at = time.time()
    receipts: dict[str, Any] = {
        "schema": 1,
        "purpose": "isolated acquisition and access-control probe",
        "fixed_pins": {
            "mcp": {"package": MCP_PACKAGE, "version": MCP_VERSION, "git_head": MCP_GIT_HEAD, "integrity": MCP_INTEGRITY},
            "skill": {"repository": SKILL_REPOSITORY, "commit": SKILL_COMMIT, "subtree": SKILL_SUBTREE.as_posix()},
        },
        "constraints": {
            "host_mcp_configuration_changed": False,
            "host_skill_configuration_changed": False,
            "secrets_used": False,
            "model_contexts_launched": 0,
            "persistent_package_install": False,
        },
        "commands": [],
        "status": "incomplete",
        "failures": [],
        "client_implementation": {
            "mode": "experiment_only_bounded_manual_jsonrpc",
            "selection": "Retained because the archived run exercised this direct process-reaping client; a replacement against the dynamically resolved SDK range requires a separate new acquisition run.",
        },
    }
    transcript: list[dict[str, Any]] = []
    temporary_root: Path | None = None
    client: StdioMcpClient | None = None

    try:
        with tempfile.TemporaryDirectory(prefix="shiploop-access-followup-") as temporary_name:
            temporary_root = Path(temporary_name)
            npm_cache = temporary_root / "npm-cache"
            npm_prefix = temporary_root / "mcp-prefix"
            allowed_root = temporary_root / "allowed"
            outside_root = temporary_root / "outside"
            skill_checkout = temporary_root / "skill-source"
            installed_skill = temporary_root / "skill-install" / "webapp-testing"
            allowed_root.mkdir()
            outside_root.mkdir()
            allowed_file = allowed_root / "target.txt"
            outside_file = outside_root / "secret.txt"
            if not EXISTING_WEB_FIXTURE.is_file():
                raise RuntimeError("pre-existing local browser fixture was unavailable")
            web_fixture_dir = allowed_root / "existing-local-candidate"
            web_fixture_dir.mkdir()
            web_fixture_file = web_fixture_dir / "index.html"
            shutil.copy2(EXISTING_WEB_FIXTURE, web_fixture_file)
            fixture_source_sha256 = sha256_file(EXISTING_WEB_FIXTURE)
            if sha256_file(web_fixture_file) != fixture_source_sha256:
                raise RuntimeError("copied local browser fixture did not preserve its source hash")
            allowed_file.write_text(ALLOWED_TEXT, encoding="utf-8")
            outside_file.write_text(OUTSIDE_TEXT, encoding="utf-8")
            receipts["existing_fixture"] = {
                "source_label": "test/experiments/shiploop_delivery/browser_consumer/local-candidate/index.html",
                "source_sha256": fixture_source_sha256,
                "temporary_copy_label": "allowed/existing-local-candidate/index.html",
                "synthetic_fixture_added": False,
                "runtime_or_browser_started": False,
            }
            npm_env = os.environ.copy()
            npm_env.update(
                {
                    "npm_config_cache": str(npm_cache),
                    "npm_config_update_notifier": "false",
                    "npm_config_audit": "false",
                    "npm_config_fund": "false",
                }
            )

            command_started = time.monotonic()
            metadata_process = compact_command(
                ["npm", "view", f"{MCP_PACKAGE}@{MCP_VERSION}", "--json"], env=npm_env, timeout_seconds=45
            )
            receipts["commands"].append(command_receipt("npm_view_pinned", metadata_process, started=command_started))
            if metadata_process.returncode != 0:
                raise RuntimeError("pinned npm metadata query failed")
            metadata = json.loads(metadata_process.stdout)
            dist = metadata.get("dist", {})
            if metadata.get("gitHead") != MCP_GIT_HEAD or dist.get("integrity") != MCP_INTEGRITY:
                raise RuntimeError("pinned MCP metadata did not match preregistered source identity")

            command_started = time.monotonic()
            install_process = compact_command(
                [
                    "npm",
                    "install",
                    "--ignore-scripts",
                    "--no-audit",
                    "--no-fund",
                    "--prefix",
                    str(npm_prefix),
                    f"{MCP_PACKAGE}@{MCP_VERSION}",
                ],
                env=npm_env,
                timeout_seconds=90,
            )
            receipts["commands"].append(command_receipt("npm_install_task_local_ignore_scripts", install_process, started=command_started))
            if install_process.returncode != 0:
                raise RuntimeError("task-local MCP installation failed")
            mcp_root = npm_prefix / "node_modules" / "@modelcontextprotocol" / "server-filesystem"
            package_json = json.loads((mcp_root / "package.json").read_text(encoding="utf-8"))
            bin_map = package_json.get("bin", {})
            if not isinstance(bin_map, dict) or "mcp-server-filesystem" not in bin_map:
                raise RuntimeError("installed MCP package did not expose expected filesystem binary")
            entrypoint = mcp_root / str(bin_map["mcp-server-filesystem"])
            if not entrypoint.is_file():
                raise RuntimeError("installed MCP filesystem entrypoint was missing")
            lock_data = json.loads((npm_prefix / "package-lock.json").read_text(encoding="utf-8"))
            lock_entry = lock_data.get("packages", {}).get("node_modules/@modelcontextprotocol/server-filesystem", {})
            if package_json.get("name") != MCP_PACKAGE or package_json.get("version") != MCP_VERSION:
                raise RuntimeError("installed MCP package metadata did not match the pinned package identity")
            receipts["mcp_acquisition"] = {
                "source": "npm registry metadata plus task-local install",
                "repository": metadata.get("repository"),
                "npm_publisher": metadata.get("_npmUser"),
                "package_scripts_declared": sorted(package_json.get("scripts", {}).keys()),
                "lifecycle_scripts_disabled": True,
                "package_json_sha256": sha256_file(mcp_root / "package.json"),
                "entrypoint_sha256": sha256_file(entrypoint),
                "package_lock_entry_keys": sorted(lock_entry.keys()) if isinstance(lock_entry, dict) else [],
                "package_lock_integrity": lock_entry.get("integrity") if isinstance(lock_entry, dict) else None,
                "package_lock_integrity_matches_pinned_metadata": lock_entry.get("integrity") == MCP_INTEGRITY if isinstance(lock_entry, dict) else False,
                "integrity_interpretation": "The pinned registry SHA-512 is retained as provenance. npm's direct --prefix lock entry may omit integrity, so source identity is additionally checked through installed package name/version and package/entrypoint SHA-256 hashes.",
            }

            command_started = time.monotonic()
            clone_process = compact_command(
                ["git", "clone", "--filter=blob:none", "--no-checkout", SKILL_REPOSITORY, str(skill_checkout)],
                timeout_seconds=90,
            )
            receipts["commands"].append(command_receipt("git_clone_skill_source", clone_process, started=command_started))
            if clone_process.returncode != 0:
                raise RuntimeError("published skill source clone failed")
            command_started = time.monotonic()
            sparse_process = compact_command(
                ["git", "sparse-checkout", "set", "--no-cone", SKILL_SUBTREE.as_posix()], cwd=skill_checkout, timeout_seconds=30
            )
            receipts["commands"].append(command_receipt("git_sparse_checkout_skill_subtree", sparse_process, started=command_started))
            if sparse_process.returncode != 0:
                raise RuntimeError("published skill sparse checkout setup failed")
            command_started = time.monotonic()
            checkout_process = compact_command(
                ["git", "checkout", "--detach", SKILL_COMMIT], cwd=skill_checkout, timeout_seconds=45
            )
            receipts["commands"].append(command_receipt("git_checkout_pinned_skill_commit", checkout_process, started=command_started))
            if checkout_process.returncode != 0:
                raise RuntimeError("published skill pinned checkout failed")
            revision_process = compact_command(["git", "rev-parse", "HEAD"], cwd=skill_checkout, timeout_seconds=15)
            receipts["commands"].append(command_receipt("git_verify_skill_commit", revision_process, started=time.monotonic()))
            revision = revision_process.stdout.strip()
            if revision != SKILL_COMMIT:
                raise RuntimeError("skill checkout revision did not match pinned commit")
            source_skill = skill_checkout / SKILL_SUBTREE
            if not (source_skill / "SKILL.md").is_file():
                raise RuntimeError("published skill card was absent from pinned subtree")
            shutil.copytree(source_skill, installed_skill)
            install_related = [
                path.relative_to(source_skill).as_posix()
                for path in sorted(source_skill.rglob("*"))
                if path.is_file()
                and (
                    "install" in path.name.casefold()
                    or path.name in {"package.json", "pyproject.toml", "requirements.txt", "setup.py"}
                )
            ]
            skill_files = relative_file_hashes(source_skill)
            script_files = [path for path in sorted(source_skill.rglob("*")) if path.is_file() and path.suffix in {".py", ".sh", ".js", ".cjs", ".mjs"}]
            receipts["skill_acquisition"] = {
                "source": "public Git checkout copied into task-local isolated skill directory",
                "verified_commit": revision,
                "source_file_sha256": skill_files,
                "local_copy_matches_source": relative_file_hashes(installed_skill) == skill_files,
                "install_related_files_inspected": install_related,
                "operational_script_files_inspected": [path.relative_to(source_skill).as_posix() for path in script_files],
                "operational_script_sha256": {path.relative_to(source_skill).as_posix(): sha256_file(path) for path in script_files},
                "skill_scripts_executed": [],
                "unnecessary_scripts_disabled": True,
                "symlinks_present": any(path.is_symlink() for path in source_skill.rglob("*")),
            }

            client = StdioMcpClient(["node", str(entrypoint), str(allowed_root)])
            try:
                client.start()
                initialize = client.request(
                    1,
                    "initialize",
                    {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "shiploop-acquisition-probe", "version": "1.0"},
                    },
                )
                if "error" in initialize:
                    raise RuntimeError("MCP initialize returned a JSON-RPC error")
                protocol = initialize.get("result", {}).get("protocolVersion") if isinstance(initialize.get("result"), dict) else None
                client.notify("notifications/initialized")
                catalog = client.request(2, "tools/list", {})
                tools = catalog.get("result", {}).get("tools", []) if isinstance(catalog.get("result"), dict) else []
                read_tool = next(
                    (
                        tool.get("name")
                        for tool in tools
                        if isinstance(tool, dict) and tool.get("name") == "read_text_file"
                    ),
                    None,
                )
                if not isinstance(read_tool, str):
                    raise RuntimeError("MCP catalog did not expose read_text_file")
                allowed_response = client.request(3, "tools/call", {"name": read_tool, "arguments": {"path": str(allowed_file)}})
                allowed_text = tool_result_text(allowed_response)
                if "error" in allowed_response or not ALLOWED_TEXT in allowed_text:
                    raise RuntimeError("MCP allowed-root read did not return synthetic allowed target")
                fixture_response = client.request(4, "tools/call", {"name": read_tool, "arguments": {"path": str(web_fixture_file)}})
                fixture_text = tool_result_text(fixture_response)
                if "error" in fixture_response or "<html" not in fixture_text.casefold() or 'id="move-piece"' not in fixture_text:
                    raise RuntimeError("MCP did not return the copied existing static HTML fixture for reconnaissance")
                receipts["skill_procedure"] = selected_skill_review(installed_skill, fixture_text, fixture_source_sha256)
                denied_response = client.request(5, "tools/call", {"name": read_tool, "arguments": {"path": str(outside_file)}})
                denied_text = tool_result_text(denied_response)
                denied = "error" in denied_response or bool(denied_response.get("result", {}).get("isError"))
                if not denied or OUTSIDE_TEXT in denied_text:
                    raise RuntimeError("MCP outside-root read was not denied safely")
                transcript = compact_transcript(
                    client.transcript,
                    catalog=catalog,
                    allowed_response=allowed_response,
                    fixture_response=fixture_response,
                    denied_response=denied_response,
                    read_tool=read_tool,
                )
                receipts["mcp_session"] = {
                    "initialized": True,
                    "negotiated_protocol_version": protocol,
                    "catalog_received": True,
                    "read_tool": read_tool,
                    "allowed_read_verified": True,
                    "existing_static_html_read_for_skill_reconnaissance": True,
                    "outside_root_refusal_verified": True,
                    "outside_root_sentinel_disclosed": False,
                }
                receipts["status"] = "completed"
            finally:
                if not transcript:
                    transcript = list(client.transcript)
                receipts["process_cleanup"] = client.close()
                client = None
    except Exception as error:  # receipt must survive expected transport and policy failures
        receipts["failures"].append({"type": type(error).__name__, "message": str(error)})
        receipts["status"] = "blocked_or_failed"
    finally:
        if client is not None:
            receipts["process_cleanup"] = client.close()
        else:
            receipts.setdefault("process_cleanup", {"owned_process_started": False, "owned_process_reaped": True})

    receipts["cleanup"] = {
        "temporary_workspace_removed": temporary_root is not None and not temporary_root.exists(),
        "persistent_artifacts": ["provenance.json", "mcp-transcript.json", "receipt.json", "SUMMARY.md"],
    }
    receipts["elapsed_ms"] = round((time.time() - started_at) * 1000)
    write_json(out_dir / "receipt.json", receipts)
    write_json(out_dir / "mcp-transcript.json", transcript)
    provenance = {
        "mcp": receipts.get("fixed_pins", {}).get("mcp"),
        "mcp_acquisition": receipts.get("mcp_acquisition"),
        "skill": receipts.get("fixed_pins", {}).get("skill"),
        "skill_acquisition": receipts.get("skill_acquisition"),
        "skill_procedure": receipts.get("skill_procedure"),
        "limitations": [
            "Registry metadata, a package checksum, and a Git commit establish source identity for this run; they do not establish ongoing maintainer trust or future compatibility.",
            "The filesystem server was given one synthetic allowed root. A refusal for the sibling synthetic path establishes this tested policy boundary only.",
            "The downloaded skill was read and its static-HTML reconnaissance branch was applied to an existing local fixture through the MCP reader. No model context or browser was launched, so this does not measure automatic skill discovery, model execution, browser outcome quality, or comparative benefit.",
        ],
    }
    write_json(out_dir / "provenance.json", provenance)
    (out_dir / "SUMMARY.md").write_text(build_summary(receipts), encoding="utf-8")
    return receipts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="new, non-symlink evidence directory; its parent must already exist",
    )
    args = parser.parse_args(argv)
    try:
        receipts = run_probe(args.out)
    except OutputDirectoryError as error:
        parser.error(str(error))
    print(json.dumps({"status": receipts["status"], "elapsed_ms": receipts["elapsed_ms"]}, sort_keys=True))
    return 0 if receipts["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
