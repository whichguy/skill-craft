from pathlib import Path
import copy, datetime, hashlib, json, sys
ROOT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'apparatus'))
import seed
import preflight
BASE=json.loads((ROOT/'registration-002.json').read_text())
OUT=ROOT/'followup-fixtures-003'
OUT.mkdir(exist_ok=False)
ids=['cell-05','cell-09','cell-10','cell-14']
before=seed.source_identity();seed.dump(OUT/'source-pre.json',before)
reg=copy.deepcopy(BASE)
reg.update(registration_id='R05-003',registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),subjects=4,subjects_launched=0,cells=[],design='Four separately registered fresh protocol follow-ups for R05-002 incomplete cells; not a replacement sixteen-cell campaign or an efficacy comparison')
reg['preceding_registration']={'path':str(ROOT/'registration-002.json'),'sha256':seed.digest(ROOT/'registration-002.json'),'outcome':'16/16 diagnosis and disposition PASS; 12 protocol PASS, four protocol INCOMPLETE. Preserve all verdicts.'}
reg['transport_correction']={'sandbox':'danger-full-access','approval_policy':'never','environment':{'SHIPLOOP_KEEPALIVE':'off'},'source_control':'test/shiploop_e2e/hosts.py:469-473 production Codex launcher','reason':'Focused real-CLI probes reproduce Git object snapshot writes denied under workspace-write and successful under production harness permissions. No production change; only owned disposable fixture writes.','production_delta':[],'probe_evidence':[str(ROOT/'permission-probes-001'),str(ROOT/'permission-probes-002')]}
reg['subject_order']='One fresh subject completes before the remaining three run, maximum concurrency three. No in-place retries.'
for key in ids:
    old=next(x for x in BASE['cells'] if x['id']==key)
    s=seed.Seed(OUT/'subjects',OUT/'seed-logs',old['situation'],old['boundary'])
    row=s.seed(); row['repetition']=old['repetition']; row['locators']=preflight.locators(row); row['hashes']=seed.tree(s.base)
    cell=copy.deepcopy(old)
    for a,b in [('workspace','workspace'),('run','run'),('assignment','assignment'),('environment_script','environment'),('actual_stage','stage'),('producer_action','action'),('active_improve','active_improve'),('handoff','handoff'),('candidate_head','candidate_head'),('old_head','old_head')]:cell[a]=row[b]
    cell.update(fixture_tree_run_hashes=row['hashes'],native_final_response=str(ROOT/'followups-003'/key/'native-final.md'),complete_tool_trace=str(ROOT/'followups-003'/key/'events.jsonl'),judge_output=str(ROOT/'followups-003-judgments'/key/'judgment.json'),status='REGISTERED_NOT_LAUNCHED',supplemental_reference_and_hygiene_audit=str(OUT/'preparation.json'),protocol_followup_for=key,original_verdict='INCOMPLETE')
    reg['cells'].append(cell)
    seed.dump(OUT/(key+'-seed.json'),row)
    assert seed.tree(s.base)==row['hashes']
after=seed.source_identity();seed.dump(OUT/'source-post.json',after)
assert before==after and before['head']==reg['source']['sha'] and not before['status']
seed.dump(OUT/'preparation.json',{'status':'PASS','source_unchanged':True,'fresh_cells':ids,'initial_bind_present':{c['id']:bool(list((Path(c['run'])/'improve').glob('*-bind.md'))) for c in reg['cells']},'semantic_preflight':'Existing reference-proof-002 frozen; no probes or callbacks run on these subjects after assignment creation.'})
script=(ROOT/'run_subjects.py').read_text()
script=script.replace("'--sandbox', 'workspace-write',","'--sandbox', 'danger-full-access', '-c', 'approval_policy=\"never\"',")
script=script.replace("REG['subjects'] == len(REG['cells']) == 16","REG['subjects'] == len(REG['cells']) == 4")
script=script.replace("'expected': 16,","'expected': 4,")
(ROOT/'run_followups.py').write_text(script)
seed.dump(ROOT/'registration-003.json',reg)
files=['registration-003.json','run_followups.py','judge-instructions.md','apparatus/seed.py','apparatus/local_store.py','apparatus/preflight-002/reference-proof.json','followup-fixtures-003/preparation.json']
seed.dump(ROOT/'registration-003-freeze.json',{'status':'REGISTERED','registered_utc':reg['registered_utc'],'source':reg['source']['sha'],'cells':ids,'sha256':{name:seed.digest(ROOT/name) for name in files}})
print(json.dumps({'status':'REGISTERED','subjects':4,'fresh_cells':ids,'source_unchanged':before==after}))
