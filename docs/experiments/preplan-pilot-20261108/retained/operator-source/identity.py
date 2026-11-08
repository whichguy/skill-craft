import hashlib, json, subprocess, sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
paths=subprocess.check_output(['git','-C',str(root),'ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0')
h=hashlib.sha256(); n=0
for name in sorted(set(paths)):
    if not name or '__pycache__' in Path(name).parts or name.endswith('.pyc'): continue
    p=root/name
    if p.is_symlink(): data=('link:'+str(p.readlink())).encode()
    elif p.is_file(): data=p.read_bytes()
    else: data=b'<missing>'
    h.update(name.encode()+b'\0'+data+b'\0'); n+=1
print(json.dumps({'head':subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD']).decode().strip(),'status':subprocess.check_output(['git','-C',str(root),'status','--short']).decode(),'files':n,'sha256':h.hexdigest()},indent=2))
