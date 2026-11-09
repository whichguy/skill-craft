"""Apply the V7-only probe delta to a new, exact V6 materialization."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .probe_fixture_controls import add

HERE = Path(__file__).resolve().parent
V6_OVERLAY = "e5f9b142b34071a56e2cb1fc9fea5586b19e42bfe8cfd622530771e5b0ed04ef"
SUPPORT = (
    "diagnostic-files.cjs", "export-coverage.cjs", "export-mutator.cjs",
    "export-test-reporter.cjs", "logger-failure.cjs", "logger-observation.cjs", "task-atomicity.cjs",
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"V6 probe anchor differs: {old.splitlines()[0][:80]}")
    return text.replace(old, new)


def section(text, start, end, new):
    lo = text.index(start)
    hi = text.index(end, lo)
    return text[:lo] + new + text[hi:]


def atomicity(text):
    text = replace(text, "const root=path.resolve", """const missingSelections=require('../../v7-probes/task-atomicity.cjs');
const root=path.resolve""")
    text = replace(text, "const app=load('src/tasks.cjs');", """const missing=missingSelections(root,path.dirname(resultFile));
const app=load('src/tasks.cjs');""")
    return section(text, "  const beforeMissing=", "\n }\n const single=", """  for(const {name,rejected,snapshotUnchanged,recordsUnchanged,completed} of missing)
   check('security',name,completed&&rejected&&snapshotUnchanged&&recordsUnchanged,
         JSON.stringify({completed,rejected,snapshotUnchanged,recordsUnchanged}));""")


def integration(text):
    text = replace(text, "../../outer-oracle/export-coverage.cjs", "../../v7-probes/export-coverage.cjs")
    return replace(text, """coverage.changedMarkerFiles.length>0,
       JSON.stringify({exit:coverage.mutantExit,markerFiles:coverage.markerFiles,changedMarkerFiles:coverage.changedMarkerFiles}));""",
                   """coverage.changedAssertionFiles.length>0,
       JSON.stringify({attribution:'changed file',...coverage}));""")


def normal_logger(text):
    text = replace(text, "const {isDeepStrictEqual:same,inspect}=require('node:util');",
                   """const {isDeepStrictEqual:same,types}=require('node:util');
const {inspect,markersFor,observeLogger}=require('../../v7-probes/logger-observation.cjs');
const {safeFiles}=require('../../v7-probes/diagnostic-files.cjs');""")
    text = replace(text, "path:rel,message:String(e&&e.message||e)", "path:rel,message:'diagnostic module could not load'")
    text = replace(text, "operation:n,message:String(e&&e.message||e)", "operation:n,message:'diagnostic operation threw'")
    text = replace(text, "const childPath=require('node:path'),cp=require('node:child_process');",
                   "const childPath=require('node:path');")
    text = section(text, "const syntheticMarkers=", "process.env.RUNTIME_CREDENTIAL", """const syntheticMarkers=markersFor([token,payload]);
const observer=observeLogger(syntheticMarkers);
function field(value,name){
 if(!value || typeof value!=='object' || types.isProxy(value))return undefined;
 return Object.getOwnPropertyDescriptor(value,name)?.value;
}
""")
    text = section(text, " const logger={", " const file=childPath", """ const logger={info:observer.capture,warn:observer.capture,error:observer.capture};
 let thrown;
 const report=call('functionality','create diagnostic report',()=>{
  try{return app.createDiagnostic(runtime,{outputDir:outDir,logger});}
  catch(error){thrown=error;throw error;}
 });
 const observation=observer.result();
 check('functionality','safe report retains useful status/count',field(report,'state')==='ready'&&field(report,'processed')===4,'required report fields');
 check('functionality','normal success calls the supplied logger',observation.calls>0,'logger event');
