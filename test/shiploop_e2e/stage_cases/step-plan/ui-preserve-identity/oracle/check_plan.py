"""Proxies for recording and selecting the current chat identity; visual quality stays under manual review."""
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
        after = text[match.end():match.end() + 56].lower()
        if re.search(r"\b(?:not|avoid|without|never|do not|don't|no)\b[^.;:]{0,50}$", before):
            continue
        if re.match(r"\s*(?:is\s+)?(?:not selected|not used|not chosen|omitted|rejected|excluded)\b", after):
            continue
        matches.append(match.group(0))
    return matches


COLOR = r"(?:#[0-9a-f]{3,8}\b|\b(?:rgb|rgba|hsl|hsla|oklch|oklab|lab|lch|color)\([^)]*\)|\b(?:black|white|red|green|blue|navy|teal|olive|coral|ivory|beige|tan|maroon|purple|violet|indigo|orange|gold|pink|brown|silver|gray|grey|crimson|salmon|tomato|rebeccapurple|slategray|slategrey|khaki|linen|mintcream|seagreen|steelblue|slateblue|midnightblue|darkslategray|darkslategrey|lightgray|lightgrey|whitesmoke|transparent)\b)"
SIZE = r"\b\d+(?:\.\d+)?(?:rem|px|em|vw|vh|%)\b"
UNREAD_INDICATOR = r"\b(?:unread(?:[- ]count)?[ -](?:badges?|markers?)|unread[- ]counts?)\b"


def ui_steps():
    ui_paths = set(contract["ui_paths"])
    visible_work = re.compile(r"\b(?:visual|appearance|style|theme|layout|composition|surface|render|browser|design|interface|badge|count marker|screen|pane)\b", re.I)
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
    return bool(re.search(r"\b(?:visual|appearance|render(?:ed)?|browser|theme|color|colour|typography|font|layout|composition|surface|responsive|focus|style|token)\b", strip_comments(text), re.I))


def decision_ids(texts):
    found = []
    for text in texts:
        found.extend(re.findall(r"\bAD-\d+\b", strip_comments(text)))
    return list(dict.fromkeys(found))


def ad_start(line, ident):
    prefix = r"^\s*(?:(?:#{2,6}\s+)|(?:[-*]\s+))?(?:\*\*)?"
    return bool(re.match(prefix + re.escape(ident) + r"\b", line))


def ad_block(document, ident):
    lines = strip_comments(document).splitlines()
    start = next((index for index, line in enumerate(lines) if ad_start(line, ident)), None)
    if start is None:
        return ""
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if re.match(r"^\s*(?:(?:#{2,6}\s+)|(?:[-*]\s+))?(?:\*\*)?AD-\d+\b", line):
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
        heading = re.match(r"^\s*#{3,6}\s+(.+?)\s*#*\s*$", line)
        bold_label = re.match(r"^\s*(?:[-*]\s*)?\*\*([^*]+)\*\*\s*:?\s*(.*?)\s*$", line)
        plain_label = re.match(r"^\s*(?:[-*]\s*)?([A-Za-z][A-Za-z0-9 /&()_-]{2,45})\s*:\s*(.*?)\s*$", line)
        match = heading or bold_label or plain_label
        if match and not re.search(r"\bAD-\d+\b", match.group(1)):
            save()
            name = match.group(1)
            inline_body = (bold_label or plain_label).group(2).strip() if (bold_label or plain_label) else ""
            body = [inline_body] if inline_body else []
        elif name:
            body.append(line)
    save()
    return sections


def source_css():
    path = tree / "styles.css"
    if not path.is_file():
        fail("the established product stylesheet is missing")
    return strip_comments(path.read_text(encoding="utf-8"))



def component_selectors(css):
    names = set(re.findall(r"(?<![\w-])\.([A-Za-z][A-Za-z0-9_-]*)", css))
    return [name for name in sorted(names)
            if re.search(r"(?:conversation|message|thread|composer)", name, re.I)]


