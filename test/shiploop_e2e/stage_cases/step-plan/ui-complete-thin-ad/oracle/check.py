"""Specificity/traceability checks for completing this existing AD, not a quality judge.

The accepted ID and values are fixture inputs. New section names, additional
composition choices and grouping of functional/visual criteria remain flexible.
Semantic coherence and whether prose actually expresses intent require review.
"""
import json
import os
from pathlib import Path
import re
import sys

if 'STAGE_RESULT' not in os.environ:
    raise SystemExit('No accepted stage result is available.')

result = json.loads(Path(os.environ['STAGE_RESULT']).read_text())
path = Path('docs/shiploop/architecture.md')
doc = path.read_text() if path.is_file() else ''
doc = re.sub(r'<!--.*?-->|/\*.*?\*/', '', doc, flags=re.S)


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def block_for(identifier):
    heading = re.search(r'(?m)^(#{1,6})\s+[^\n]*\b' + re.escape(identifier) + r'\b[^\n]*$', doc)
    if not heading:
        return ''
    tail = doc[heading.end():]
    boundary = re.search(r'(?m)^#{1,' + str(len(heading[1])) + r'}\s+', tail)
    return doc[heading.start():heading.end() + boundary.start()] if boundary else doc[heading.start():]


block = block_for('AD-2')
sections = re.findall(r'(?m)^#{2,6}\s+(.+)$', block)[1:]


def normalize(text):
    return ' '.join(re.findall(r'[a-z0-9]+', text.lower()))


def positive(pattern, text):
    for match in re.finditer(pattern, text, flags=re.I):
        before = text[max(0, match.start() - 42):match.start()]
        if not re.search(r"\b(?:not|never|reject|rejected|avoid|without)\b[^.;:\n]{0,38}$", before, flags=re.I):
            return True
    return False


def dimensions(text):
    return {m.lower().lstrip('0') for m in re.findall(r'(?<![\w.])(?:\d*\.)?\d+(?:rem|px|em|vw|vh|%)\b', text, flags=re.I)}


def concrete():
    require(block and sections, 'AD-2 is missing or has no named choice sections')
    require(positive(r'\b(?:below|after)\b', block), 'No positive summary placement choice')
    require(bool(dimensions(block)), 'No concrete size or spacing choices')
    require(positive(r'system-ui|sans-serif|inherit[^.\n]*styles\.css', block), 'Existing type choice is not reproducible')
    require(positive(r'\blight\b', block) and positive(r'\bdark\b|theme-dark', block), 'Existing theme choices are missing')


def trace():
    require(block and sections, 'No selected AD-2 record to resolve')
    criteria = {str(row.get('id')): str(row.get('text', '')) for row in result.get('criteria', [])}
    visible = [step for step in result.get('steps', []) if any(
        p == 'index.html' or p.endswith('.css') or p.startswith('src/')
        for p in step.get('paths', []))]
    require(visible, 'No visible implementation step to assess')
    for step in visible:
        selected = []
        for identifier in step.get('criteria', []):
            text = re.sub(r'<!--.*?-->', '', criteria.get(str(identifier), ''), flags=re.S)
            located = ('docs/shiploop/architecture.md' in text or 'KNOWLEDGE/architecture.md' in text)
            section = any(normalize(name) in normalize(text) for name in sections)
            if re.search(r'\bAD-2\b', text) and located and section:
                if positive(r'\b(?:below|after)\b', text) and dimensions(text) & dimensions(block):
                    selected.append(text)
        require(selected, f"{step.get('id')}: no visual criterion selects the actual AD section and composition anchors")
    require('AD-2' in result.get('follows', []), 'Selected AD-2 omitted from follows')


def retained():
    require(block, 'Existing AD-2 ID was replaced or removed')
    for role, color in [('--page', '#f4f1e9'), ('--surface', '#fffdf8'), ('--ink', '#19302e'), ('--accent', '#bb633e')]:
        rgb = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
        rgb_pattern = r'rgba?\(\s*' + r'\s*[, ]\s*'.join(map(str, rgb)) + r'(?:\s*\)|\s*[,/])'
        # Retention can be phrased as "do not change VALUE". Presence is a
        # traceability proxy; semantic acceptance is assessed separately.
        literal = re.search(re.escape(color) + r'\b|' + rgb_pattern, block, flags=re.I)
        linked = role in block and 'styles.css' in block
        require(literal or linked, f'Accepted {role} value is lost')
        for clause in re.split(r'[.;]\s+|\n', block):
            if role not in clause or not re.search(re.escape(color) + r'\b|' + rgb_pattern, clause, flags=re.I):
                continue
            # Reject a direct contradictory instruction even if the old token
            # still appears. "Do not change VALUE" remains a valid control.
            rejects = positive(r"\b(?:do not|don't|never)\s+(?:retain|keep|preserve|reuse)\b", clause)
            replaces = positive(r'\b(?:replace[sd]?|chang(?:e[sd]?|ing)|discard|retire|override)\b', clause)
            require(not (rejects or replaces), f'Accepted {role} is explicitly rejected or replaced')
    for value in [r'(?<!\d)(?:0?\.75)rem\b', r'\b44rem\b', r'\b32rem\b']:
        require(re.search(value, block, flags=re.I), 'An explicitly accepted size value is lost')


{'P1': concrete, 'P2': trace, 'C1': retained}[sys.argv[1]]()
