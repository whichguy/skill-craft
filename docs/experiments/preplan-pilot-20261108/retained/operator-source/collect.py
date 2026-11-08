"""Collect complete decision artifacts and selected application tool evidence.

Raw streams remain alongside every bundle. Only framework packet/guide output is
omitted from the judge view, never application observations or adverse results.
"""
from pathlib import Path
import hashlib, json, re, sys

ROOT=Path('/Users/dadleet/Documents/Codex/experiments/shiploop-preplan-pilot-20261108-f2qois1r')
SOURCE=ROOT/'source'
SUITE=SOURCE/'docs/experiments/preplan-pilot-20261108'
sys.path.insert(0,str(SOURCE/'skills/shiploop/scripts'))
import shiploop_store as store

def digest(root):
    h=hashlib.sha256(); count=0
    for p in sorted(root.rglob('*')):
        if not p.is_file() or p.is_symlink() or '__pycache__' in p.parts or p.suffix=='.pyc': continue
        h.update(str(p.relative_to(root)).encode()+b'\0'+p.read_bytes()+b'\0'); count+=1
    return {'files':count,'sha256':h.hexdigest()}

def events(out):
    result=[]
    for n,l in enumerate((out/'events.jsonl').read_text().splitlines(),1):
        try: result.append((n,json.loads(l)))
        except ValueError: pass
    return result

def collect(out):
    inv=json.loads((out/'invocation.json').read_text())
    run=Path(inv['seeded']['run_dir']); state=store.read_record(run/'state.md')
    rows=[r for r in state['history'] if r['stage']=='plan']
    plans=[{'action':r['action'],'outcome':r['outcome'],'initial':state.get('improve_results',{}).get(r['action'],{}).get('seed_result'), 'final':state.get('accepted',{}).get(r['action']), 'improve_receipt':state.get('improve_results',{}).get(r['action'])} for r in rows]
    child=state.get('active_improve') or {}
    if child.get('stage')=='plan': plans.append({'action':child['action_id'],'outcome':'pending-review','initial':child['seed_result'],'final':None,'improve_receipt':None})
    es=events(out)
    calls=[]; omitted=[]; notices=[]
    for n,e in es:
        if e.get('type')=='text': notices.append({'event':n,'text':e.get('data','')})
        if e.get('type')!='tool_call_update': continue
        raw=e.get('rawOutput') or {}; cmd=raw.get('command','') or ''
        output=raw.get('output_for_prompt','')
        framework=bool(re.search(r'/skills/[^\s]+/(?:scripts|references|SKILL\.md)|/scripts/shiploop(?:["\s]|$)|/packets/|/active\.md',cmd))
        # Compound commands reading application files remain in the evidence view.
        application=bool(re.search(r'(?:src/|tests/|data/|docs/shiploop/|planning-experiments|probe[._-]|scratch/)',cmd))
        row={'event':n,'command':cmd,'exit_code':raw.get('exit_code'),'status':e.get('status')}
        if framework and not application:
            row.update(output_omitted='framework packet or guide output; raw stream retained',output_sha256=hashlib.sha256(str(output).encode()).hexdigest())
            omitted.append(row)
        else:
            row['output']=output;calls.append(row)
    project=Path(state['repo']); files={}
    for base in [project/'docs',run/'notes']:
        if not base.exists():continue
        for p in sorted(base.rglob('*')):
            if p.is_file() and p.suffix in ('.md','.json','.txt','.log','.py'):
                files[str(p)]=p.read_text(errors='replace')
    # Include the review's own notes and probes, avoiding runtime controls/contracts.
    improve=project/'.shiploop-improve'
    if improve.exists():
        for p in sorted(improve.rglob('*')):
            if p.is_file() and p.suffix in ('.md','.txt','.log','.py') and ('review-' in p.name or 'experiment' in str(p) or 'planning-investigation' in p.name):
                files[str(p)]=p.read_text(errors='replace')
    supplied={str(p.relative_to(SUITE/'fixtures'/inv['case'])):p.read_text(errors='replace') for p in (SUITE/'fixtures'/inv['case']).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    usage=[e.get('usage') for _,e in es if e.get('type')=='end']
    resources=[json.loads(l) for l in (out/'resources.jsonl').read_text().splitlines() if l.strip()]
    result=json.loads((out/'slice-result.json').read_text()) if (out/'slice-result.json').exists() else None
    receipt_checks=[]
    for plan in plans:
        rec=plan['improve_receipt'] or {}
        terminal=run/'improve'/plan['action']/'terminal.json'
        expected=rec.get('identities',{}).get('terminal_packet_sha256')
        receipt_checks.append({'action':plan['action'],'runtime_phase':rec.get('runtime_phase'),'archived_terminal_exists':terminal.is_file(),'terminal_hash_matches':bool(expected and terminal.is_file() and hashlib.sha256(terminal.read_bytes()).hexdigest()==expected)})
    successful_commands=[(e.get('rawOutput') or {}).get('command','') or '' for _,e in es if e.get('type')=='tool_call_update' and (e.get('rawOutput') or {}).get('exit_code')==0]
    runtime_executed=any('until_loop_ephemeral.py' in c for c in successful_commands)
    completion=bool(result and result['pass'] and plans and receipt_checks[-1]['runtime_phase']=='complete' and receipt_checks[-1]['terminal_hash_matches'] and runtime_executed)
    evidence={'case_request':inv['seeded'].get('prompt',json.loads((SUITE/'cases.json').read_text())[inv['case']]['prompt']), 'obligations':json.loads((SUITE/'obligations.json').read_text())[inv['case']], 'supplied_files':supplied, 'plans':plans,'planning_artifacts':files,'application_tool_evidence':calls,'framework_command_index':omitted,'subject_messages':notices,'completion':{'slice':result,'verified_plan_improve_done':completion,'state_status':state.get('status'),'stage':state.get('stage')}}
    def mask(text): return text.replace(str(out),'TRIAL').replace(str(ROOT),'OPERATOR').replace(str(SOURCE),'SOURCE')
    bundle=mask(json.dumps(evidence,indent=2))
    metadata={'case':inv['case'],'model':inv['model'],'effort':inv['effort'],'plan_count':len(plans),'completion':completion,'receipt_checks':receipt_checks,'runtime_executed':runtime_executed,'slice_pass':result.get('pass') if result else None,'improve_keys':[list(p['improve_receipt'] or {}) for p in plans],'plugin_build':digest(Path(inv['plugin_dir'])),'plugin_installed':digest(Path(inv['plugin']['path'])),'usage':usage,'host_commands':[x['leader']['command'] for x in resources if x.get('kind')=='group' and isinstance(x.get('leader'),dict)],'bundle_characters':len(bundle),'application_tools':len(calls),'framework_tools':len(omitted)}
    return bundle,metadata

if __name__=='__main__':
    out=Path(sys.argv[1]);dest=Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True)
    bundle,meta=collect(out)
    (dest/'bundle.json').write_text(bundle+'\n');(dest/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(json.dumps({k:v for k,v in meta.items() if k not in ('host_commands',)},indent=2))
