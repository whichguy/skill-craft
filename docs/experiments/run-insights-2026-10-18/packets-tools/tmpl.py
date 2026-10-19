"""Prototype of the strict template loader, validator and renderer (analysis tool; not ShipLoop code).

    python3 -I tmpl.py validate <template> <partials_dir>
    python3 -I tmpl.py render <template> <partials_dir> <values.json> <out.md> <report.json>

Template = front matter (flags, slots, rows, result tables) + body of fixed text with {{slot}}, {{> partial}},
{{#if flag}}...{{/if}} / {{#if !flag}}...{{/if}}. HTML comments are provenance notes and never print. The printed region
ends at the first line starting "<!-- appendix"; the rest is the file appendix.
"""
import itertools
import json
import re
import sys
from pathlib import Path

HEAD_END = "=== end ShipLoop head ==="
SLOT = re.compile(r"\{\{([a-z_]+)\}\}")
PARTIAL = re.compile(r"\{\{> ([a-z-]+)\}\}")
IF = re.compile(r"\{\{#if (!?)([a-z_]+)\}\}(.*?)\{\{/if\}\}", re.S)
COMMENT = re.compile(r"[ \t]*<!--.*?-->[ \t]*(\n)?", re.S)


class TemplateError(Exception):
    pass


def _table(lines, start):
    rows = []
    i = start
    while i < len(lines) and lines[i].startswith("|"):
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", lines[i].strip())[1:-1]]
        if not set("".join(cells)) <= set("-: "):
            rows.append([c.replace("\\|", "|") for c in cells])
        i += 1
    return rows[1:], i  # drop the header row


def parse(path: Path):
    text = path.read_text()
    if not text.startswith("---\n"):
        raise TemplateError(f"{path.name}: no front matter")
    end = text.index("\n---\n", 4)
    head, body = text[4:end].split("\n"), text[end + 5:]
    meta, tables = {}, {}
    i = 0
    while i < len(head):
        line = head[i]
        m = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if m and m.group(1) in ("flags", "slots", "rows", "result", "pools", "gates"):
            rows, i = _table(head, i + 1)
            tables[m.group(1)] = rows
            continue
        if m:
            meta[m.group(1)] = m.group(2)
        i += 1
    slots = {r[0]: {"kind": r[1], "source": r[2], "bound": r[3], "over": r[4],
                    "pool": (r[5] if len(r) > 5 and r[5] not in ("", "-") else None)} for r in tables.get("slots", [])}
    # A pool's size is fixed ("3000") or elastic ("rest>=800"): an elastic pool gets what the print budget leaves after
    # every other line is rendered, never less than its minimum; the static budget counts the minimum.
    meta["pools"] = {r[0]: (int(r[1].split(">=")[1]) if r[1].startswith("rest") else int(r[1])) for r in tables.get("pools", [])}
    meta["elastic"] = {r[0] for r in tables.get("pools", []) if r[1].startswith("rest")}
    flags = {r[0]: r[1] for r in tables.get("flags", [])}
    rows = {r[0]: r[1].strip("`") for r in tables.get("rows", [])}
    meta["gates"] = [{"gate": r[0], "refusal": r[1], "anchor": r[2]} for r in tables.get("gates", [])]
    meta["requires"] = [x.strip() for x in meta.get("requires", "").split(" · ") if x.strip()]
    return meta, slots, flags, rows, tables.get("result", []), body


# A form placeholder: <...> with at most one nested <...> (for example "<R-<n> or AD-<n> this item follows>").
PLACEHOLDER = re.compile(r"<[^<>\n]*(?:<[^<>\n]*>[^<>\n]*)*>")
RESULT_HEAD = "== Result form"


def form_placeholders(printed: str) -> list[str]:
    """Every <...> string the Result form section and its outcome shapes print: the exact strings the gate's placeholder
    registry must refuse (template review SP-5, F17: never a <...> regex, because real results hold XML)."""
    section = printed.split(RESULT_HEAD, 1)[1] if RESULT_HEAD in printed else ""
    section = section.split("=== appendix (file only) ===")[0]
    return sorted(set(PLACEHOLDER.findall(section)))


