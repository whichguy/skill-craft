"""Descriptive extraction; no adoption threshold or significance test."""
from pathlib import Path
import json,re,sys

ROOT=Path(__file__).resolve().parent.parent
OP=ROOT/'operator'

def document(text):
    text=text.strip()
    if text.startswith('```'):
        text=re.sub(r'^```(?:json)?\s*','',text);text=re.sub(r'\s*```$','',text)
    return json.loads(text)

def norm(text):return re.sub(r'\s+',' ',text).strip()

def analyze():
    manifest=json.loads((OP/'manifest.json').read_text());rows=[]
    for cell in manifest['cells']:
        out=Path(cell['out']);graded=OP/'graded'/cell['id']
        row={k:cell[k] for k in ('id','case','rep','arm','cohort')}
        done=OP/(cell['id']+'-complete.json')
        row['attempt']=json.loads(done.read_text()) if done.exists() else None
        if (out/'metrics.json').exists():
            m=json.loads((out/'metrics.json').read_text())
            span=m.get('span') or {}
            row['host_seconds']=(span['ended']-span['started']) if all(span.get(k) is not None for k in ('started','ended')) else None
            row['tokens']=m.get('tokens');row['unmeasured']=m.get('unmeasured');row['stages']=m.get('stages')
            row['improve_reviews']=m.get('improve_reviews');row['shiploop_failures']=m.get('shiploop_failures')
        findings=[]
        if (out/'events.jsonl').exists():
            for n,line in enumerate((out/'events.jsonl').read_text().splitlines(),1):
                try:e=json.loads(line)
                except ValueError:continue
                if e.get('type')!='tool_call':continue
                arg=json.dumps(e.get('rawInput') or {})
                other=sorted(set(re.findall(r'/runs/(sample-\d+)',arg))-{cell['id']})
                if other:findings.append({'event':n,'kind':'other-sample-reference','samples':other})
                if str(ROOT/'operator') in arg or str(ROOT/'source') in arg:findings.append({'event':n,'kind':'operator-or-source-reference'})
                if str(ROOT/'arms') in arg:findings.append({'event':n,'kind':'shared-arm-build-reference-requires-review'})
                if re.search(r'(?:/\.codex/auth\.json|/\.aws/|/\.ssh/)',arg):findings.append({'event':n,'kind':'credential-path-reference'})
                name=e.get('toolName') or e.get('title') or ''
                if name in ('web_search','mcp_tool') or re.search(r'spawn|collab|agent_tool',name):findings.append({'event':n,'kind':'extra-capability-requires-review','tool':name})
        row['access_audit_findings']=findings
        row['access_audit_scope']='Heuristic scan of executed tool arguments for cross-sample/operator/source/credential paths; not an OS read fence or proof against computed paths.'
        if (graded/'metadata.json').exists():
            meta=json.loads((graded/'metadata.json').read_text());row['completion']=meta['completion']
            row['plugin_identity_matches']=meta['plugin_build']==meta['plugin_installed']==manifest['arms'][cell['arm']]['digest']
        if (graded/'judge.json').exists():
            call=json.loads((graded/'judge.json').read_text());row['judge_spec']=call['spec'];row['judge_outside']=call['outside']
            try:
                j=document(call['text']);row['judgment']=j
                bundle=json.loads((graded/'bundle.json').read_text())
                pieces=[]
                def texts(x):
                    if isinstance(x,str):
                        pieces.append(x)
                        # Tool outputs may themselves be serialized JSON with a
                        # stdout string. Validate quotes against decoded stdout
                        # as well as its retained JSON representation.
                        try:nested=json.loads(x)
                        except ValueError:nested=None
                        if isinstance(nested,(dict,list)):texts(nested)
                    elif isinstance(x,dict):
                        for v in x.values():texts(v)
                    elif isinstance(x,list):
                        for v in x:texts(v)
                texts(bundle);hay=norm('\n'.join(pieces))
                expected=set(bundle['obligations']);given=[c['id'] for c in j['criteria']]
                row['criterion_set_valid']=len(given)==len(expected) and set(given)==expected
                row['quote_failures']=[c['id'] for c in j['criteria'] if not c.get('quote') or norm(c['quote']) not in hay]
                row['score']=sum(c['grade'] for c in j['criteria'])
                row['possible']=2*len(expected)
                row['false_readiness_count']=len(j.get('false_readiness',[]))
                row['material_rework_count']=sum(r.get('value')=='valuable' for r in j.get('decision_rework',[]))
                row['unnecessary_investigation_count']=len(j.get('unnecessary_investigation',[]))
            except (ValueError,KeyError,TypeError) as exc:row['judge_parse_error']=str(exc)
        rows.append(row)
    pairs=[]
    for case in manifest['registration']['cases']:
        for rep in range(1,3):
            cells=[r for r in rows if r['case']==case and r['rep']==rep]
            pair={'case':case,'rep':rep,'ids':{r['arm']:r['id'] for r in cells}}
            a=next(r for r in cells if r['arm']=='current');b=next(r for r in cells if r['arm']=='early')
            for field in ('score','host_seconds','material_rework_count','unnecessary_investigation_count'):
                pair[field+'_delta_early_minus_current']=(b[field]-a[field]) if a.get(field) is not None and b.get(field) is not None else None
            pairs.append(pair)
    report={'scope':'Descriptive four-scenario planning pilot; no significance or adoption decision','rows':rows,'pairs':pairs}
    (OP/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'finished':sum(r['attempt'] is not None for r in rows),'graded':sum('score' in r for r in rows),'rows':[{k:r.get(k) for k in ('id','case','rep','arm','completion','score','possible','host_seconds','quote_failures','access_audit_findings')} for r in rows]},indent=2))

if __name__=='__main__':analyze()
