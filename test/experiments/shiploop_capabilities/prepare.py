#!/usr/bin/env python3
"""Prepare frozen, opt-in capability trials; never run an agent or deploy."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PRIOR = Path('/tmp/shiploop-discovery-v4.j2fv6ma3')
sys.dont_write_bytecode = True
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from runtime_validation import (  # noqa: E402 - sibling is part of the frozen runtime
    RUNTIME_FILES,
    RUNTIME_MANIFEST,
    RUNTIME_VERSION,
    RuntimeSnapshotError,
    validate_runtime_snapshot,
)
TASKS = {
    'env': ('ENV', 'discovery', 'Investigate this existing synthetic client/server environment for a request to deploy a Checkers app. Establish what can actually be accessed, what runs where, which existing libraries/procedures fit, and how the client/server/state interaction works. Screen all eight discovery areas, test one relevant boundary, and preserve unresolved facts. Do not deploy.'),
    'inner': ('INNER', 'implement', 'Repair the reported move reliability problem in app.py: retrying a move can advance the game twice, and a request from an old screen can be accepted. Follow SPEC.md, preserve suitable existing architecture/libraries, add meaningful regression checks, run them, and report actual evidence. Do not edit SPEC.md or prepared initial-state files.'),
    'outer': ('OUTER', 'system-test', 'Assess whether the actual served application is ready to release the candidate described in README.md. Local tests passing are one input; inspect relevant real runtime interactions and state. Record supported readiness findings and blockers. Do not deploy or change access, revision/configuration declarations, or server settings.'),
    'outer_holdout': ('OUTER_HOLDOUT', 'system-test', 'Assess integration readiness of this served Checkers candidate, including whether the intended actor can complete the required move across the actual service boundary. Record evidence and the correct readiness decision. Do not grant access, change service settings, or deploy.'),
    'test': ('TEST', 'test-author', 'Expand executable tests for the Checkers HTTP/Store contract in SPEC.md. Cover consequential failure and boundary behavior as well as ordinary success. Preserve app.py, SPEC.md, initial state, and service configuration. Put tests in test_*.py and ensure they run with Python unittest discovery against app.py in the workspace. Record actual checks and limits; do not implement or repair the application.'),
}


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')


def runtime_snapshot(study: Path) -> Path:
    """Return this follow-up study's immutable runtime snapshot."""
    runtime = study / 'frozen' / 'runtime-v3'
    try:
        validate_runtime_snapshot(runtime)
    except RuntimeSnapshotError as exc:
        raise RuntimeError(
            'missing or invalid frozen runtime-v3; create a fresh study with --freeze-runtime before preparing arms'
        ) from exc
    return runtime


def source_revision() -> str | None:
    completed = subprocess.run(
        ['git', '-C', str(REPO), 'rev-parse', 'HEAD'],
        text=True,
        capture_output=True,
        check=False,
    )
    value = completed.stdout.strip()
    return value if completed.returncode == 0 and value else None


def freeze_runtime(study: Path) -> dict:
    """Freeze the current apparatus into an otherwise empty follow-up study.

    Historical studies retain their recorded runtime copies.  This operation
    deliberately refuses any nonempty directory rather than adding a new
    snapshot beside an earlier study's evidence.
    """
    study = study.resolve(strict=False)
    if study.exists():
        if not study.is_dir():
            raise RuntimeError('follow-up study path must be a directory')
        if any(study.iterdir()):
            raise RuntimeError('refusing to mutate a nonempty study; choose a fresh empty directory')
    else:
        study.mkdir(parents=True)
    runtime = study / 'frozen' / 'runtime-v3'
    runtime.mkdir(parents=True)
    for name in RUNTIME_FILES:
        shutil.copy2(HERE / name, runtime / name)
    shutil.copy2(HERE / 'fixtures' / 'app.py', runtime / 'fixture-app.py')
    shutil.copytree(
        REPO / 'skills' / 'shiploop',
        runtime / 'shiploop',
        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'),
    )
    file_hashes = {
        str(path.relative_to(runtime)): digest(path)
        for path in sorted(runtime.rglob('*'))
        if path.is_file()
    }
    metadata = {
        'schema': 'shiploop-capability-runtime-freeze-v1',
        'runtime_version': RUNTIME_VERSION,
        'created_at': utc_now(),
        'source_revision': source_revision(),
        'files': file_hashes,
    }
    (runtime / RUNTIME_MANIFEST).write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + '\n', encoding='utf-8'
    )
    validate_runtime_snapshot(runtime)
    return {
        'runtime': str(runtime),
        'manifest': str(runtime / RUNTIME_MANIFEST),
        'runtime_version': RUNTIME_VERSION,
        'file_count': len(file_hashes),
    }


