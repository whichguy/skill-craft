import hashlib, json, os, subprocess, sys, tempfile, time
from pathlib import Path
source=Path('/Users/dadleet/Documents/Codex/experiments/shiploop-preplan-pilot-20261108-f2qois1r/source')
sys.path.insert(0,str(source/'skills/rubric-eval/scripts'))
import model_call
prompt=Path(sys.argv[1]); dest=Path(sys.argv[2])
if dest.exists(): raise SystemExit('Refusing to overwrite an existing call')
content=prompt.read_text()
spec=model_call.resolve('codex:gpt-6-astra@xhigh')
record={'text':'','input_tokens':None,'output_tokens':None,'seconds':0.0,'outside':None,'spec':spec['spec'],'transport':'codex-stdin-v2','prompt_sha256':hashlib.sha256(content.encode()).hexdigest()}
started=time.monotonic()
# Same isolated home, model, effort and read-only sandbox as model_call._codex;
# stdin changes only prompt transport and avoids the OS argv-size limit.
with tempfile.TemporaryDirectory(prefix='rubric-eval-') as cwd:
    home=model_call.codex_home();(home/'home').mkdir(exist_ok=True)
    env={k:os.environ[k] for k in ('PATH','HOME','LANG','TERM') if k in os.environ}
    env.update(CODEX_HOME=str(home),HOME=str(home/'home'))
    argv=['codex','exec','--ignore-user-config','--skip-git-repo-check','-m',spec['model'],'-s','read-only','-C',cwd,'--json','-c',f'model_reasoning_effort="{spec["effort"]}"','-']
    record['argv']=argv
    try:
        result=subprocess.run(argv,input=content,capture_output=True,text=True,timeout=3600,env=env)
        record['exit']=result.returncode
        dest.with_suffix('.events.jsonl').write_text(result.stdout)
        dest.with_suffix('.stderr.log').write_text(result.stderr)
        events=[]
        for line in result.stdout.splitlines():
            try:events.append(json.loads(line))
            except ValueError:pass
        messages=[e['item'].get('text','') for e in events if e.get('type')=='item.completed' and (e.get('item') or {}).get('type')=='agent_message']
        record['text']=messages[-1] if messages else ''
        turns=[e['usage'] for e in events if e.get('type')=='turn.completed' and isinstance(e.get('usage'),dict)]
        if turns:
            record.update(input_tokens=sum(u.get('input_tokens',0) for u in turns),output_tokens=sum(u.get('output_tokens',0) for u in turns))
        record['outside']=model_call.codex_outside(events,cwd)
        record['tool_items']=[e['item']['type'] for e in events if e.get('type')=='item.completed' and (e.get('item') or {}).get('type') in ('command_execution','file_change','mcp_tool_call','web_search')]
    except (OSError,subprocess.TimeoutExpired) as exc:
        record['error']=str(exc);record['exit']=None
record['seconds']=round(time.monotonic()-started,1)
record['prompt_path']=str(prompt)
record['requested_model_attestation']='Exact model and effort requested; provider served identity not independently exposed.'
dest.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'path':str(dest),'spec':record['spec'],'text_chars':len(record['text']),'outside':record['outside'],'seconds':record['seconds']}))
raise SystemExit(0 if record['text'] and record['outside']==[] and record.get('exit')==0 and record.get('tool_items')==[] else 1)
