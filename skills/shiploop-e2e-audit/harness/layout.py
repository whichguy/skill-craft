"""Resolve the bundled audit harness without searching for source checkouts.

The audit package is portable. Its harness always lives beside this module;
the separately installed ShipLoop skill remains the selected subject under
test. A source sibling is only a development default when this package is in
the canonical ``<checkout>/skills/shiploop-e2e-audit`` layout.
"""
from __future__ import annotations

from pathlib import Path


HARNESS_ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = HARNESS_ROOT.parent
HOST_DEFAULT_SKILL_ROOT = Path.home() / ".grok" / "skills" / "shiploop"
_selected_skill_root: Path | None = None


def within(child: Path, parent: Path) -> bool:
    """Return whether a resolved path is contained by another resolved path."""
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def canonical_source_checkout() -> Path | None:
    """Return the adjacent source checkout only for its exact canonical layout.

    This deliberately performs no upward walk or name-based checkout search.
    A copied marketplace package has no source-checkout default even if it is
    placed beneath an arbitrary directory named ``skills``.
    """
    skills_directory = PACKAGE_ROOT.parent
    if skills_directory.name != "skills" or not (PACKAGE_ROOT / "SKILL.md").is_file():
        return None
    checkout = skills_directory.parent
    expected_harness = checkout / "skills" / "shiploop-e2e-audit" / "harness"
    legacy_harness = checkout / "test" / "experiments" / "shiploop_e2e"
    if (expected_harness.resolve() != HARNESS_ROOT or not (checkout / ".git").exists()
            or not legacy_harness.exists() or legacy_harness.resolve() != HARNESS_ROOT):
        return None
    return checkout.resolve()


def default_skill_binding() -> tuple[Path, str]:
    """Return the portable default and the reason it was selected."""
    checkout = canonical_source_checkout()
    if checkout is not None:
        sibling = checkout / "skills" / "shiploop"
        if (sibling / "SKILL.md").is_file():
            return sibling.resolve(), "source-sibling"
    return HOST_DEFAULT_SKILL_ROOT.expanduser().resolve(), "installed-skill-dir"


def default_skill_root() -> Path:
    """Choose the source sibling only for canonical development checkouts."""
    return default_skill_binding()[0]


def set_selected_skill_root(root: Path | None) -> None:
    """Temporarily bind fixture tests to one independently selected subject."""
    global _selected_skill_root
    _selected_skill_root = None if root is None else Path(root).expanduser().resolve()


def selected_skill_root() -> Path:
    """Return the temporary suite binding or the portable default."""
    return _selected_skill_root or default_skill_root()


def selected_skill_binding() -> tuple[Path, str]:
    """Return the temporary suite binding or a portable default with its reason."""
    if _selected_skill_root is not None:
        return _selected_skill_root, "suite-selected"
    return default_skill_binding()


def resolve_skill_root(value: Path | str | None) -> Path:
    """Resolve an explicit subject root, preserving explicit-over-default order."""
    if value is None:
        return selected_skill_root()
    return Path(value).expanduser().resolve()


def resolve_skill_binding(value: Path | str | None) -> tuple[Path, str]:
    """Resolve an explicit subject root and preserve its selection provenance."""
    if value is None:
        return selected_skill_binding()
    return Path(value).expanduser().resolve(), "explicit"


def protected_roots(subject_root: Path | None = None) -> list[Path]:
    """Execution inputs that a trial must not use as product or output space."""
    protected = [PACKAGE_ROOT]
    checkout = canonical_source_checkout()
    if checkout is not None:
        protected.append(checkout)
    if subject_root is not None:
        protected.append(Path(subject_root).expanduser().resolve())
    return protected


def validate_external_product(path: Path | str, *, subject_root: Path | None = None) -> Path:
    """Reject product roots that contain or are contained by execution inputs."""
    product = Path(path).expanduser().resolve()
    if any(within(product, root) or within(root, product) for root in protected_roots(subject_root)):
        raise ValueError("product must be separate from the audit package, source checkout, and selected ShipLoop subject")
    return product


def validate_new_external_output(path: Path | str, *, subject_root: Path | None = None) -> Path:
    """Reject output that could modify the audit package, source, or subject."""
    output = Path(path).expanduser().resolve()
    if output.exists():
        raise ValueError("output must be a new directory")
    protected = protected_roots(subject_root)
    if any(within(output, root) for root in protected):
        raise ValueError("output must be outside the audit package, source checkout, and selected ShipLoop subject")
    return output