# N5 names for today's stage_spec outcomes; repeat is dropped.
N5 = {"done": "done", "blocked": "blocked", "revise": "send-back", "replan": "add-work"}


def outcome_check(name: str, full: str) -> list[str]:
    """The outcome partials a template includes must be exactly the stage's outcomes in stage_spec, under N5 names."""
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "skills/shiploop/scripts"))
    try:
        import shiploop_stage_spec as spec
    except ImportError:
        return ["stage_spec not importable; outcome check skipped"]
    if name not in spec.STAGES:
        return []
    want = {N5[o] for o in spec.stage(name).outcomes if o in N5}
    have = set(re.findall(r"\{\{> outcome-([a-z-]+)\}\}", full))
    return [] if want == have else [f"outcome partials {sorted(have)} differ from stage_spec {sorted(want)} (N5 names)"]


# Install lengths a bound may name: the run directory, the skill package root and the CLI path (test/shiploop_head_budget.py
# reference install: 83, 63, 96).
REFERENCE_INSTALL = {"run": 83, "root": 63, "cli": 96}
# What a pooled slot prints when its pool is spent: a one-line pointer to its source (counted in the static budget).
POINTER_ALLOWANCE = 110


def bound_of(spec: dict, install: dict) -> int:
    """A slot's bound: an integer, or a sum of install lengths and integers (``cli+run+74``)."""
    total = 0
    for term in str(spec["bound"]).split("+"):
        term = term.strip()
        total += install[term] if term in install else int(term)
    return total


def expand(body: str, partials: Path, seen=()):
    def sub(m):
        name = m.group(1)
        f = partials / (name + ".md")
        if name in seen or not f.is_file():
            raise TemplateError(f"unknown or recursive partial {name!r}")
        return expand(f.read_text().rstrip("\n"), partials, seen + (name,))
    return PARTIAL.sub(sub, body)


WHOLE_LINE_COMMENT = re.compile(r"(?m)^[ \t]*<!--.*?-->[ \t]*\n", re.S)


def strip_comments(text: str) -> str:
    """Remove provenance comments: a comment on its own line with its line, an inline one with its leading space."""
    return COMMENT.sub(lambda m: m.group(1) or "", WHOLE_LINE_COMMENT.sub("", text))


def apply_flags(text: str, flags: dict) -> str:
    while True:
        new = IF.sub(lambda m: m.group(3) if bool(flags[m.group(2)]) != bool(m.group(1)) else "", text)
        if new == text:
            return new
        text = new


