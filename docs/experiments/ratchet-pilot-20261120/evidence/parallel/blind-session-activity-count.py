import json
import re
import sys

FAILRE=re.compile(r'not ok|✖|# fail [1-9]')
def load(f):
    with open(f) as handle:
        rows=[json.loads(l) for l in handle]
    res={r['toolCallId']:r for r in rows if r.get('type')=='tool_call_update'}
    cmds=[]
    for r in rows:
        if r.get('type')=='tool_call' and r.get('toolName')=='run_terminal_command':
            u=res.get(r['toolCallId'],{}).get('rawOutput',{}) or {}
            cmds.append({'id':r['toolCallId'],'cmd':r['rawInput']['command'],'out':u.get('output_for_prompt') or '','exit':u.get('exit_code')})
    edits=sum(1 for r in rows if r.get('type')=='tool_call' and r.get('toolName')=='search_replace')
    end=[r for r in rows if r.get('type')=='end']
    usage=end[-1].get('usage') if end else None
    return rows,cmds,edits,usage
def strip_heredoc_writes(c):
    # remove bodies of 'cat > file <<EOF ... EOF' and 'cat >> file <<EOF'
    return re.sub(r"cat >>? [^\n]*<<'?\\?'?(\w+)'?\n.*?\n\1\n?",'CATWRITE\n',c,flags=re.DOTALL)
def is_acc_run(c):
    s=strip_heredoc_writes(c)
    if 'acceptance.json' in s and re.search(r'subprocess\.run|spawn\(|exec\(|execSync|spawnSync',s): return 'runner'
    if re.search(r'node [^\n]*--test[^\n]*acceptance/|node\s+(--[^\n ]+ )*acceptance/',s) : return 'direct'
    return None
READ=re.compile(r'\b(cat|sed -n|rg|grep|nl|head|tail|git show)\b')
FILE=re.compile(r'(?<![\w./-])((?:src|bin|scripts)/[\w./-]*\.\w+)')
def prod_tests(c):
    s=strip_heredoc_writes(c)
    return bool(re.search(r'npm test|node --test(?![^\n]*acceptance)',s)) and not is_acc_run(c)
def main(f):
    _rows,cmds,edits,usage=load(f)
    print(f, 'cmds',len(cmds),'edits',edits,'usage',usage)
    acc=[];prod=[];files=set()
    for i,c in enumerate(cmds,1):
        k=is_acc_run(c['cmd'])
        s=strip_heredoc_writes(c['cmd'])
        if k: acc.append((i,k,c))
        if prod_tests(c['cmd']): prod.append((i,c))
        if READ.search(s) and 'CATWRITE' not in s[:0]:
            # only count files in reading commands; avoid counting writes
            for m in FILE.findall(s): files.add(m)
    for i,k,c in acc:
        print(f" ACC #{i} {k} exit={c['exit']} fail={bool(FAILRE.search(c['out']))}")
    for i,c in prod:
        shown=c['cmd'][:120].replace('\n',' ')
        print(f" PROD #{i} exit={c['exit']} {shown}")
    print(' files',len(files),sorted(files))
main(sys.argv[1])
