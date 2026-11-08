"""Traceability, explicit-style precedence and scope proxies; semantic fit stays under manual review."""
import json
import os
import re
import sys
from pathlib import Path

if "STAGE_RESULT" not in os.environ:
    raise SystemExit("No accepted stage result is available.")

result = json.loads(Path(os.environ["STAGE_RESULT"]).read_text(encoding="utf-8"))
oracle = Path(os.environ["STAGE_ORACLE"])
contract = json.loads((oracle / "contract.json").read_text(encoding="utf-8"))
tree = Path.cwd()


def fail(message):
    raise SystemExit(message)


def strip_comments(text):
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", text)


def positive_matches(pattern, text):
    text = strip_comments(text)
    matches = []
    for match in re.finditer(pattern, text, re.I):
        before = text[max(0, match.start() - 54):match.start()].lower()
        if re.search(r"\b(?:not|avoid|without|never|do not|don't|no)\b[^.;:]{0,50}$", before):
            continue
        matches.append(match.group(0))
    return matches


COLOR = r"(?:#[0-9a-f]{3,8}\b|\b(?:rgb|rgba|hsl|hsla|oklch|oklab|lab|lch|color)\([^)]*\)|\b(?:black|white|red|green|blue|navy|teal|olive|coral|ivory|beige|tan|maroon|purple|violet|indigo|orange|gold|pink|brown|silver|gray|grey|crimson|salmon|tomato|rebeccapurple|slategray|slategrey|khaki|linen|mintcream|seagreen|steelblue|slateblue|midnightblue|darkslategray|darkslategrey|lightgray|lightgrey|whitesmoke|transparent)\b)"
SIZE = r"\b\d+(?:\.\d+)?(?:rem|px|em|vw|vh|%)\b"


def ui_steps():
    ui_paths = set(contract["ui_paths"])
    visible_work = re.compile(r"\b(?:visual|appearance|style|theme|layout|composition|surface|render|browser|design|interface|panel|strip|board|screen)\b", re.I)
    return [step for step in result.get("steps", []) if isinstance(step, dict)
            and ui_paths.intersection(map(str, step.get("paths", [])))
            and (any(is_visual(text) for text in criteria_for(step)) or visible_work.search(str(step.get("task", ""))))]


def criterion_map():
    return {str(item.get("id")): str(item.get("text", ""))
            for item in result.get("criteria", []) if isinstance(item, dict)}


def criteria_for(step):
    criteria = criterion_map()
    return [criteria[str(ident)] for ident in step.get("criteria", []) if str(ident) in criteria]


def is_visual(text):
    return bool(re.search(r"\b(?:visual|appearance|render(?:ed)?|browser|theme|color|colour|typography|font|layout|composition|surface|responsive|focus|style|retro|pixel)\b", strip_comments(text), re.I))


def decision_ids(texts):
    found = []
    for text in texts:
        found.extend(re.findall(r"\bAD-\d+\b", strip_comments(text)))
    return list(dict.fromkeys(found))


def ad_start(line, ident):
    return bool(re.match(r"^\s*(?:#{2,6}\s+|[-*]\s+|\*\*)?" + re.escape(ident) + r"\b", line))


def ad_block(document, ident):
    lines = strip_comments(document).splitlines()
    start = next((index for index, line in enumerate(lines) if ad_start(line, ident)), None)
    if start is None:
        return ""
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if re.match(r"^\s*(?:#{2,6}\s+|[-*]\s+|\*\*)?AD-\d+\b", line):
            if re.search(r"\bAD-\d+\b", line).group(0) != ident:
                end = index
                break
        if re.match(r"^\s*#{1,2}\s+(?!AD-\d+\b)", line):
            end = index
            break
    return "\n".join(lines[start:end])