""")
    text = replace(text, "JSON.stringify(fileValue));", "'required file fields');")
    text = section(text, " const outputFiles=[];", " check('security','credential absent from returned values'", """ const returned=inspect([report,thrown],syntheticMarkers);
 const returnedSafe=returned.safe;
 const logsSafe=observation.safe; // Parent also observes actual fd 1/2 bytes.
 const outputFilesSafe=safeFiles(outDir,syntheticMarkers);
 const treeSafe=safeFiles(root,syntheticMarkers);
 security_surfaces={returned_safe:returnedSafe,logs_safe:logsSafe,output_files_safe:outputFilesSafe,
   current_tree_safe:treeSafe,logger_observation:observation,
   history_safe:null,history_coverage:{status:'unmeasured_no_subject_era_canary'}};
""")
    text = replace(text, " check('security','credential absent from retained Git blobs when history exists',historySafe,historyCoverage.status);\n", "")
    return replace(text, "message:String(e&&e.stack||e)", "message:'diagnostic observation could not complete'")


def logger_wrapper(text):
    text = replace(text, "../../../logger_failure.cjs", "../../v7-probes/logger-failure.cjs")
    return replace(text, """   const failure=loggerFailure(path.resolve(source),scratch);
   result.logger_failure_surfaces=failure;""",
                   """   const {checks:failure,observation}=loggerFailure(path.resolve(source),scratch);
   result.logger_failure_surfaces=failure;
   result.logger_failure_observation=observation;""")


def apply(root):
    """Return a deterministic manifest; call once on the newly assembled tree."""
    root = Path(root)
    receipt = json.loads((root / "materialization.json").read_text())
    if receipt.get("corpus_version") != 6 or receipt.get("overlay_sha256") != V6_OVERLAY:
        raise ValueError("probe overlay requires a fresh V6 materialization")
    support = root / "corpus" / "v7-probes"
    if support.exists() or support.is_symlink():
        raise ValueError("probe overlay is already present")

    functions = {
        "corpus/later-added-work/oracle/probe.cjs": atomicity,
        "corpus/integration-only/oracle/probe.cjs": integration,
        "corpus/integrated-secure/oracle/probe.cjs": integration,
        "corpus/secret-exposure/oracle/probe.cjs": normal_logger,
        "corpus/secret-exposure/oracle/oracle.cjs": logger_wrapper,
    }
    staged = {}
    rows = []

    def record(path, before):
        rows.append({"path": path.relative_to(root).as_posix(), "before_sha256": before,
                     "sha256": digest(path.read_bytes())})

    for name, transform in functions.items():
        path = root / name
        data = path.read_bytes()
        staged[path] = (digest(data), transform(data.decode()).encode())
    calibrations = {
        path: (digest(path.read_bytes()), json.loads(path.read_text())["references"])
        for path in sorted((root / "corpus").glob("*/oracle/calibration.json"))
    }
    v6_count = sum(len(values) for _, values in calibrations.values())
    if v6_count != 94:
        raise ValueError("V6 calibration inventory differs")
    support.mkdir(mode=0o700)
    support.chmod(0o700)
    for name in SUPPORT:
        dest = support / name
        dest.write_bytes((HERE / "probes" / name).read_bytes())
        dest.chmod(0o600)
        record(dest, None)
    for path, (before, data) in staged.items():
        path.write_bytes(data)
        record(path, before)
    added = add(root)
    for path, (before, old) in calibrations.items():
        new = json.loads(path.read_text())["references"]
        labels = added.get(path.parent.parent.name, {})
        if new != {**old, **labels}:
            raise ValueError("V6 expectations changed during probe overlay")
        if labels:
            record(path, before)
            for label in labels:
                for item in sorted((path.parent.parent / "references" / label).rglob("*")):
                    if item.is_file():
                        record(item, None)
    return {"schema": "shiploop-security-probe-overlay/v1",
            "files": sorted(rows, key=lambda row: row["path"]),
            "v6_reference_count": v6_count,
            "added_reference_count": sum(map(len, added.values())),
            "added_references": {case: sorted(labels) for case, labels in sorted(added.items())}}
