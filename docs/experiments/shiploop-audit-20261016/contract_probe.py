from pathlib import Path
import sys,json,copy
repo=Path('/Users/dadleet/src/skill-craft');sys.path.insert(0,str(repo/'skills/shiploop/scripts'))
import shiploop_navigator as nav
import shiploop_navigator_dry_run as driver
import shiploop_reference as ref
import shiploop_stage_spec as spec
import shiploop_standalone_improve as bridge
import shiploop_loops as loops
out=Path('/tmp/shiploop-audit-20261016-analysis'); fixture=out/'contract-fixture'; fixture.mkdir(exist_ok=True); run=out/'contract-run'
result={}
for mode in ['stage','none']:
 state=nav.new_state(str(fixture),'Controlled contract probe',planning_review=mode,improve_skill=str(repo/'skills/improve/SKILL.md'))
 reference=ref.render(state,run,'1.4.0'); start=reference.index('ShipLoop starts an Improve child'); end=reference.index('Run only the checks',start)
 result[mode]={'reviewed_stages':list(spec.reviewed_stages(mode)),'reference_schedule':reference[start:end].strip()}
state=nav.new_state(str(fixture),'Controlled multi-step chain review probe',delegation='ask-agent',improve_skill=str(repo/'skills/improve/SKILL.md'))
for original in driver.scenarios()['delivery']['steps']:
 row=copy.deepcopy(original)
 if row['at']=='step-plan': row['result']['steps']=[{'id':'S1','task':'First step','paths':['src/a.py'],'deps':[]},{'id':'S2','task':'Second step','paths':['src/b.py'],'deps':['S1']}]
 action=nav.current_action(state)
 if row.get('command')=='finish-improve':
  child=state['active_improve']
  if child['stage']=='implement':
   bound=copy.deepcopy(state);bound['active_improve']=bridge.binding(state,child['action_id'],child['stage'],child['seed_result'],bridge.resolve_skill(str(repo/'skills/improve/SKILL.md')),improve_action=child['improve_action'])
   handoff=nav.improve_handoff_text(driver.CORE,run,bound)
   focus=handoff[handoff.index('Implementation step review focus.'):]; focus=focus[:focus.index('Do not write tests')+160]
   result['chain']={'effective_scope_before_completion':scope,'review_focus':focus,'contains_all_paths': all(p in handoff for p in ['src/a.py','src/b.py'])}
   (out/'chain-improve-handoff.md').write_text(handoff); break
  state=nav.finish_improve(state,child['action_id'],row['receipt'])
 else:
  if row['at']=='implement': scope=loops._implement_scope(state,'W1',action['id'])
  state=nav.apply(state,action['id'],row['result'])
(out/'contract-findings.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