def component_is_named(name, text):
    return bool(re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", strip_comments(text), re.I))


def color_values(text):
    return {value.lower() for value in positive_matches(COLOR, text)}


def has_badge_composition(text):
    clean = strip_comments(text).lower()
    if not re.search(UNREAD_INDICATOR, clean):
        return False
    subject = r"\b(?:conversation[- ](?:rows?|items?|list|grid)|(?:rows?|items?) of (?:the )?conversations?)\b"
    placement = r"\b(?:trailing|right|end|align(?:ed|ment)?|place(?:d|ment)?|beside|alongside|within|inside)\b"
    return bool(re.search(subject + r"[^.;:\n]{0,110}" + placement, clean)
                or re.search(placement + r"[^.;:\n]{0,110}" + subject, clean))


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
    lower = strip_comments(block).lower()
    if not sections:
        fail(f"{ident} has no named choice section")
    if not re.search(UNREAD_INDICATOR, lower):
        fail(f"{ident} does not record the authorized unread badge/marker delta")
    if not re.search(r"\b(?:only|limited|confined|authorized delta|small delta)\b[^.\n]{0,100}\b(?:unread|badge)", lower):
        fail(f"{ident} does not limit the decision to the unread-badge feature")
    css = source_css()
    existing_colors = color_values(css)
    reused_colors = existing_colors & color_values(block)
    if len(reused_colors) < 2:
        fail(f"{ident} does not reuse at least two existing stylesheet colors")
    selectors = component_selectors(css)
    reused_components = [name for name in selectors if component_is_named(name, block)]
    if len(reused_components) < 2:
        fail(f"{ident} does not retain at least two existing chat components")
    source_sizes = {value.lower() for value in positive_matches(SIZE, css)}
    ad_sizes = {value.lower() for value in positive_matches(SIZE, block)}
    if not source_sizes.intersection(ad_sizes) and not has_badge_composition(block):
        fail(f"{ident} has neither a current numeric size anchor nor a concrete unread-count placement")
    # Numeric and composition anchors are lexical proxies; whether the choices sufficiently preserve identity remains manual.
    return ident, block, sections, reused_colors, reused_components


def normalized(text):
    return re.sub(r"[^a-z0-9.#_-]+", " ", strip_comments(text).lower()).strip()


def section_is_cited(name, text):
    label, criterion = normalized(name), normalized(text)
    if label and label in criterion:
        return True
    words = [word for word in label.split() if word not in {"the", "and", "of", "for", "a", "an"}]
    return bool(words) and all(word in criterion.split() for word in words)


def check_trace():
    ident, block, _ = selected_record()
    sections = named_sections(block)
    steps = ui_steps()
    if not steps:
        fail("there is no planned step that changes the visible chat UI")
    css = source_css()
    reused_colors = color_values(css) & color_values(block)
    reused_components = [name for name in component_selectors(css) if component_is_named(name, block)]

    def trace_problem(text, proof):
        clean = strip_comments(text)
        if ident not in clean or not any(path in clean for path in ("docs/shiploop/architecture.md", "KNOWLEDGE/architecture.md")):
            return "the visual criterion does not cite the selected AD ID and exact knowledge file"
        cited = [(name, body) for name, body in sections if section_is_cited(name, clean)]
        if not cited:
            return "the visual criterion does not name a section in the selected AD"
        selected_text = "\n".join(body for _, body in cited)
        selected_colors = color_values(selected_text) & reused_colors
        criterion_colors = color_values(clean)
        if not criterion_colors.intersection(selected_colors):
            return "the visual criterion does not select an existing color value from its AD section"
        if not any(component_is_named(name, clean) and component_is_named(name, selected_text)
                   for name in reused_components):
            return "the visual criterion does not select an existing chat component"
        source_sizes = {value.lower() for value in positive_matches(SIZE, css)}
        ad_sizes = {value.lower() for value in positive_matches(SIZE, selected_text)}
        criterion_sizes = {value.lower() for value in positive_matches(SIZE, clean)}
        has_current_size = bool(criterion_sizes.intersection(source_sizes).intersection(ad_sizes))
        if not has_current_size and not has_badge_composition(clean):
            return "the visual criterion omits a source-backed size or concrete unread-count placement"
        if not re.search(r"\b(?:render|rendered|browser)\b", clean, re.I):
            return "the criterion does not name a rendered observation"
        viewport_text = clean + " " + proof
        widths = [int(match.group(1)) for match in re.finditer(r"\b([1-9]\d{2,3})\s*(?:[x×]\s*\d{2,4}\b|px\b)", viewport_text, re.I)]
        narrow_max = int(contract.get("narrow_viewport_max", 480))
        wide_min = int(contract.get("wide_viewport_min", 1024))
        has_narrow = any(width <= narrow_max for width in widths) or re.search(r"\b(?:narrow|mobile|phone)\b", viewport_text, re.I)
        has_wide = any(width >= wide_min for width in widths) or re.search(r"\b(?:wide|desktop)\b", viewport_text, re.I)
        if not has_narrow or not has_wide:
            return "the criterion omits narrow and wide rendered coverage"
        if not re.search(UNREAD_INDICATOR, clean, re.I):
            return "the visual criterion does not identify the requested unread badge/marker delta"
        return None

    for step in steps:
        visuals = [text for text in criteria_for(step) if is_visual(text)]
        if not visuals:
            fail("a visible-UI step has no criterion for the unread-badge appearance")
        proof = str(step.get("proof", ""))
        problems = [trace_problem(text, proof) for text in visuals]
        if not any(problem is None for problem in problems):
            fail("no visual criterion fully selects the badge appearance for step " + str(step.get("id")) + ": " + "; ".join(f"visual criterion {index + 1}: {problem}" for index, problem in enumerate(problems)))



def package_maps_node_test():
    package = tree / "package.json"
    if not package.is_file():
        return False
    try:
        scripts = json.loads(package.read_text(encoding="utf-8")).get("scripts", {})
    except (OSError, json.JSONDecodeError):
        return False
    test_script = scripts.get("test", "") if isinstance(scripts, dict) else ""
    return isinstance(test_script, str) and bool(re.search(r"\bnode\s+--test\b", test_script))


def is_node_test_command(command):
    direct = re.search(r"(?<![A-Za-z0-9_.-])(?:[A-Za-z_][A-Za-z0-9_]*=(?:'[^']*'|\"[^\"]*\"|[^\s]+)\s+)*node\s+--test\b", command)
    npm_test = re.search(r"(?:^|[;&|]\s*)npm\s+(?:test|run\s+test)(?:\s|$)", command)
    return bool(direct or (npm_test and package_maps_node_test()))


def check_behavior():
    """Lexical behavior-presence proxy; node:test remains a separate check."""
    texts = [strip_comments(str(item.get("text", ""))) for item in result.get("criteria", []) if isinstance(item, dict)]
    combined = " ".join(texts).lower()
    if not all(token in combined for token in ("unread", "count", "conversation", "select", "clear")):
        fail("criteria omit the per-conversation unread-count and clear-on-selection behavior")
    if "message" not in combined or "local" not in combined:
        fail("criteria omit the existing local conversation/message behavior")
    commands = [str(item.get("command", "")) for item in result.get("test_commands", []) if isinstance(item, dict)]
    if not any(is_node_test_command(command) for command in commands):
        fail("the plan omits the existing node:test suite")


def within_allowed_prefix(path, prefix):
    parts = path.split("/")
    return (path.startswith(prefix) and not path.startswith("/")
            and all(part not in {"", ".", ".."} for part in parts))


def check_scope():
    """Path and phrasing proxy; it cannot establish semantic plan-scope coverage."""
    allowed = set(contract["allowed_paths"])
    prefixes = contract.get("allowed_path_prefixes", [])
    paths = set(map(str, result.get("paths", [])))
    paths |= {str(path) for step in result.get("steps", []) if isinstance(step, dict) for path in step.get("paths", [])}
    outside = sorted(path for path in paths if path not in allowed and not any(within_allowed_prefix(path, prefix) for prefix in prefixes))
    if outside:
        fail("planned paths go beyond the unread feature and design record: " + ", ".join(outside))
    missing = sorted(set(contract["required_paths"]) - paths)
    if missing:
        fail("plan omits an expected feature or test path: " + ", ".join(missing))
    prose = " ".join(str(step.get("task", "")) for step in result.get("steps", []) if isinstance(step, dict))
    prose += " " + " ".join(str(item.get("text", "")) for item in result.get("criteria", []) if isinstance(item, dict))
    active_external = positive_matches(r"\b(?:add|build|create|introduce|wire|call|depend on)\b[^.\n]{0,65}\b(?:remote service|server|api|package dependency|network service|backend)\b", prose)
    if active_external:
        fail("the plan adds an external or unrelated service")
    active_rebrand = positive_matches(r"\b(?:rebrand|redesign|re-theme|retheme)\b|\b(?:replace|rebuild)\s+(?:the\s+)?(?:whole|entire|current|existing)\s+(?:chat|product|interface|identity|palette|components?)\b", prose)
    if active_rebrand:
        fail("the plan replaces or reworks established chat identity outside the unread-badge delta")


checks = {"P1": check_record, "P2": check_trace, "C1": check_behavior, "C2": check_scope}
if len(sys.argv) != 2 or sys.argv[1] not in checks:
    fail("usage: check_plan.py P1|P2|C1|C2")
checks[sys.argv[1]]()
