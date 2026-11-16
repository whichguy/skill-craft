"""External evidence-only subprocess recorder; test and runtime behavior are unchanged."""
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time
import unittest

root = Path('/Users/dadleet/src/skill-craft-r19-20261115')
evidence = Path(__file__).resolve().parent
original_run = subprocess.run
original_test_run = unittest.TestCase.run
current = None

def test_run(self, *args, **kwargs):
    global current
    current = self.id()
    try:
        return original_test_run(self, *args, **kwargs)
    finally:
        current = None

def traced(*args, **kwargs):
    start = time.monotonic()
    row = {'test': current, 'argv': args[0] if args else kwargs.get('args'),
           'cwd': str(kwargs.get('cwd', os.getcwd())), 'shell': kwargs.get('shell', False),
           'input': kwargs.get('input')}
    try:
        result = original_run(*args, **kwargs)
        row.update(exit=result.returncode, stdout=result.stdout, stderr=result.stderr)
        return result
    except Exception as error:
        row.update(exception=repr(error), stdout=getattr(error, 'stdout', None),
                   stderr=getattr(error, 'stderr', None), exit=getattr(error, 'returncode', None))
        raise
    finally:
        row['seconds'] = time.monotonic() - start
        with (evidence / 'green-processes.jsonl').open('a') as stream:
            stream.write(json.dumps(row, default=str) + '\n')

subprocess.run = traced
unittest.TestCase.run = test_run
sys.path.insert(0, str(root / 'test'))
sys.argv = [str(root / 'test/shiploop-loops.test.py'), *sys.argv[1:]]
runpy.run_path(sys.argv[0], run_name='__main__')
