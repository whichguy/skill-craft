"""Traceability and reproducibility proxy; semantic coherence stays under manual review."""
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
criteria = {str(c.get("id")): str(c.get("text", "")) for c in result.get("criteria", []) if isinstance(c, dict)}
steps = [s for s in result.get("steps", []) if isinstance(s, dict)]

def fail(message):
    raise SystemExit(message)

def strip_comments(text):
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", text)

COLOR_PATTERN = r"(?:#[0-9a-f]{3,8}\b|\b(?:rgb|rgba|hsl|hsla|oklch|oklab|lab|lch|color)\([^)]*\)|\b(?:black|white|red|green|blue|navy|teal|olive|coral|ivory|beige|tan|maroon|purple|violet|indigo|orange|gold|pink|brown|silver|gray|grey|crimson|salmon|tomato|rebeccapurple|slategray|slategrey|khaki|linen|mintcream|seagreen|steelblue|slateblue|midnightblue|darkslategray|darkslategrey|lightgray|lightgrey|whitesmoke|transparent)\b)"
DIMENSION_PATTERN = r"\b\d+(?:\.\d+)?(?:rem|px|em|vw|vh|%)\b"
VARIABLE_PATTERN = r"--[a-z][a-z0-9_-]*"

def positive_matches(pattern, text):
    text = strip_comments(text)
    matches = []
    for match in re.finditer(pattern, text, re.I):
        before = text[max(0, match.start() - 48):match.start()].lower()
        if re.search(r"\b(?:not|avoid|without|never|do not|don't|rejected|reject)\b[^.;:]{0,44}$", before):
            continue
        matches.append(match.group(0))
    return matches

def ui_steps():
    ui_paths = contract.get("ui_paths", [])
    return [s for s in steps if any(str(p) in ui_paths for p in s.get("paths", []))]

def texts_for(step):
    return [criteria[str(cid)] for cid in step.get("criteria", []) if str(cid) in criteria]

def is_visual(text):
    return bool(re.search(r"\b(?:visual|appearance|render(?:ed)?|browser|theme|color|colour|typography|font|layout|composition|surface|responsive|focus|style)\b", strip_comments(text), re.I))

def ad_start(line, ad_id):
    prefix = r"^\s*(?:(?:#{2,6}\s+)|(?:[-*]\s+))?(?:\*\*)?"
    return bool(re.match(prefix + re.escape(ad_id) + r"\b", line))

def ad_block(doc, ad_id):
    lines = strip_comments(doc).splitlines()
    start = next((i for i, line in enumerate(lines) if ad_start(line, ad_id)), None)
    if start is None:
        return ""
    end = len(lines)
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if re.match(r"^\s*(?:(?:#{2,6}\s+)|(?:[-*]\s+))?(?:\*\*)?AD-\d+\b", line):
            other = re.search(r"\bAD-\d+\b", line)
            if other and other.group(0) != ad_id:
                end = i
                break
        if re.match(r"^\s*#{1,2}\s+(?!AD-\d+\b)", line):
            end = i
            break
    return "\n".join(lines[start:end])

def named_sections(block):
    sections = []
    current_name, current_lines = None, []

    def save():
        if current_name:
            sections.append((current_name.strip(), "\n".join(current_lines)))

    for line in block.splitlines()[1:]:
        heading = re.match(r"^\s*#{3,6}\s+(.+?)\s*#*\s*$", line)
        bold_label = re.match(r"^\s*(?:[-*]\s*)?\*\*([^*]+)\*\*\s*:?\s*(.*?)\s*$", line)
        plain_label = re.match(r"^\s*(?:[-*]\s*)?([A-Za-z][A-Za-z0-9 /&()_-]{2,45})\s*:\s*(.*?)\s*$", line)
        match = heading or bold_label or plain_label
        if match and not re.search(r"\bAD-\d+\b", match.group(1)):
            save()
            current_name = match.group(1)
            inline_body = (bold_label or plain_label).group(2).strip() if (bold_label or plain_label) else ""
            current_lines = [inline_body] if inline_body else []
        elif current_name:
            current_lines.append(line)
    save()
    return sections

def visible_texts():
    return [text for step in ui_steps() for text in texts_for(step) if is_visual(text)]

def selected_record():
    cited = []
    for text in visible_texts():
        cited.extend(re.findall(r"\bAD-\d+\b", strip_comments(text)))
    fixed = contract.get("fixed_ad")
    if fixed:
        cited = [fixed]
    cited = list(dict.fromkeys(cited))
    if not cited:
        fail("no selected AD is cited by a visual criterion")
    doc_path = tree / "docs/shiploop/architecture.md"
    if not doc_path.is_file():
        fail("docs/shiploop/architecture.md is missing")
    doc = doc_path.read_text(encoding="utf-8")
    for ad_id in cited:
        block = ad_block(doc, ad_id)
        if block:
            return ad_id, block, named_sections(block)
    fail("the selected AD ID has no matching architecture decision")

