#!/usr/bin/env python3
"""Freeze one fictional follow-up case; render a real discovery action packet."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def hashes(root):
    return {str(p.relative_to(root)): digest(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def prepare(source, fixture, output):
    source, fixture, output = map(lambda p: p.resolve(), (source, fixture, output))
    assert not output.exists(), 'Each attempt needs a new output directory'
    output.mkdir(parents=True)
    package = output / 'package'
    shutil.copytree(source, package, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    case = output / 'case'
    shutil.copytree(fixture, case)
    workspace = case / 'workspace'
    helper = source.parents[1] / 'test/experiments/shiploop_discovery_handoff/apparatus/prepare.py'
    spec = importlib.util.spec_from_file_location('packet_setup', helper)
    setup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(setup)
    task = ('Discover a retry UI for existing review case CASE-17. Internal sources use '
            'both Orion Analytics and Orion Review Gateway; establish what each name '
            'means, which owner and approved retry policy apply to this review case, '
            'and what is still needed before implementation. Use available internal '
            'knowledge readers and Teams if available. Do not implement.')
    packet, loaded = setup.render_packet(package, case, workspace, task)
    launch = case / 'participant/LAUNCH.md'
    launch.write_text(f'''# Bounded follow-up discovery

Work in {workspace}. {task}

Read README.md, SHIPLOOP.md, relevant local source, and the actual discovery
packet at {packet}. Use its relevant linked guidance. The fictional reader is
documented by `python3 -B {case / 'adapter.py'} --help`; do not open its implementation,
data, expected answers or coordinator files. All content is fictional and may be
retained in this private fixture's notes and receipts.

The coordinator's fresh test-runner baseline for this exact frozen workspace is
BASELINE.txt. Inspect that current command/output/hash receipt before source
discovery. It is this exercise's first verification activity; it is only a narrow
fixture check and proves no remote access or runtime behavior. Do not rerun it.

Write DISCOVERY.md (<=900 words), update SHIPLOOP.md, and write the ordinary
discovery completion result to RESULT.json with outcome, summary and evidence_refs
as required by the packet. Stop there; the coordinator submits that exact result
for a separate transport experiment. Do not submit a callback or run Improve.

Only these three output files may change; documented adapter reads append their
receipt log. No source/test changes, network, real accounts, installs, messages,
product implementation or delegation. One attempt, 8 minutes or 24 host actions;
return an honest partial result at the bound. Prior Navigator/Improve transitions
only initialized the section sample and are not completed workflow work.
''')
    manifest = {'source': str(source), 'source_hashes': hashes(source),
                'package_hashes': hashes(package), 'fixture_hashes': hashes(fixture),
                'input_hashes': hashes(workspace), 'loaded_navigator': loaded,
                'packet_sha256': digest(packet), 'launch_sha256': digest(launch),
                'setup_helper_sha256': digest(helper),
                'limits': 'New single attempt; synthetic section setup, no real MCP or full workflow proof'}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
    print(launch)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'fixture', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    prepare(**vars(parser.parse_args()))
