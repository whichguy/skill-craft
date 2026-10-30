"""The concern map (run-insights A1, build plan S2.2): which SDLC concerns each work item touches, decided at plan,
mapped to steps at step-plan.

The run analysis found the step plan's concern surface (duty 9, a free-text plan record) ungated and skipped or
compressed in all four step-plan results it read, while concerns such as concurrency and accessibility were dropped
on the way to code.  So the plan writes, per work item, one short row for every concern in ``CONCERNS``: does it
apply, and if so the decision, where it is anchored (an R-<n>, AD-<n> or file) and the stage that owns it; if not,
why.  The step plan maps every applicable row it owns to the steps that deliver it.  ShipLoop checks the structure
only: whether a decision is good is the review's question, not the gate's.

Plan result::

    "concerns": {"W1": [{"id": "ui", "applies": "yes", "decision": "...", "anchor": "R-3", "owner_stage": "step-plan"},
                        {"id": "messaging", "applies": "no", "reason": "..."}, ...]}

Step-plan result::

    "concerns": [{"id": "ui", "steps": ["S1", "S2"]}]

Items added after the plan (carry-forward or add-work) have no rows, and their step plans map none.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

# The fifteen concerns, each with the one-line question the plan answers for it.
CONCERNS = (
    ("ui", "screens, controls and layout the user sees"),
    ("api", "interfaces other code or systems call"),
    ("messaging", "events, queues and notifications"),
    ("state", "stored or shared state and who owns it"),
    ("migrate-before", "data or schema changes that must land before release"),
    ("migrate-after", "cleanup that follows the release"),
    ("switchover", "how the change reaches its users: deploy, flags, access"),
    ("concurrency", "simultaneous actions and their ordering"),
    ("platform-services", "the platform's own services the item reuses"),
    ("scale", "volume and platform limits"),
    ("security", "access, secrets and least privilege"),
    ("observability", "logs, errors and monitoring"),
    ("config", "configuration and pinned versions"),
    ("performance", "speed and resource budgets"),
    ("accessibility", "names, keyboard use, contrast and screen readers"),
)
CONCERN_IDS = tuple(name for name, _ in CONCERNS)
# The stages that can own an applicable concern: step-plan maps it to steps; a later stage delivers it there.
OWNER_STAGES = ("step-plan", "test", "document", "system-test-author", "release-plan", "operations")
# The print budget of one work item's applicable rows as the step-plan packet prints them (run-insights T-D2).  No gate
# refuses longer rows (owner, 2026-10-28, plan F2): past the budget the packet prints the rows that fit and names the
# run file that holds them all (shiploop_navigator._concern_lines, shiploop_fields).
ROWS_PRINT = 1_200


class ConcernError(ValueError):
    """A concern map ShipLoop refuses; the message names the row and the fix."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ConcernError(message)


def _text(value: Any, label: str) -> str:
    _need(isinstance(value, str) and value.strip() != "", label + " must be a nonempty string")
    return " ".join(value.split())


def canonical_plan(value: Any) -> Dict[str, List[Dict[str, str]]]:
    """A plan's ``concerns`` in canonical form: every item lists every concern once, in ``CONCERNS`` order."""
    _need(isinstance(value, Mapping) and value, "concerns is an object keyed by work item ID, each a list of rows")
    out: Dict[str, List[Dict[str, str]]] = {}
    for item, rows in value.items():
        _need(isinstance(rows, list), f"concerns for {item} must be a list of rows")
        seen: Dict[str, Dict[str, str]] = {}
        for raw in rows:
            _need(isinstance(raw, Mapping), f"each concern row for {item} is an object")
            name = raw.get("id")
            _need(name in CONCERN_IDS, f"{item}: unknown concern {name!r}; the concerns are " + ", ".join(CONCERN_IDS))
            _need(name not in seen, f"{item}: concern {name} is listed twice")
            applies = raw.get("applies")
            if applies == "yes":
                _need(set(raw) == {"id", "applies", "decision", "anchor", "owner_stage"},
                      f"{item}: an applicable concern row is {{id, applies: yes, decision, anchor, owner_stage}} "
                      f"({name})")
                owner = raw.get("owner_stage")
                _need(owner in OWNER_STAGES, f"{item}: concern {name}'s owner_stage must be one of "
                      + ", ".join(OWNER_STAGES))
                row = {"id": name, "applies": "yes", "decision": _text(raw.get("decision"), f"{item} {name} decision"),
                       "anchor": _text(raw.get("anchor"), f"{item} {name} anchor"), "owner_stage": str(owner)}
            elif applies == "no":
                _need(set(raw) == {"id", "applies", "reason"},
                      f"{item}: a concern that does not apply is {{id, applies: no, reason}} ({name})")
                row = {"id": name, "applies": "no", "reason": _text(raw.get("reason"), f"{item} {name} reason")}
            else:
                raise ConcernError(f"{item}: concern {name}'s applies must be yes or no")
            seen[str(name)] = row
        missing = [name for name in CONCERN_IDS if name not in seen]
        _need(not missing, f"{item}: every concern needs a row (applies yes or no); missing: " + ", ".join(missing))
        out[str(item)] = [seen[name] for name in CONCERN_IDS]
    return out