def validate(path: Path, partials: Path, install: dict = REFERENCE_INSTALL) -> dict:
    meta, slots, flags, rows, result, body = parse(path)
    problems = outcome_check(path.name.split(".")[0], body)
    full = expand(body, partials)
    used_flags = {m.group(2) for m in IF.finditer(full)}
    for f in used_flags - set(flags):
        problems.append(f"undeclared flag {f}")
    for f in set(flags) - used_flags:
        problems.append(f"declared flag never used {f}")
    used = set(SLOT.findall(strip_comments(full)))
    for s in used - set(slots):
        problems.append(f"unknown slot {{{{{s}}}}}")
    for s in set(slots) - used:
        problems.append(f"declared slot never used {s}")
    for name, spec in slots.items():
        if spec["kind"] not in ("scalar", "cmd", "block", "include"):
            problems.append(f"slot {name}: unknown kind {spec['kind']}")
        if spec["over"] not in ("refuse", "excerpt", "toc"):
            problems.append(f"slot {name}: unknown over policy {spec['over']}")
        if spec["pool"] and (spec["pool"] not in meta["pools"] or spec["over"] == "refuse"):
            problems.append(f"slot {name}: pool {spec['pool']} undeclared, or a refuse slot in a pool")
        if spec["kind"] == "include" and spec["over"] == "refuse" and "producer bound" not in spec["source"]:
            problems.append(f"slot {name}: a refuse-class include must name the producer gate that bounds it")
        if spec["kind"] == "block" and "row " in spec["source"]:
            row = spec["source"].split("row ")[1].split()[0].rstrip(",;")
            if row not in rows:
                problems.append(f"slot {name}: unknown row {row}")
    # static budget: the printed region's fixed text plus every slot's bound, over every flag combination
    worst = 0
    combos = []
    for values in itertools.product([False, True], repeat=len(flags)):
        fl = dict(zip(flags, values))
        printed = strip_comments(apply_flags(full, fl)).split("<!-- appendix")[0]
        printed = printed.split("=== appendix (file only) ===")[0]
        fixed = len(SLOT.sub("", printed))
        names = [s for s in SLOT.findall(printed) if s in slots]
        # Plan 8.5: a refuse-class slot prints whole at most its bound; any other slot can always shrink to a one-line
        # pointer, which the renderer does (last in body order first) before a print would pass its budget.
        bound = sum(bound_of(slots[s], install) for s in names if slots[s]["over"] == "refuse")
        bound += sum(min(bound_of(slots[s], install), POINTER_ALLOWANCE) for s in names if slots[s]["over"] != "refuse")
        total = fixed + bound + len(HEAD_END) + 1
        combos.append({"flags": fl, "fixed": fixed, "slot_bounds": bound, "max_printed": total})
        worst = max(worst, total)
    budget = int(meta.get("print_budget", "0") or 0)
    if worst > budget:
        problems.append(f"static budget: max printed {worst} > print_budget {budget}")
    printed_all = strip_comments(apply_flags(full, {f: True for f in flags}))
    return {"template": path.name, "slots": len(slots), "flags": list(flags), "requires": meta["requires"],
            "problems": problems, "placeholders": form_placeholders(printed_all), "gates": len(meta["gates"]),
            "combos": combos, "max_printed": worst, "print_budget": budget}


def _cut(text: str, bound: int, over: str, locator: str) -> tuple[str, str]:
    if len(text) <= bound:
        return text, "whole"
    if over == "refuse":
        raise TemplateError(f"value of {len(text)} characters over its bound {bound} ({locator})")
    if over == "toc":
        heads = "\n".join(l for l in text.splitlines() if l.startswith("#"))
        toc = (heads + "\n" if heads else "") + f"[headings only; whole: {locator}]"
        if len(toc) <= bound:
            return toc, "toc"
    tail = f" [excerpt; whole: {locator}]"
    room = bound - len(tail)
    if room < 80:
        pointer = f"[not quoted: the packet's budget is spent; read {locator}]"
        return (text, "whole") if len(text) <= len(pointer) else (pointer, "pointer")
    cut = text[:room]
    stop = max(cut.rfind(". "), cut.rfind(".\n"), cut.rfind("\n"))
    cut = cut[: stop + 1] if stop > room // 2 else cut
    return cut.rstrip() + tail, "excerpt"


