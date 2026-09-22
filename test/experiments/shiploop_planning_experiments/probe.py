#!/usr/bin/env python3
"""Disposable apparatus for the planning pilot, not a model quality test."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import tempfile


def connection(operation: str, database: str) -> dict:
    script = (
        "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); "
        + ("c.execute('create table seeded(v text)'); "
           "c.execute(\"insert into seeded values ('seed')\"); c.commit(); "
           if operation == 'seed' else '')
        + "print(c.execute('select v from seeded').fetchall())"
    )
    command = [sys.executable, '-B', '-c', script, database]
    result = subprocess.run(command, text=True, capture_output=True, timeout=10, check=False)
    return {'command': command, 'exit_code': result.returncode,
            'stdout': result.stdout, 'stderr': result.stderr}


def run(case: str) -> dict:
    result = {'case': case, 'python': sys.version, 'platform': platform.platform(),
              'apparatus': str(Path(__file__).resolve())}
    with tempfile.TemporaryDirectory(prefix='shiploop-plan-probe-') as scratch:
        root = Path(scratch)
        if case == 'A':
            result['sqlite'] = sqlite3.sqlite_version
            result['observations'] = {
                'memory_seed': connection('seed', ':memory:'),
                'memory_consumer': connection('consume', ':memory:'),
                'file_seed': connection('seed', str(root / 'shared.sqlite')),
                'file_consumer': connection('consume', str(root / 'shared.sqlite')),
            }
        else:
            source, destination = root / 'source', root / 'destination'
            source.write_bytes(b'NEW-SOURCE-BYTES')
            destination.write_bytes(b'EXISTING-DESTINATION-BYTES')
            observations = {'before': destination.read_text(), 'returned': False, 'error': None}
            try:
                source.rename(destination)
                observations['returned'] = True
            except OSError as exc:
                observations['error'] = {'type': type(exc).__name__, 'message': str(exc)}
            observations['after'] = destination.read_text() if destination.exists() else None
            observations['source_exists'] = source.exists()
            result['observations'] = observations
    result['scratch_removed'] = not Path(scratch).exists()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', choices=('A', 'B'))
    args = parser.parse_args()
    print(json.dumps(run(args.case), indent=2))