def check_plan(concerns: Mapping[str, Sequence[Mapping[str, str]]], item_ids: Sequence[str]) -> None:
    """Every work item of the queue has its rows, and no other item has any.  Rows of any length are accepted."""
    missing = [item for item in item_ids if item not in concerns]
    _need(not missing, "a done plan maps every concern for every work item: concerns lacks " + ", ".join(missing))
    extra = sorted(set(concerns) - set(item_ids))
    _need(not extra, "concerns names items that are not in work_items: " + ", ".join(extra))


def owned_rows(plan_concerns: Mapping[str, Sequence[Mapping[str, str]]], item: str) -> List[Mapping[str, str]]:
    """The applicable rows of ``item`` that its step plan maps to steps."""
    return [row for row in plan_concerns.get(item, ()) if row.get("applies") == "yes"
            and row.get("owner_stage") == "step-plan"]


def canonical_step_plan(value: Any) -> List[Dict[str, Any]]:
    """A step plan's ``concerns``: ``[{"id", "steps"}]``, each concern once."""
    _need(isinstance(value, list), 'concerns is a list of {"id": "<concern>", "steps": ["S1"]}')
    out: List[Dict[str, Any]] = []
    seen = set()
    for raw in value:
        _need(isinstance(raw, Mapping) and set(raw) == {"id", "steps"},
              'each step-plan concern row is {"id": "<concern>", "steps": ["<step id>", ...]}')
        name = raw.get("id")
        _need(name in CONCERN_IDS, f"unknown concern {name!r}")
        _need(name not in seen, f"concern {name} is mapped twice")
        steps = raw.get("steps")
        _need(isinstance(steps, list) and steps and all(isinstance(step, str) and step for step in steps),
              f"concern {name}'s steps must name at least one step")
        seen.add(name)
        out.append({"id": name, "steps": list(steps)})
    return out


def check_step_plan(mapped: Sequence[Mapping[str, Any]], owned: Sequence[Mapping[str, str]],
                    step_ids: Sequence[str], item: str) -> None:
    """Every concern the plan gave this step plan is mapped to its steps, and nothing else is."""
    want = [row["id"] for row in owned]
    got = {row["id"]: row["steps"] for row in mapped}
    unmapped = [name for name in want if name not in got]
    _need(not unmapped, f"{item}'s plan gives this step plan concerns no step delivers: " + ", ".join(unmapped)
          + '. Map each to the steps that deliver it in concerns: [{"id": "<concern>", "steps": ["S1"]}]')
    stray = [name for name in got if name not in want]
    _need(not stray, "concerns maps concerns the plan does not give this step plan: " + ", ".join(stray))
    for name, steps in got.items():
        unknown = [step for step in steps if step not in step_ids]
        _need(not unknown, f"concern {name} names steps the result does not list: " + ", ".join(unknown))


def packet_lines(plan_concerns: Mapping[str, Sequence[Mapping[str, str]]], item: str) -> List[str]:
    """The step-plan packet's lines for ``item``: its applicable rows, by value; none when the plan wrote none."""
    rows = [row for row in plan_concerns.get(item, ()) if row.get("applies") == "yes"]
    if not rows:
        return []
    lines = ["Concerns the plan decided for " + item + " (map each owned by step-plan to the steps that deliver it):"]
    lines += ["- " + row["id"] + ": " + row["decision"] + " (" + row["anchor"] + "; owner " + row["owner_stage"] + ")"
              for row in rows]
    return lines


__all__ = ("CONCERNS", "CONCERN_IDS", "ConcernError", "OWNER_STAGES", "ROWS_PRINT", "canonical_plan",
           "canonical_step_plan", "check_plan", "check_step_plan", "owned_rows", "packet_lines")
