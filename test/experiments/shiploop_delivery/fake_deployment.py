"""A local, deterministic model of separate delivery observations.

It intentionally does not execute a browser, call a service, or prove a
provider integration. The fixture makes it possible to test that a caller does
not confuse local source, served identity, operation outcome, and consumer UI
behavior while counting forbidden operations independently.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FakeDeployment:
    """Synthetic private source-sync target with an independently observed UI."""

    local_candidate: str
    served_candidate: str
    ui_mode: str = "working"
    operations: list[dict[str, str]] = field(default_factory=list)
    forbidden_operations: int = 0

    def artifact_identity(self) -> dict[str, str]:
        status = "current" if self.served_candidate == self.local_candidate else "stale"
        return {
            "kind": "artifact_identity",
            "status": status,
            "local_candidate": self.local_candidate,
            "served_candidate": self.served_candidate,
        }

    def update(self, operation: str, *, outcome: str = "success") -> dict[str, str]:
        """Record one attempted operation without automatically reconciling it."""
        self.operations.append({"operation": operation, "outcome": outcome})
        if operation != "private-source-sync":
            self.forbidden_operations += 1
            return {"kind": "operation_effect", "status": "forbidden"}
        if outcome == "success":
            self.served_candidate = self.local_candidate
            return {"kind": "operation_effect", "status": "succeeded"}
        if outcome == "unknown":
            return {"kind": "operation_effect", "status": "unknown"}
        return {"kind": "operation_effect", "status": "failed"}

    def consumer_behavior(self) -> dict[str, str]:
        """Observe the consumer separately from source and artifact identity."""
        if self.served_candidate != self.local_candidate:
            return {
                "kind": "consumer_behavior",
                "status": "blocked",
                "reason": "served artifact is stale",
            }
        if self.ui_mode == "login":
            return {
                "kind": "consumer_behavior",
                "status": "blocked",
                "reason": "login boundary prevents interaction",
            }
        if self.ui_mode == "broken":
            return {
                "kind": "consumer_behavior",
                "status": "failed",
                "reason": "visual interaction failed",
            }
        if self.ui_mode == "working":
            return {"kind": "consumer_behavior", "status": "passed"}
        raise ValueError(f"unknown synthetic UI mode: {self.ui_mode}")
