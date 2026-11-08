"""Check the pilot's actual overlay and fixture boundaries without a model."""
from pathlib import Path
import importlib.util
import json
import shutil
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT/'test/shiploop_e2e'),str(ROOT/'skills/shiploop/scripts')]
import overlay
import shiploop_prompts as original

with tempfile.TemporaryDirectory() as tmp:
    scripts=Path(tmp)/'scripts'
    shutil.copytree(ROOT/'skills/shiploop/scripts',scripts)
    result=overlay.apply(overlay.load(HERE/'candidate-overlay.json'),scripts)
    spec=importlib.util.spec_from_file_location('candidate_prompts',scripts/'shiploop_prompts.py')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    changed=[k for k in original.DUTIES if original.DUTIES[k]!=mod.DUTIES[k]]
    assert changed==['plan'],changed
    assert original.PLANNING_REVIEW_FOCUS==mod.PLANNING_REVIEW_FOCUS
    assert original.DUTIES['test-strategy']==mod.DUTIES['test-strategy']
    baseline=original.DUTIES['plan']; candidate=mod.DUTIES['plan']
    start=candidate.index('Before defining work items, assess')
    end=candidate.index('2. Plan backward',start)
    assert candidate[:start]+candidate[end:]==baseline
    assert start>candidate.index('1. Reopen the accepted')
    print(json.dumps({'overlay':result,'changed_duties':changed,'added_characters':len(candidate)-len(baseline),'plan_improve_identical':True,'test_strategy_identical':True,'baseline_preserved':True},indent=2))