def render(path: Path, partials: Path, values: dict) -> tuple[str, dict]:
    install = values.get("install", REFERENCE_INSTALL)
    meta, slots, flags, rows, result, body = parse(path)
    for name, bound in values.get("bound_overrides", {}).items():
        slots[name] = {**slots[name], "bound": str(bound)}
    full = strip_comments(apply_flags(expand(body, partials), values["flags"]))
    report = {}
    left = dict(meta["pools"])
    if meta["elastic"]:
        # first pass: everything but the pooled slots, to learn what the budget leaves for the elastic pools
        probe = {**values, "slots": {k: ("" if slots.get(k, {}).get("pool") else v) for k, v in values["slots"].items()}}
        probe_meta_pools = {p: 10**9 for p in meta["pools"]}
        printed0 = _render_text(full, slots, rows, probe, install, probe_meta_pools, {})[0].split("=== appendix (file only) ===")[0]
        pooled = len([s for s in SLOT.findall(full.split("=== appendix (file only) ===")[0]) if slots[s]["pool"]])
        rest = int(meta.get("print_budget", "0")) - len(printed0) - len(HEAD_END) - 1 - POINTER_ALLOWANCE * pooled
        for p in meta["elastic"]:
            left[p] = max(meta["pools"][p], rest)
    text, report = _render_text(full, slots, rows, values, install, left, report)
    budget = int(meta.get("print_budget", "0") or 0)
    order = [n for n in dict.fromkeys(SLOT.findall(full.split("=== appendix (file only) ===")[0]))
             if slots[n]["over"] != "refuse" and not slots[n]["pool"]]
    shrunk = []
    while budget and not values.get("allow_over_budget") and order and \
            len(text.split("=== appendix (file only) ===")[0]) + len(HEAD_END) + 1 > budget:
        name = order.pop()
        slots[name] = {**slots[name], "bound": str(POINTER_ALLOWANCE)}
        shrunk.append(name)
        report = {}
        text, report = _render_text(full, slots, rows, values, install, dict(left), report)
    if "{{" in text:
        raise TemplateError("unrendered marker left: " + text[text.index("{{"):][:60])
    printed, _, appendix = text.partition("=== appendix (file only) ===")
    printed = re.sub(r"\n{3,}", "\n\n", printed).rstrip("\n") + "\n" + HEAD_END + "\n"
    whole = printed + "=== appendix (file only) ===" + appendix
    budget = int(meta.get("print_budget", "0") or 0)
    over = len(printed) - budget if budget and len(printed) > budget else 0
    if over and not values.get("allow_over_budget"):
        raise TemplateError(f"printed {len(printed)} characters, {over} over print_budget {budget}")
    missing = [g["gate"] for g in meta["gates"] if g["anchor"] not in printed]
    if missing:
        raise TemplateError("gate anchors missing from the print: " + ", ".join(missing))
    return whole, {"printed_chars": len(printed), "file_chars": len(whole), "pools": left, "slots": report,
                   "bound_overrides": values.get("bound_overrides", {}), "gates_anchored": len(meta["gates"]),
                   "placeholders": form_placeholders(printed), "over_budget": over, "shrunk_to_pointer": shrunk}


def _render_text(full, slots, rows, values, install, left, report):

    def fill(m):
        name = m.group(1)
        spec = slots[name]
        if name not in values["slots"]:
            raise TemplateError(f"slot {name} left unfilled")
        v = values["slots"][name]
        locator = values.get("locators", {}).get(name, spec["source"])
        if spec["kind"] == "block":
            fmt = rows[spec["source"].split("row ")[1].split()[0].rstrip(",;")] if "row " in spec["source"] else "{text}"
            joiner = "\n" if fmt.startswith(("- ", "  ")) else "; "
            text = joiner.join(fmt.format(**row) for row in v) if isinstance(v, list) else str(v)
            text = text or "none"
        else:
            text = str(v)
        own = bound_of(spec, install)
        bound = own if not spec["pool"] else min(own, left[spec["pool"]])
        out, how = _cut(text, bound, spec["over"], locator)
        if spec["pool"]:
            left[spec["pool"]] -= len(out)
        report[name] = {"kind": spec["kind"], "chars": len(out), "source_chars": len(text), "bound": own,
                        "pool": spec["pool"], "rendered": how}
        return out

    return SLOT.sub(fill, full), report


def main():
    cmd, tpl, partials = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    if cmd == "validate":
        print(json.dumps(validate(tpl, partials), indent=1))
        return
    values = json.loads(Path(sys.argv[4]).read_text())
    whole, rep = render(tpl, partials, values)
    Path(sys.argv[5]).write_text(whole)
    rep["validate_reference_install"] = validate(tpl, partials)
    rep["validate_this_install"] = validate(tpl, partials, values.get("install", REFERENCE_INSTALL))
    Path(sys.argv[6]).write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: rep[k] for k in ("printed_chars", "file_chars")}))


if __name__ == "__main__":
    main()
