#!/usr/bin/env python3
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
s=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(s/'frozen'))
from study_inputs import validate_study_inputs
validate_study_inputs(s)
spec=importlib.util.spec_from_file_location('frozen_fixture_facts',s/'frozen/fixtures.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
c=json.loads((s/'private/oracle-calibration.json').read_text())
rows=[]
for family,case in f.CASES.items():
 expected={'schema':'shiploop-probe-decisions-family-judge-packet/1','family':family,'task':case['task'],
 'required':list(case['required']),'forbidden':list(case['forbidden']),
 'calibrated_reference_observations':c['families'][family]['reference'],'calibration_limits':c.get('limits')}
 raw=(json.dumps(expected,indent=2,sort_keys=True)+'\n').encode()
 path=s/f'private/judge-packets/{family}.json'
 assert raw==path.read_bytes(),f'{family} packet differs from frozen source and calibration'
 rows.append({'family':family,'exact_reconstruction':True,'sha256':hashlib.sha256(raw).hexdigest(),
 'review_already_launched':(s/f'reviews/{family}-r0').exists()})
print(json.dumps({'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'frozen_manifest_sha256':hashlib.sha256((s/'frozen-inputs.json').read_bytes()).hexdigest(),
 'method':'exact bytes reconstructed from manifest-validated frozen CASES and calibration; no edits',
 'packets':rows},indent=2))
