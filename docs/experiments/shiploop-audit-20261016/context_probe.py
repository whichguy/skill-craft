from pathlib import Path
import sys,json,copy,hashlib,re
REPO=Path('/Users/dadleet/src/skill-craft')
sys.path.insert(0,str(REPO/'skills/shiploop/scripts'))
import shiploop_navigator as nav
import shiploop_navigator_dry_run as driver
import shiploop_standalone_improve as bridge
import shiploop_reference as reference
out=Path('/tmp/shiploop-audit-20261016-analysis'); fixture=out/'fixture-repo'; fixture.mkdir(exist_ok=True)
run=out/'fixture-run'; run.mkdir(exist_ok=True)
home=fixture/'docs/shiploop'; home.mkdir(parents=True,exist_ok=True)
selected=bridge.resolve_skill(str(REPO/'skills/improve/SKILL.md'))
rows=driver.scenarios()['delivery']['steps']
results={}
for mode in ['empty','three-5000-character-files']:
 for name in ['spec.md','environment.md','architecture.md']:
  f=home/name
  if mode=='empty':
   if f.exists(): f.unlink()
  else:
   prefix='# Synthetic '+name+'\n\n'; text=prefix+('Controlled sizing fixture. No requirements or execution evidence.\n'*100)
   f.write_text(text[:4999]+'\n'); assert len(f.read_text())==5000
 state=nav.new_state(str(fixture),'Inspect the SDLC graph with synthetic declarations.',improve_skill=str(REPO/'skills/improve/SKILL.md'))
 packets=[]; handoffs=[]
 for row in rows:
  text=nav.render(driver.CORE,run,state)
  parts={}
  labels=['Current stage guidance:','Knowledge files this stage reads,','Handed off by earlier stages,','State: ']
  a=text.find('Current stage guidance:'); b=text.find('\nPause without consuming the action:',a)
  if a>=0: parts['stage_guidance_characters']=len(text[a:b if b>=0 else len(text)])
  packets.append({'stage':row['at'],'chars':len(text),**parts})
  current=nav.current_action(state)
  if row.get('command')=='finish-improve':
   child=state['active_improve']; bound=copy.deepcopy(state)
   bound['active_improve']=bridge.binding(state,child['action_id'],child['stage'],child['seed_result'],selected,improve_action=child['improve_action'])
   h=nav.improve_handoff_text(driver.CORE,run,bound)
   handoffs.append({'stage':child['stage'],'characters':len(h)})
   (out/f"handoff-{mode}-{child['stage']}.md").write_text(h)
   state=nav.finish_improve(state,child['action_id'],row['receipt'],row.get('final_result'))
  else: state=nav.apply(state,current['id'],row['result'])
 results[mode]={'packet_total':sum(p['chars'] for p in packets),'packets':packets,'packets_over_16000':sum(p['chars']>16000 for p in packets),'bound_handoff_total':sum(p['characters'] for p in handoffs),'bound_handoffs':handoffs,'shared_reference_characters':len(reference.render(state,run,reference.package_version()))}
results['scope']='Controlled synthetic corpus; each living file is exactly 5000 characters, not an observed project. Pure navigator and bound handoff rendering only; no live model, no child runtime, no complete CLI or Git operations. Raw handoffs are sizing fixtures, not receipts.'
(out/'context-measurements.json').write_text(json.dumps(results,indent=2))
for k,v in results.items():
 if isinstance(v,dict): print(k,json.dumps({a:b for a,b in v.items() if a!='packets'}))
print('per-stage guidance', json.dumps(results['empty']['packets']))