def has_knowledge_locator(text):
    return bool(re.search(r"(?:docs/shiploop/architecture\.md|knowledge/architecture\.md)", text, re.I))

def check_record():
    ad_id, block, sections = selected_record()
    mode = contract.get("mode", "new")
    if not sections:
        fail(f"{ad_id} has no named choice section")
    colors = positive_matches(COLOR_PATTERN, block)
    dimensions = positive_matches(DIMENSION_PATTERN, block)
    lower = strip_comments(block).lower()
    if len({c.lower() for c in colors}) < 2:
        fail(f"{ad_id} has fewer than two concrete color anchors")
    if not dimensions:
        fail(f"{ad_id} has no concrete size or spacing anchor")
    if not re.search(r"\bfont(?:[-\s]+family)?\s*[:=]|\bsystem-ui\b|\bsans-serif\b", lower):
        fail(f"{ad_id} has no concrete type choice")
    if mode == "new":
        light_default = re.search(r"\blight[- ]first\b|\bdefaults?\s+to\s+light\b|\blight\b.{0,32}\bdefault\b|\bdefault\b.{0,20}\blight\b|\bdefault\s*[:=]\s*light\b", lower, re.S)
        dark_default = re.search(r"\bdark\b.{0,18}\bdefault\b|\bdefault\b.{0,12}\bis\s+dark\b|\bdefault\s*[:=]\s*dark\b", lower, re.S)
        if not light_default or dark_default:
            fail(f"{ad_id} does not select a light default")
        if "dark" not in lower:
            fail(f"{ad_id} does not record a dark option")
    if mode == "explicit":
        if not re.search(r"\bretro\b|\barcade\b|\bpixel\b", lower):
            fail(f"{ad_id} does not record the explicitly requested style")
        if not re.search(r"\bbanner\b|\bstatus strip\b|\bselection strip\b", lower):
            fail(f"{ad_id} does not keep the style decision on the requested component")
    if contract.get("fixed_ad") and contract["fixed_ad"] != ad_id:
        fail("the stable decision ID changed")
    if ad_id not in [str(value) for value in result.get("follows", [])]:
        fail("the selected AD is missing from follows")
    # The visual criterion itself carries the AD/file/section trace; a duplicate summary locator is optional.
    if mode == "identity":
        css_path = tree / contract.get("identity_css", "styles.css")
        if not css_path.is_file():
            fail("the established product stylesheet is missing")
        css = strip_comments(css_path.read_text(encoding="utf-8"))
        existing = {v.lower() for v in positive_matches(COLOR_PATTERN, css)}
        chosen = {v.lower() for v in colors}
        if len(existing & chosen) < 2:
            fail("the AD does not reuse colors already present in the product")
    return ad_id, block, sections

def normalize(text):
    return re.sub(r"[^a-z0-9]+", " ", strip_comments(text).lower()).strip()

def section_is_cited(name, text):
    label, citation = normalize(name), normalize(text)
    if label and label in citation:
        return True
    words = [w for w in label.split() if w not in {"the", "and", "of", "for", "a", "an"}]
    return bool(words) and all(w in citation.split() for w in words)

def declared_color_roles(text):
    """Return bare roles only for color tokens declared in this selected AD section."""
    roles = {}
    declaration = re.compile(r"(" + VARIABLE_PATTERN + r")\s*:?\s*(" + COLOR_PATTERN + r")", re.I)
    for match in declaration.finditer(strip_comments(text)):
        token = match.group(1).lower()
        roles[token[2:]] = token
    return roles

def cited_color_roles(text, roles):
    clean = strip_comments(text)
    return [role for role in roles
            if re.search(r"(?<![\w-])" + re.escape(role) + r"(?![\w-])", clean, re.I)]