def named_sections(block):
    sections = []
    name, body = None, []

    def save():
        if name:
            sections.append((name.strip(), "\n".join(body)))

    for line in block.splitlines()[1:]:
        match = (re.match(r"^\s*#{3,6}\s+(.+?)\s*#*\s*$", line)
                 or re.match(r"^\s*(?:[-*]\s*)?\*\*([^*]+)\*\*\s*:?\s*$", line)
                 or re.match(r"^\s*(?:[-*]\s*)?([A-Za-z][A-Za-z0-9 /&()_-]{2,45})\s*:\s*$", line))
        if match and not re.search(r"\bAD-\d+\b", match.group(1)):
            save()
            name, body = match.group(1), []
        elif name:
            body.append(line)
    save()
    return sections


def selected_record():
    visible = [text for step in ui_steps() for text in criteria_for(step) if is_visual(text)]
    cited = decision_ids(visible)
    if not cited:
        fail("no selected AD is cited by a visual criterion")
    path = tree / "docs/shiploop/architecture.md"
    if not path.is_file():
        fail("docs/shiploop/architecture.md is missing")
    document = path.read_text(encoding="utf-8")
    for ident in cited:
        block = ad_block(document, ident)
        if block:
            return ident, block, document
    fail("the selected AD ID has no matching architecture decision")


def check_record():
    ident, block, _ = selected_record()
    sections = named_sections(block)
    clean = strip_comments(block)
    lower = clean.lower()
    if not sections:
        fail(f"{ident} has no named choice section")
    if not positive_matches(r"\b(?:retro|arcade|pixel)\b", block):
        fail(f"{ident} does not record the explicit retro direction")
    if re.search(r"\b(?:retro|arcade|pixel)\b[^.\n]{0,55}\b(?:not selected|omitted|rejected|excluded|not used|not chosen)\b", lower):
        fail(f"{ident} records the requested retro direction as rejected or omitted")
    if not re.search(r"(?:summary|selection|status)\s+strip\b", lower):
        fail(f"{ident} does not scope its visual choices to the summary strip")
    precedence = re.search(r"\bexplicit\b[^.\n]{0,100}\b(?:retro|arcade|pixel)\b", lower)
    precedence = precedence and re.search(r"\b(?:precedence|prevail|override|takes precedence|wins over|follow the request)\b", lower)
    if not precedence:
        fail(f"{ident} does not explain that the explicit request controls over a default")
    if not re.search(r"\b(?:only|confined|restricted|limited|scoped)\b[^.\n]{0,90}(?:summary|selection|status)\s+strip\b", lower):
        fail(f"{ident} does not limit the treatment to the requested strip")
    if not re.search(r"\b(?:board|controls?|rest of the page)\b[^.\n]{0,100}\b(?:unchanged|preserv|as-is|remain)\b", lower):
        fail(f"{ident} does not preserve the board and surrounding page")
    if len({value.lower() for value in positive_matches(COLOR, block)}) < 2:
        fail(f"{ident} has fewer than two concrete component color anchors")
    if not positive_matches(SIZE, block):
        fail(f"{ident} has no concrete component size or spacing anchor")
    if not re.search(r"\bfont(?:\s+family)?\s*[:=]|\bmonospace\b|\bui-monospace\b", lower):
        fail(f"{ident} has no concrete type choice")
    return ident, block, sections


def normalized(text):
    return re.sub(r"[^a-z0-9]+", " ", strip_comments(text).lower()).strip()


def section_is_cited(name, text):
    label, criterion = normalized(name), normalized(text)
    if label and label in criterion:
        return True
    words = [word for word in label.split() if word not in {"the", "and", "of", "for", "a", "an"}]
    return bool(words) and all(word in criterion.split() for word in words)