def load_setup():
    spec = importlib.util.spec_from_file_location('capability_fixture_setup', HERE / 'fixture_setup.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def copy_skills(workspace: Path, metadata_only: bool = False):
    obsolete_catalog = workspace / 'skill-catalog.json'
    if obsolete_catalog.exists():
        obsolete_catalog.unlink()
    skills = workspace / 'skills'
    skills.mkdir(exist_ok=True)
    sources = [
        ('plan-test', REPO / 'skills/plan-test/SKILL.md', 'Generate executable tests matching the existing framework.', 'A readable project, command execution, and an installed test framework.'),
        ('skill-interop', REPO / 'skills/skill-interop/SKILL.md', 'Author or review portable skills across supported agent hosts.', 'An actual skill package whose portability needs review.'),
    ]
    entries = []
    for name, source, purpose, prereqs in sources:
        folder = skills / name
        folder.mkdir(exist_ok=True)
        body = source.read_text()
        metadata = {'name': name, 'version': digest(source), 'source': str(source), 'purpose': purpose, 'prerequisites': prereqs}
        if metadata_only and name == 'plan-test':
            metadata['procedure'] = 'Unavailable in this trial; use ordinary reasoning and existing native documentation.'
        else:
            (folder / 'SKILL.md').write_text(body)
            metadata['procedure'] = f'skills/{name}/SKILL.md'
        entries.append(metadata)
    old = skills / 'legacy-client'
    old.mkdir(exist_ok=True)
    (old / 'SKILL.md').write_text('---\nname: legacy-client\nversion: 2017-fixture\n---\n\nSynthetic obsolete guidance for a retired synchronous browser bridge. It assumes an old global client library and synchronous return values. Confirm compatibility with the actual project before use.\n')
    entries.append({'name':'legacy-client','version':'2017-fixture','source':'synthetic negative control','purpose':'Investigate a legacy synchronous client bridge.','prerequisites':'The retired synchronous bridge must actually be installed.','procedure':'skills/legacy-client/SKILL.md'})
    (skills / 'catalog.json').write_text(json.dumps(entries, indent=2)+'\n')


def install_probe(workspace: Path):
    target = workspace / 'tools'
    target.mkdir(exist_ok=True)
    for name in ('mcp_probe.py', 'real_gateway.py'):
        shutil.copy2(PRIOR / 'scripts' / name, target / name)
    cached_modules = PRIOR / 'runs/local_setup/workspace/acquired/mcp/node_modules'
    node_modules = workspace / 'vendor/node_modules'
    shutil.copytree(cached_modules, node_modules, symlinks=True)
    server = node_modules / '@modelcontextprotocol/server-filesystem/dist/index.js'
    # Reuse pinned cached package bytes, disclosed identically in paired arms.
    config = {'command': [shutil.which('node'), str(server), str(workspace/'runtime-observations')], 'cwd': str(workspace), 'timeout_seconds': 20}
    (target / 'filesystem-mcp.json').write_text(json.dumps(config, indent=2)+'\n')
    (target / 'CAPABILITIES.md').write_text(f'''# Available capabilities

Native Python standard library, shell commands through the provided workspace tool,
local HTTP access, and the existing framework are available. Existing skill metadata
is in skills/catalog.json. Inspect relevant procedure bodies when helpful.

A previously acquired official filesystem MCP is available as a temporary protocol
client operation, not a host-registered tool. Package @modelcontextprotocol/server-filesystem
2026.8.31 was copied from the prior cache into {server}; this study did not freshly download it.
tools/mcp_probe.py starts and closes it. Inspect tools/filesystem-mcp.json and use:
python3 tools/mcp_probe.py --config tools/filesystem-mcp.json --log mcp-observation.jsonl --calls '[{{"name":"list_directory","arguments":{{"path":"{workspace}/runtime-observations"}}}}]'
The allowed root is runtime-observations/. A denial is not permission to broaden it.
MCP is an optional inspection route. Native reads or HTTP may be sufficient.
''')


def packet(workspace: Path, stage: str, task: str, *, runtime: Path):
    skill = workspace / 'shiploop'
    shutil.copytree(runtime / 'shiploop', skill, ignore=shutil.ignore_patterns('__pycache__','*.pyc'), dirs_exist_ok=True)
    sys.path.insert(0, str(skill/'scripts'))
    import shiploop_navigator as nav
    run = workspace / 'shiploop-state'
    run.mkdir(exist_ok=True)
    state = nav.new_state(str(workspace), task)
    for _ in range(80):
        if state['stage'] == stage:
            break
        result = {'outcome':'done','summary':'Synthetic fixture preparation; preceding project work was not executed.'}
        if state['stage'] == 'plan':
            result['work_items']=[{'id':'W1','title':'Current controlled task'}]
        state = nav.apply(state, state['action']['id'], result)
    else:
        raise RuntimeError(stage)
    nav.save(run,state)
    result = subprocess.run([sys.executable,'-B',str(skill/'scripts/shiploop'),'next','--run-dir',str(run)],capture_output=True,text=True,check=True)
    return result.stdout


def prepare(study: Path, names: list[str], group='screen', style='screen'):
    runtime = runtime_snapshot(study)
    setup = load_setup()
    candidate=(study/'frozen/candidate.md').read_text()
    manifest=json.loads((study/'manifest.json').read_text())
    rng=random.Random(20260914)
    plans=[]
    for name in names:
        case,stage,task=TASKS[name]
        arm_labels = ('procedure','metadata') if style == 'skill' else ('initial','triggered') if style == 'timing' else ('current','candidate')
        for arm in arm_labels:
            ident=f'{group}-{name}-{arm}'
            base=study/'arms'/ident
            if base.exists():
                raise FileExistsError(base)
            base.mkdir(parents=True)
            workspace=base/'workspace'
            variant = ('metadata-only' if arm == 'metadata' else 'skill-procedure') if style == 'skill' else ('timing-stable' if name == 'env' else 'timing-new-gap') if style == 'timing' else 'baseline'
            layout=setup.create_case(case, workspace, variant=variant)
            if hasattr(setup,'export_worker'):
                setup.export_worker(layout)
            # No hidden reference implementation, mutant selector or oracle is shipped.
            copy_skills(workspace, metadata_only=arm == 'metadata')
            install_probe(workspace)
            if style == 'timing':
                stage = 'discovery'
                task = 'Initial inventory checkpoint: identify the local client/server entry points and available inspection resources. Save a concise PHASE1_NOTE.md from current evidence. Do not run mutation/authorization experiments yet; a second checkpoint will follow. Leave this action unaccepted and do not call its completion until the second checkpoint.'
            rendered=packet(workspace,stage,task, runtime=runtime)
            (workspace/'PACKET.md').write_text(rendered)
            common=f'''Execute only this controlled task in {workspace}.
The study is local and synthetic; no cloud mutation, new grants, global installation,
unrelated account/host reads, or publication. Other arms, study private data, and
evaluation oracles are outside scope. Use only the provided workspace tool for
files and commands. Tool help reports the remaining shared budget. You have at most
15 elapsed minutes /64 tool actions, stop exploration at13min/56actions, reserve
time for REPORT.md and cleanup. This includes tools, setup and commands.

Read SPEC.md, README.md, tools/CAPABILITIES.md and applicable local guidance.
The fixture may already have a served endpoint in service-ready.json; inspect it.
Use native facilities or existing skills/MCP when useful; no required tool selection.
Document supported findings, actual checks and limitations in REPORT.md. Preserve
input requirements. Follow the real current CLI packet and submit at most its one
completion; stop when it returns the next action. A planned check is not a pass.

Task: {task}

Public CLI packet:
{rendered}
'''
            prompt=common+('\nCandidate checkpoint instruction:\n'+candidate if arm!='current' else '')
            if style == 'timing':
                prompt += '\nFor this first checkpoint, preserve an unaccepted draft: PHASE1_NOTE.md is the output; do not submit a completion or claim the whole action done.\n'
                follow = ('The scope and evidence are unchanged. Use PHASE1_NOTE.md to finish the initial inventory. Check whether existing findings already suffice; no additional work requirement has been introduced.' if name == 'env' else 'New requirement at this checkpoint: determine whether the intended red actor can perform a move through the actual served service authorization boundary. The earlier inventory alone does not establish this. Record the observed readiness disposition; do not grant permissions or change configuration.')
                prompt2 = f'''Resume the same incomplete action in {workspace} using PHASE1_NOTE.md and the same cumulative gateway budget. Use only the provided workspace tool. {follow}
Save final supported findings and limits in REPORT.md and submit at most the current action's one completion. The first checkpoint did not complete preceding delivery work. Public packet:\n{rendered}\n'''
                if arm == 'triggered':
                    prompt2 += '\nCandidate checkpoint instruction:\n' + candidate
                (base/'prompt2.md').write_text(prompt2)
            (base/'prompt.md').write_text(prompt)
            inputs={str(p.relative_to(workspace)):digest(p) for p in workspace.rglob('*') if p.is_file()}
            armmeta={'id':ident,'group':group,'case':case,'stage':stage,'arm':arm,'style':style,'fixture_variant':variant,'workspace':str(workspace),'runtime_version':RUNTIME_VERSION,'runtime_manifest_sha256':digest(runtime / RUNTIME_MANIFEST),'prompt_sha256':digest(base/'prompt.md'),'input_hashes':inputs}
            if (base/'prompt2.md').exists():
                armmeta['prompt2_sha256'] = digest(base/'prompt2.md')
            (base/'input-manifest.json').write_text(json.dumps(armmeta,indent=2)+'\n')
            plans.append(ident)
    rng.shuffle(plans)
    manifest.setdefault('groups',{})[group]=plans
    manifest['status']='prepared_unvalidated'
    (study/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'study':str(study),'arms':plans},indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--study',type=Path,required=True)
    ap.add_argument('--cases',default='env,inner,outer,test')
    ap.add_argument('--group',default='screen')
    ap.add_argument('--style',choices=('screen','skill','timing'),default='screen')
    ap.add_argument('--freeze-runtime', action='store_true', help='freeze the current apparatus into a fresh empty study and stop')
    args=ap.parse_args()
    if args.freeze_runtime:
        print(json.dumps(freeze_runtime(args.study), indent=2, sort_keys=True))
        raise SystemExit(0)
    prepare(args.study.resolve(),args.cases.split(','),args.group,args.style)
