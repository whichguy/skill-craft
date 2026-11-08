"""Fresh, randomized Astra comparison of each matched pair's decision evidence."""
from pathlib import Path
import concurrent.futures,json,random,subprocess,sys

ROOT=Path(__file__).resolve().parent.parent
OP=ROOT/'operator'
sys.path.insert(0,str(OP))
from analyze import document

INSTRUCTION='''Compare two planning outcomes on the same request. The labels are randomized and do not identify a treatment. Evaluate consequential correctness, supported readiness and useful planning decisions first. An experiment's existence, extra forms, stricter prose or more checks are not wins by themselves. Source inspection and valid reused evidence are fully legitimate. Preserve distinctions between implementation acceptance still due, a probe observation and an unavailable boundary. A plan can correctly remain conditional.

Use the complete initial and final plan records and the cited decision evidence below. The paired view retains product documents, investigation notes, review notes and probe artifacts, and omits duplicate runtime receipts, framework handoffs and the full command transcript already examined in the individual judgment. Individual judgments are evidence to challenge, not authority. Identify factual errors in them when the actual plan/evidence disagrees, and identify an unresolved issue if it requires omitted raw command evidence. Compare meaningful review rework separately from final quality. Do not call a retained disposable scratch data file a material harm solely because cleanup is unmentioned; explain any effect on the outcome, experiment validity, authority, sensitive data or running resources. Likewise, an extra command is a cost observation unless it causes a consequential regression. Do not equate a tiny rubric-point difference with a demonstrated improvement.

Return JSON only: {"final_quality":"A_better|B_better|tie|inconclusive","reason":"...","decisive_evidence":[{"side":"A|B","quote":"exact short text","locator":"...","consequence":"..."}],"initial_plan_and_rework":"...","earlier_evidence_value":"...","harms_or_lost_requirements":["..."],"individual_judgment_corrections":["..."],"confidence":"low|medium|high","limits":["..."]}. No tools, no arm inference, no model or score preference. If both support the same consequential outcome, say tie even if one is more elaborate. This is a small diagnostic planning pilot, not a release decision.
'''

def view(cell):
    d=OP/'graded'/cell['id']
    b=json.loads((d/'bundle.json').read_text());j=document(json.loads((d/'judge.json').read_text())['text'])
    plans=[{k:v for k,v in p.items() if k!='improve_receipt'} for p in b['plans']]
    artifacts={k:v for k,v in b['planning_artifacts'].items() if '/docs/' in k or '/run/notes/' in k or '/reviews/review-' in k or '/.experiments/' in k or k.endswith(('planning-investigation.md','checks.md'))}
    omitted=[k for k in b['planning_artifacts'] if k not in artifacts]
    return {'request':b['case_request'],'obligations':b['obligations'],'plans':plans,'planning_artifacts':artifacts,'omitted_framework_artifact_paths':omitted,'individual_judgment':j,'completion':b['completion']}

def one(pair):
    name=f'{pair[0]["case"]}-{pair[0]["rep"]}';dest=OP/'pairs'/name;dest.mkdir(parents=True,exist_ok=True)
    if (dest/'judge.json').exists():return {'pair':name,'status':'EXISTS'}
    mapping={label:c['id'] for label,c in zip(['A','B'],pair)}
    # The mapping is outside the text given to the judge.
    (dest/'mapping.json').write_text(json.dumps(mapping,indent=2)+'\n')
    content={label:view(c) for label,c in zip(['A','B'],pair)}
    prompt=INSTRUCTION+'\n\nPAIR EVIDENCE\n'+json.dumps(content,indent=2)
    (dest/'prompt.txt').write_text(prompt)
    result=subprocess.run([sys.executable,'-B',str(OP/'judge_call.py'),str(dest/'prompt.txt'),str(dest/'judge.json')],capture_output=True,text=True)
    (dest/'call.log').write_text(result.stdout+result.stderr)
    return {'pair':name,'exit':result.returncode,'characters':len(prompt)}

if __name__=='__main__':
    manifest=json.loads((OP/'manifest.json').read_text());rng=random.Random(manifest['registration']['order_seed']+991)
    pairs=[]
    for case in manifest['registration']['cases']:
        for rep in range(1,3):
            pair=[c for c in manifest['cells'] if c['case']==case and c['rep']==rep];rng.shuffle(pair)
            if sys.argv[1:] and f'{case}-{rep}' not in sys.argv[1:]:continue
            if all((OP/'graded'/c['id']/'judge.json').exists() for c in pair):pairs.append(pair)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(one,pairs):print(json.dumps(result),flush=True)