def trace_criterion_error(criterion_id, text, proof, ad_id, sections, mode):
    clean = strip_comments(text)
    if ad_id not in clean or not has_knowledge_locator(clean):
        return "visual criterion does not cite the selected AD ID and exact knowledge file"
    cited_sections = [(name, body) for name, body in sections if section_is_cited(name, clean)]
    if not cited_sections:
        return "visual criterion does not name a section that exists in the selected AD"
    selected_text = "\n".join(body for _, body in cited_sections)
    colors = positive_matches(COLOR_PATTERN, clean)
    dimensions = positive_matches(DIMENSION_PATTERN, clean)
    variables = positive_matches(VARIABLE_PATTERN, clean)
    color_roles = declared_color_roles(selected_text)
    resolved_roles = cited_color_roles(clean, color_roles)
    if not colors and not variables and not resolved_roles:
        return "visual criterion omits a concrete color value or token role"
    if not dimensions:
        return "visual criterion omits a concrete size or composition anchor"
    ad_colors = {m.lower() for m in positive_matches(COLOR_PATTERN, selected_text)}
    ad_variables = {m.lower() for m in positive_matches(VARIABLE_PATTERN, selected_text)}
    ad_dimensions = {m.lower() for m in positive_matches(DIMENSION_PATTERN, selected_text)}
    if (not any(c.lower() in ad_colors for c in colors)
            and not any(v.lower() in ad_variables for v in variables)
            and not resolved_roles):
        return "criterion color anchor is not in the cited AD section"
    if not any(d.lower() in ad_dimensions for d in dimensions):
        return "criterion size anchor is not in the cited AD section"
    if not re.search(r"\b(?:render|rendered|browser)\b", clean, re.I):
        return "criterion does not specify a rendered observation"
    for theme in contract.get("required_themes", ["light", "dark"]):
        if theme == "current":
            if not re.search(r"\b(?:current|existing|selected) theme\b", clean, re.I):
                return "criterion omits the existing theme it must preserve"
        elif not re.search(r"\b" + re.escape(theme) + r"\b", clean, re.I):
            return f"criterion omits the {theme} rendered state"
    viewport_text = clean + " " + proof
    widths = [int(match.group(1)) for match in re.finditer(r"\b([1-9]\d{2,3})\s*(?:[x×]\s*\d{2,4}\b|px\b)", viewport_text, re.I)]
    narrow_max = int(contract.get("narrow_viewport_max", 480))
    wide_min = int(contract.get("wide_viewport_min", 1024))
    has_narrow = any(width <= narrow_max for width in widths) or re.search(r"\b(?:narrow|mobile|phone)\b", viewport_text, re.I)
    has_wide = any(width >= wide_min for width in widths) or re.search(r"\b(?:wide|desktop)\b", viewport_text, re.I)
    if not has_narrow or not has_wide:
        return "criterion omits narrow and wide viewport coverage"
    command_rows = [c for c in result.get("test_commands", []) if isinstance(c, dict)
                    and str(c.get("command", "")).strip() == proof
                    and criterion_id in [str(x) for x in c.get("criteria", [])]]
    if not command_rows:
        return "the rendered criterion is not linked to its step proof command"
    # Whether a rendered helper is the appropriate local route is reviewed manually; focused scratch helpers are valid.
    if mode == "explicit" and (not re.search(r"\b(?:retro|arcade|pixel)\b", clean, re.I) or not re.search(r"\bbanner\b|\bstatus strip\b|\bselection strip\b", clean, re.I)):
        return "criterion does not bind the explicit style to its requested component"
    return None

def check_trace():
    ad_id, block, sections = selected_record()
    mode = contract.get("mode", "new")
    visible = ui_steps()
    if not visible:
        fail("there is no planned step that changes visible UI")
    visual_seen = False
    for step in visible:
        visual_criteria = [(str(cid), criteria[str(cid)]) for cid in step.get("criteria", [])
                           if str(cid) in criteria and is_visual(criteria[str(cid)])]
        if not visual_criteria:
            fail("a visible-UI step has no criterion for its visual choices")
        proof = str(step.get("proof", "")).strip()
        if not re.match(r"^(?:(?:[A-Za-z_][A-Za-z0-9_]*=(?:'[^']*'|\"[^\"]*\"|[^\s]+))\s+)*(?:node|npm|python3)\s+", proof):
            fail("the UI step proof is not a local command")
        errors = []
        for criterion_id, text in visual_criteria:
            error = trace_criterion_error(criterion_id, text, proof, ad_id, sections, mode)
            if error is None:
                visual_seen = True
                break
            errors.append(criterion_id + ": " + error)
        else:
            fail(f"visible-UI step {step.get('id', '<unknown>')} has no visual criterion with complete AD trace and rendered proof: {'; '.join(errors)}")
    if not visual_seen:
        fail("no visual criterion was selected by a visible-UI step")

def behavior_present(term, text):
    if term.lower() == "selection":
        return bool(re.search(r"\b(?:select(?:ion|ing)?|choose|choosing|pick(?:ing)?|click(?:ing)?|activate|activating)\b", text, re.I))
    if term.lower() == "coordinate":
        return "coordinate" in text or bool(re.search(r"\bselected:\s*[a-h][1-8]\b", text, re.I))
    return term.lower() in text

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
    criteria_by_id = {str(c.get("id")): str(c.get("text", "")) for c in result.get("criteria", []) if isinstance(c, dict)}
    all_text = " ".join(criteria_by_id.values()).lower()
    if not all(behavior_present(term, all_text) for term in contract.get("fixture_behavior", [])):
        fail("criteria omit existing local behavior that the task must preserve")
    feature_terms = contract.get("feature_behavior", [])
    if feature_terms and not all(behavior_present(term, all_text) for term in feature_terms):
        fail("the criteria omit the requested feature behavior")
    commands = [str(t.get("command", "")) for t in result.get("test_commands", []) if isinstance(t, dict)]
    if not any(is_node_test_command(command) for command in commands):
        fail("plan omits the existing node:test suite")

checks = {"P1": check_record, "P2": check_trace, "C1": check_behavior}
if len(sys.argv) != 2 or sys.argv[1] not in checks:
    fail("usage: check_plan.py P1|P2|C1")
checks[sys.argv[1]]()