def check_trace():
    ident, block, sections = check_record()
    steps = ui_steps()
    if not steps:
        fail("there is no planned step that changes the visible board")

    def trace_problem(text):
        clean = strip_comments(text)
        if ident not in clean or not any(path in clean for path in ("docs/shiploop/architecture.md", "KNOWLEDGE/architecture.md")):
            return "the visual criterion does not cite the selected AD ID and exact knowledge file"
        cited = [(name, body) for name, body in sections if section_is_cited(name, clean)]
        if not cited:
            return "the visual criterion does not name a section in the selected AD"
        if not positive_matches(r"\b(?:retro|arcade|pixel)\b", clean):
            return "the visual criterion omits the explicit requested style"
        section_text = "\n".join(body for _, body in cited)
        criterion_colors = positive_matches(COLOR, clean)
        criterion_sizes = positive_matches(SIZE, clean)
        section_colors = {value.lower() for value in positive_matches(COLOR, section_text)}
        section_sizes = {value.lower() for value in positive_matches(SIZE, section_text)}
        if not any(value.lower() in section_colors for value in criterion_colors):
            return "the visual criterion has no color anchor selected from its AD section"
        if not any(value.lower() in section_sizes for value in criterion_sizes):
            return "the visual criterion has no size anchor selected from its AD section"
        if not re.search(r"\b(?:render|rendered|browser)\b", clean, re.I):
            return "the criterion does not name a rendered observation"
        if not re.search(r"\b(?:mobile|phone|narrow)\b", clean, re.I) or not re.search(r"\b(?:desktop|wide)\b", clean, re.I):
            return "the criterion omits narrow and wide rendered contexts"
        if not re.search(r"(?:summary|selection|status)\s+strip\b", clean, re.I):
            return "the visual criterion does not identify the scoped summary strip"
        return None

    for step in steps:
        visuals = [text for text in criteria_for(step) if is_visual(text)]
        if not visuals:
            fail("a visible-UI step has no criterion for the selected strip choices")
        problems = [trace_problem(text) for text in visuals]
        if not any(problem is None for problem in problems):
            fail("no visual criterion fully selects the strip choices for step " + str(step.get("id")) + ": " + problems[0])


def check_behavior():
    """Lexical behavior-presence proxy; node:test remains a separate check."""
    texts = [strip_comments(str(item.get("text", ""))) for item in result.get("criteria", []) if isinstance(item, dict)]
    combined = " ".join(texts).lower()
    if not all(token in combined for token in ("coordinate", "reset", "choose a square")):
        fail("criteria omit selected-coordinate and reset-to-empty behavior")
    if not re.search(r"\b(?:selection|selected)\b", combined):
        fail("criteria omit board selection behavior")
    paths = {str(path) for step in result.get("steps", []) if isinstance(step, dict) for path in step.get("paths", [])}
    if "test/board-state.test.mjs" not in paths:
        fail("the plan omits the existing board state test path")
    commands = [str(item.get("command", "")) for item in result.get("test_commands", []) if isinstance(item, dict)]
    if not any("node --test" in command for command in commands):
        fail("the plan omits the existing node:test suite")


def check_scope():
    """Path and phrasing proxy; it cannot establish semantic plan-scope coverage."""
    allowed = set(contract["allowed_paths"])
    paths = set(map(str, result.get("paths", [])))
    paths |= {str(path) for step in result.get("steps", []) if isinstance(step, dict) for path in step.get("paths", [])}
    outside = sorted(paths - allowed)
    if outside:
        fail("planned paths go beyond the summary feature and design record: " + ", ".join(outside))
    missing = sorted(set(contract["required_paths"]) - paths)
    if missing:
        fail("plan omits an expected feature or test path: " + ", ".join(missing))
    plans = " ".join(str(step.get("task", "")) for step in result.get("steps", []) if isinstance(step, dict))
    active_external = positive_matches(r"\b(?:add|build|create|introduce|wire|call|depend on)\b[^.\n]{0,65}\b(?:remote service|server|api|package dependency|network service|backend)\b", plans)
    if active_external:
        fail("the plan adds an external or unrelated service")


checks = {"P1": check_record, "P2": check_trace, "C1": check_behavior, "C2": check_scope}
if len(sys.argv) != 2 or sys.argv[1] not in checks:
    fail("usage: check_plan.py P1|P2|C1|C2")
checks[sys.argv[1]]()
