"""Validate and render independent evidence for one attended Grok Bot generation.

The caller authenticates the independent reviewer launch and the discovery seal.
This module verifies that the exact review output refers to that seal and to
locatable evidence. The reviewer judges whether the evidence proves the claim.
"""
import hashlib
import json
import re
import struct
from collections import Counter
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA = "grokbot-outcome-evaluation/1"
JOURNEY_ROUTES = {
    "grok_bot_experience": {"browser"},
    "setup": {"browser", "provider"},
    "read_followup": {"browser", "provider", "records"},
    "approved_writes": {"browser", "records"},
    "history_memory": {"browser"},
    "background_recovery": {"browser", "native"},
    "responsive_keyboard": {"browser"},
}
JOURNEY_LABELS = {
    "grok_bot_experience": "Grok Bot behavior and look and feel",
    "setup": "First use and setup",
    "read_followup": "Natural read and follow-up",
    "approved_writes": "Proposed, rejected and confirmed writes",
    "history_memory": "Returning, history and memory",
    "background_recovery": "Browser-away work and recovery",
    "responsive_keyboard": "Desktop, narrow and keyboard use",
}
ROUTES = {"browser", "provider", "native", "records"}
LAYERS = {
    "app_unit": "App unit",
    "integration": "Integration",
    "salesforce_native": "Salesforce native",
    "live_provider": "Live provider",
    "rendered_ui": "Rendered UI",
    "harness_self_test": "Harness self-test",
}
LAYER_ENVIRONMENTS = {
    "app_unit": {"local", "mock"},
    "integration": {"local", "mock", "hosted"},
    "salesforce_native": {"mock", "hosted"},
    "live_provider": {"hosted"},
    "rendered_ui": {"hosted"},
    "harness_self_test": {"local", "mock"},
}
TEST_STATUSES = ("PASS", "FAIL", "NOT_RUN", "UNKNOWN")
TEST_IDENTITY = ("generation_id", "build_sha256", "source_sha256", "deployment_ids")
TARGET_FIELDS = ("org_id", "user_id", "prefix")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def shape(value, keys, description):
    require(isinstance(value, dict) and set(value) == set(keys), f"invalid {description} fields")


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def words(values, description, *, required=False):
    require(isinstance(values, list) and (values or not required)
            and all(map(nonempty, values)), f"invalid {description}")


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def canonical(path):
    require(isinstance(path, (str, Path)), "invalid evidence path")
    parsed = Path(path)
    require(parsed.is_absolute() and str(parsed) == str(path) and parsed.resolve() == parsed,
            "noncanonical evidence path")
    return parsed


def read_artifact(path):
    path = canonical(path)
    require(path.is_file(), "artifact is missing or not a regular file")
    raw = path.read_bytes()
    require(raw, "artifact is empty")
    return raw


def ref_key(ref):
    shape(ref, ("path", "sha256"), "artifact reference")
    require(isinstance(ref["path"], str) and digest(ref["sha256"]), "invalid artifact reference")
    return ref["path"], ref["sha256"]


def evidence(ref, cache):
    path, expected = ref_key(ref)
    if (path, expected) not in cache:
        raw = read_artifact(path)
        require(sha256(raw) == expected, "artifact hash does not match its reference")
        cache[path, expected] = raw
    return cache[path, expected]


def json_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def invalid_constant(_value):
    raise ValueError("non-finite JSON constant")


def load_json(raw):
    return json.loads(raw, object_pairs_hook=json_object, parse_constant=invalid_constant)


def json_pointer(raw, pointer):
    require(isinstance(pointer, str) and pointer.startswith("/")
            and re.search(r"~(?![01])", pointer) is None, "invalid JSON pointer")
    node = load_json(raw)
    for component in pointer[1:].split("/"):
        token = component.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict):
            require(token in node, "JSON pointer missing from artifact")
            node = node[token]
        elif isinstance(node, list):
            require(re.fullmatch(r"0|[1-9][0-9]*", token) and int(token) < len(node),
                    "JSON pointer index out of bounds")
            node = node[int(token)]
        else:
            raise ValueError("JSON pointer traverses a scalar")
    require(node is not None and node not in ("", [], {}), "JSON pointer has no evidence at that location")


def validate_locator(raw, locator):
    require(isinstance(locator, dict), "invalid evidence locator")
    kind = locator.get("kind")
    if kind == "json_pointer":
        shape(locator, ("kind", "pointer"), "JSON locator")
        json_pointer(raw, locator["pointer"])
    elif kind == "lines":
        shape(locator, ("kind", "start", "end"), "line locator")
        start, end = locator["start"], locator["end"]
        require(type(start) is int and type(end) is int, "line bounds must be integers")
        lines = raw.decode("utf-8").splitlines()
        require(1 <= start <= end <= len(lines) and any(line.strip() for line in lines[start - 1:end]),
                "line locator is empty or out of bounds")
    elif kind == "png_region":
        shape(locator, ("kind", "x", "y", "width", "height"), "PNG locator")
        require(len(raw) >= 33 and raw.startswith(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"),
                "PNG locator requires a PNG image header")
        image_width, image_height = struct.unpack(">II", raw[16:24])
        x, y, width, height = (locator[key] for key in ("x", "y", "width", "height"))
        require(all(type(value) is int for value in (x, y, width, height))
                and x >= 0 and y >= 0 and width > 0 and height > 0
                and x + width <= image_width and y + height <= image_height,
                "PNG region is out of bounds")
    else:
        raise ValueError("unsupported evidence locator")


def validate_link(link, cache, *, observation=False):
    keys = ("artifact", "locator", "proves")
    shape(link, (*keys, "route") if observation else keys, "evidence link")
    require(nonempty(link["proves"]), "evidence link needs what it proves")
    validate_locator(evidence(link["artifact"], cache), link["locator"])


def validate_url(url):
    require(nonempty(url) and not any(char.isspace() or ord(char) < 32 for char in url)
            and not any(char in url for char in ("\\", "?", "#")), "invalid generation app URL")
    parsed = urlsplit(url)
    require(parsed.scheme == "https" and parsed.hostname and parsed.username is None
            and parsed.password is None, "generation app URL must be HTTPS without credentials")


def validate_generation(generation):
    shape(generation, (*TEST_IDENTITY, *TARGET_FIELDS, "app_url", "retained_state"), "generation")
    require(nonempty(generation["generation_id"]) and nonempty(generation["retained_state"]),
            "generation needs identity and retained state")
    for key in ("build_sha256", "source_sha256"):
        require(generation[key] is None or digest(generation[key]), f"invalid {key}")
    for key in TARGET_FIELDS:
        require(generation[key] is None or nonempty(generation[key]), f"invalid {key}")
    ids = generation["deployment_ids"]
    words(ids, "deployment IDs")
    require(len(set(ids)) == len(ids), "duplicate deployment IDs")
    if generation["app_url"] is not None:
        validate_url(generation["app_url"])


def validate_layer(layer, environment):
    require(isinstance(layer, str) and layer in LAYER_ENVIRONMENTS
            and isinstance(environment, str) and environment in LAYER_ENVIRONMENTS[layer],
            "invalid test layer or execution environment")


def test_identity(generation, environment):
    expected = {key: generation[key] for key in TEST_IDENTITY}
    if environment != "hosted":
        expected["deployment_ids"] = []
    return expected


def validate_tested_generation(tested, generation, environment):
    shape(tested, TEST_IDENTITY, "tested generation")
    expected = test_identity(generation, environment)
    require(tested == expected and expected["build_sha256"] is not None
            and expected["source_sha256"] is not None
            and (environment != "hosted" or all(generation[key] for key in (*TARGET_FIELDS, "deployment_ids"))),
            "test evidence belongs to a different or unidentified build, source, deployment or generation")


def test_artifact_key(artifact, tested, layer, environment):
    return (ref_key(artifact), tested["generation_id"], tested["build_sha256"],
            tested["source_sha256"], tuple(tested["deployment_ids"]), layer, environment)


def sealed_test_artifacts(rows, generation):
    require(isinstance(rows, list), "invalid sealed test artifacts")
    allowed = set()
    for row in rows:
        shape(row, ("artifact", "tested_generation", "layer", "environment"), "sealed test artifact")
        tested, layer, environment = row["tested_generation"], row["layer"], row["environment"]
        validate_layer(layer, environment)
        validate_tested_generation(tested, generation, environment)
        key = test_artifact_key(row["artifact"], tested, layer, environment)
        require(key not in allowed, "duplicate sealed test artifact")
        allowed.add(key)
    return allowed


def validate_product(row, journey, generation, routes, cache):
    shape(row, ("verdict", "reason", "observations"), "product finding")
    verdict = row["verdict"]
    require(verdict in ("PASS", "FAIL", "UNKNOWN") and nonempty(row["reason"]), "invalid product verdict")
    require(isinstance(row["observations"], list), "invalid product observations")
    observed = set()
    for link in row["observations"]:
        validate_link(link, cache, observation=True)
        route = link["route"]
        require(isinstance(route, str) and routes.get(route) == link["artifact"],
                "product observation does not cite this generation's sealed route artifact")
        observed.add(route)
    if verdict in ("PASS", "FAIL"):
        require(all(generation[key] for key in (*TEST_IDENTITY, *TARGET_FIELDS)),
                "decisive outcome requires an exact deployed generation")
    if verdict == "PASS":
        require(JOURNEY_ROUTES[journey] <= observed, "product pass is missing required route evidence")
    elif verdict == "FAIL":
        require(JOURNEY_ROUTES[journey] & observed, "product fail is missing a counterexample observation")


def validate_test(row, generation, allowed, cache):
    shape(row, ("test_id", "behavior", "layer", "environment", "generated", "status", "tested_generation",
                "test_definition", "execution", "assertion", "limitations"), "test finding")
    require(nonempty(row["test_id"]) and nonempty(row["behavior"]) and type(row["generated"]) is bool,
            "test finding needs test ID, behavior and generation flag")
    layer, environment, status = row["layer"], row["environment"], row["status"]
    validate_layer(layer, environment)
    require(status in TEST_STATUSES, "invalid test status")
    words(row["limitations"], "test limitations", required=environment == "mock" or layer == "harness_self_test")
    if layer != "harness_self_test" and status == "NOT_RUN":
        require(row["generated"], "app NOT_RUN requires a generated test definition")
    definition = row["test_definition"]
    require(definition is not None or not row["generated"], "generated test needs source evidence")
    if definition is not None:
        validate_link(definition, cache)

    tested = row["tested_generation"]
    if status in ("PASS", "FAIL"):
        validate_tested_generation(tested, generation, environment)
        for field in ("execution", "assertion"):
            link = row[field]
            validate_link(link, cache)
            require(test_artifact_key(link["artifact"], tested, layer, environment) in allowed,
                    f"{field} is not sealed for the tested generation, layer and environment")
    else:
        require(tested is None and row["execution"] is None and row["assertion"] is None,
                "unproven execution must not claim a tested generation or terminal evidence")

    if row["generated"]:
        identity = test_identity(generation, environment)
        require(test_artifact_key(definition["artifact"], identity, layer, environment) in allowed,
                "generated definition is not sealed for this generation, layer and environment")


def summary_for(journeys, *, generation=None, anchor=None, review=None, routes=None, references=None):
    outcomes = Counter(row["product"]["verdict"] for row in journeys.values())
    executed = Counter()
    coverage = Counter()
    for journey in journeys.values():
        for row in journey["coverage"]["tests"]:
            layer, status, environment = row["layer"], row["status"], row["environment"]
            if layer == "harness_self_test":
                coverage["harness_findings"] += 1
            else:
                coverage[f"app_{status.lower()}_findings"] += 1
                if status in ("PASS", "FAIL"):
                    executed[layer, environment, status] += 1
    unknown, passed, failed = (outcomes[key] for key in ("UNKNOWN", "PASS", "FAIL"))
    return {
        "schema": "grokbot-outcome-evaluation-summary/1",
        "generation": generation,
        "anchor": anchor,
        "review_result": review,
        "routes": routes or {},
        "references": references or [],
        "journeys": journeys,
        "measures": {"observed": passed + failed, "passed": passed, "failed": failed, "unknown": unknown},
        "floors": {"all_outcomes_observed": unknown == 0, "all_outcomes_pass": passed == len(JOURNEY_ROUTES),
                   "qualified_acceptance": False},
        "coverage_summary": {
            **{f"app_{status.lower()}_findings": coverage[f"app_{status.lower()}_findings"]
               for status in TEST_STATUSES},
            "harness_findings": coverage["harness_findings"],
            "executions_by_layer": [
                {"layer": layer, "environment": environment, "status": status, "findings": count}
                for (layer, environment, status), count in sorted(executed.items())
            ],
        },
        "qualified": False,
        "evaluator_qualification": "UNQUALIFIED",
        "generic_improvement": "NOT_MEASURED",
    }


def assess(path, *, anchor, routes, builder_output):
    """Return deterministic findings from the actual independent review output.

    The caller supplies authenticated review and anchor identities. Invalid or
    unlocatable claims refuse the report. Record incomplete claims as UNKNOWN.
    """
    try:
        return _assess(path, anchor, routes, builder_output)
    except (OSError, RuntimeError, RecursionError, OverflowError) as exc:
        raise ValueError("unable to read evaluation evidence") from exc


def _assess(path, anchor, routes, builder_output):
    builder = canonical(builder_output)
    cache = {}
    require(not canonical(ref_key(anchor)[0]).is_relative_to(builder)
            and not canonical(path).is_relative_to(builder), "anchor and review must be outside builder output")
    sealed = load_json(evidence(anchor, cache))
    require(isinstance(sealed, dict), "invalid discovery anchor")
    generation = sealed.get("evaluation_generation")
    validate_generation(generation)
    require(isinstance(routes, dict) and routes.keys() <= ROUTES and routes == sealed.get("evaluation_routes"),
            "routes must match the sealed discovery anchor")
    allowed = sealed_test_artifacts(sealed.get("evaluation_test_artifacts", []), generation)

    raw = read_artifact(path)
    review = load_json(raw)
    shape(review, ("schema", "anchor", "journeys"), "independent review")
    require(review["schema"] == SCHEMA and review["anchor"] == anchor,
            "independent review is bound to a different discovery anchor")
    journeys = review["journeys"]
    shape(journeys, JOURNEY_ROUTES, "reviewed journeys")

    for ref in routes.values():
        require(not canonical(ref_key(ref)[0]).is_relative_to(builder),
                "independent route evidence must be outside builder output")
        evidence(ref, cache)
    for name, journey in journeys.items():
        shape(journey, ("product", "coverage"), "journey")
        validate_product(journey["product"], name, generation, routes, cache)
        coverage = journey["coverage"]
        shape(coverage, ("tests", "gaps"), "coverage finding")
        words(coverage["gaps"], "coverage gaps and limits", required=True)
        require(isinstance(coverage["tests"], list), "invalid coverage tests")
        for test in coverage["tests"]:
            validate_test(test, generation, allowed, cache)

    references = sealed.get("evaluation_reference_artifacts", [])
    require(isinstance(references, list), "invalid sealed reference artifacts")
    for item in references:
        shape(item, ("label", "artifact"), "reference material")
        require(nonempty(item["label"]), "reference material needs a label")
        evidence(item["artifact"], cache)

    return summary_for(journeys, generation=generation, anchor=anchor,
                       review={"path": str(path), "sha256": sha256(raw)}, routes=routes, references=references)


def unmeasured_summary(reason):
    """Build a prelaunch status artifact without representing it as a review."""
    require(nonempty(reason), "unmeasured status needs a reason")
    journeys = {
        name: {
            "product": {"verdict": "UNKNOWN", "reason": reason, "observations": []},
            "coverage": {"tests": [], "gaps": ["Journey coverage is unknown before generation and execution."]},
        }
        for name in JOURNEY_ROUTES
    }
    return summary_for(journeys)


def artifact_link(ref, label):
    return (f'<a href="{escape(Path(ref["path"]).as_uri())}">{escape(label)}</a>'
            f' <code class="digest">sha256 {escape(ref["sha256"])}</code>')


def locator_label(locator):
    kind = locator["kind"]
    if kind == "json_pointer":
        return f'JSON pointer {locator["pointer"]}'
    if kind == "lines":
        return f'lines {locator["start"]}–{locator["end"]}'
    return f'pixels ({locator["x"]}, {locator["y"]}), {locator["width"]} × {locator["height"]}'


def evidence_item(link, label):
    return (f'<li>{artifact_link(link["artifact"], label)}'
            f'<br><code>{escape(locator_label(link["locator"]))}</code> · {escape(link["proves"])}</li>')


def item_list(items):
    return "<ul>" + "".join(items) + "</ul>"


def render_test(row):
    badges = [LAYERS[row["layer"]], row["environment"], row["status"]]
    if row["generated"]:
        badges.append("Generated")
    details = [f'<li>{escape(limit)}</li>' for limit in row["limitations"]]
    for key, label in (("test_definition", "Test definition"), ("execution", "Execution result"),
                       ("assertion", "Assertion evidence")):
        if row[key] is not None:
            details.append(evidence_item(row[key], label))
    tested = row["tested_generation"]
    if tested is None:
        identity = ""
    elif tested["deployment_ids"]:
        deployments = escape(", ".join(tested["deployment_ids"]))
        identity = f'<p class="meta">Tested deployment <code>{deployments}</code></p>'
    else:
        identity = '<p class="meta">Tested against this generation’s local source.</p>'
    return (f'<li><strong>{escape(row["test_id"])}</strong> <span class="meta">{escape(" · ".join(badges))}</span>'
            f'<p>{escape(row["behavior"])}</p>{identity}' + (item_list(details) if details else "") + "</li>")


def render_journey(name, row):
    product, coverage = row["product"], row["coverage"]
    verdict = product["verdict"]
    observations = item_list(evidence_item(link, f'{link["route"].capitalize()} observation')
                             for link in product["observations"]) if product["observations"] else ""
    tests = item_list(map(render_test, coverage["tests"])) if coverage["tests"] else "<p>No test findings supplied.</p>"
    gaps = item_list(f"<li>{escape(gap)}</li>" for gap in coverage["gaps"])
    return (f'<section class="journey" aria-labelledby="{name}"><h2 id="{name}">{JOURNEY_LABELS[name]}</h2>'
            f'<div class="findings"><div><h3>Product <span class="verdict {verdict.lower()}">{verdict}</span></h3>'
            f'<p>{escape(product["reason"])}</p>{observations}</div><div><h3>Test coverage</h3>'
            f'{tests}<h4>Gaps and limits</h4>{gaps}</div></div></section>')


def render_generation(generation):
    if generation is None:
        return "<p>Generation, source and deployment evidence unavailable.</p>"
    rows = (
        ("Generation", generation["generation_id"]),
        ("Org", generation["org_id"]),
        ("User", generation["user_id"]),
        ("Metadata prefix", generation["prefix"]),
        ("ShipLoop build SHA256", generation["build_sha256"]),
        ("Deployed source SHA256", generation["source_sha256"]),
        ("Deployment IDs", ", ".join(generation["deployment_ids"])),
    )
    return "<dl>" + "".join(f'<dt>{label}</dt><dd><code>{escape(value or "Unavailable")}</code></dd>'
                           for label, value in rows) + "</dl>"


def render_html(summary):
    """Render a validated summary without embedding evidence bodies or external assets."""
    measured = summary["measures"]
    generation = summary["generation"]
    title = "Grok Bot E2E effectiveness unmeasured" if measured["observed"] == 0 else "Grok Bot E2E evaluation"
    if generation and generation["app_url"]:
        app = f'<a href="{escape(generation["app_url"])}">Open the Salesforce generation</a>'
    else:
        app = "Salesforce generation link unavailable"
    state = generation["retained_state"] if generation else "NOT_STARTED"
    evidence_refs = [artifact_link(summary[key], label) for key, label in
                     (("anchor", "Sealed discovery"), ("review_result", "Independent review output"))
                     if summary[key] is not None]
    evidence_refs.extend(artifact_link(ref, f"{route.capitalize()} evidence")
                         for route, ref in sorted(summary["routes"].items()))
    evidence_refs.extend(artifact_link(item["artifact"], item["label"]) for item in summary["references"])
    reference_list = item_list(f"<li>{link}</li>" for link in evidence_refs) if evidence_refs else (
        "<p>No sealed discovery, observation or review evidence available.</p>"
    )
    journeys = "".join(render_journey(name, summary["journeys"][name]) for name in JOURNEY_ROUTES)
    coverage_counts = summary["coverage_summary"]
    executions = coverage_counts["executions_by_layer"]
    execution_list = item_list(
        f'<li>{LAYERS[row["layer"]]} · {row["environment"]} · {row["status"]} · {row["findings"]} findings</li>'
        for row in executions
    ) if executions else "<p>No generation-bound app test executions were verified. Coverage remains unknown.</p>"
    app_unproven = (
        f'<p>App test findings with execution unproven: {coverage_counts["app_not_run_findings"]} '
        f'NOT_RUN and {coverage_counts["app_unknown_findings"]} UNKNOWN.</p>'
        if coverage_counts["app_not_run_findings"] or coverage_counts["app_unknown_findings"] else ""
    )
    harness_count = coverage_counts["harness_findings"]
    harness = f"<p>Harness self-test findings, reported separately: {harness_count}.</p>" if harness_count else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; color: #17272d; background: #f4f6f2; font: 1rem/1.55 system-ui, sans-serif; }}
main {{ max-width: 75rem; padding: clamp(1rem, 4vw, 3rem); margin: auto; overflow-wrap: anywhere; }}
h1 {{ font: 700 clamp(2rem, 5vw, 3.5rem)/1.1 Georgia, serif; max-width: 22ch; margin: .25em 0 .5em; }}
h2, h3, h4 {{ line-height: 1.25; margin-bottom: .5em; }}
p {{ margin-top: .5em; }}
a {{ color: #075d63; text-underline-offset: .2em; }}
header {{ border-bottom: 3px solid #306060; padding-bottom: 1.25rem; }}
.status, .meta {{ color: #385356; font-size: .92rem; }}
.journey {{ border-top: 1px solid #abb9b6; margin-top: 1.55rem; }}
.findings {{ display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 3fr); gap: 1rem; }}
.findings > div {{ background: #fff; padding: 0 1rem .65rem; border-radius: .4rem; }}
.verdict {{ border-radius: .25rem; padding: .1em .35em; font: 700 .8rem system-ui, sans-serif; background: #e7e9e9; }}
.verdict.pass {{ background: #dceee1; color: #194d28; }}
.verdict.fail {{ background: #f7e1dd; color: #83291b; }}
code {{ font-family: ui-monospace, monospace; font-size: .88em; }}
.digest {{ display: block; color: #405257; }}
li + li {{ margin-top: .45em; }}
dt {{ font-weight: 600; }}
dd {{ margin: 0 0 .35em; }}
@media (max-width: 44rem) {{ .findings {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<main>
<header>
<p>{app} · <span class="status">Retained state at sealing: {escape(state)}</span></p>
<h1>{title}</h1>
<p>{measured["passed"]} PASS · {measured["failed"]} FAIL · {measured["unknown"]} UNKNOWN customer journeys</p>
<p>Evaluator qualification <strong>UNQUALIFIED</strong> · Generic ShipLoop improvement <strong>NOT_MEASURED</strong></p>
</header>
<section aria-labelledby="coverage-summary">
<h2 id="coverage-summary">Executed test findings</h2>
{execution_list}{app_unproven}{harness}
</section>
{journeys}
<section aria-labelledby="generation"><h2 id="generation">Generation and deployment</h2>{render_generation(generation)}</section>
<section aria-labelledby="evidence"><h2 id="evidence">Reference evidence</h2>{reference_list}</section>
</main>
</body>
</html>
"""
