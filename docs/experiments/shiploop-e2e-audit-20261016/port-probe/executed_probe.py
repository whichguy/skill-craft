import json, os, socket, subprocess, tempfile, time
from pathlib import Path

root = Path('/tmp/shiploop-e2e-audit-20261016-coverage')
root.mkdir(parents=True, exist_ok=True)
probe = Path(tempfile.mkdtemp(prefix='fixed-port-probe-', dir=root))
sibling = probe / 'sibling'
candidate = probe / 'candidate'
sibling.mkdir()
candidate.mkdir()
port = 39171

# Confirm this repository's first Battleship check port is currently free.
with socket.socket() as sock:
    sock.bind(('127.0.0.1', port))

(sibling / 'server.js').write_text(
    "require('http').createServer((req,res)=>{res.writeHead(200,{'content-type':'text/html'});res.end('<title>Battleship</title> stale sibling app')}).listen(Number(process.env.PORT));\n"
)
(candidate / 'server.js').write_text(
    "require('http').createServer((req,res)=>res.end('candidate')).listen(Number(process.env.PORT));\n"
)
sibling_proc = subprocess.Popen(
    ['node', 'server.js'], cwd=sibling, env={**os.environ, 'PORT': str(port)},
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)
try:
    ready = False
    for _ in range(50):
        if sibling_proc.poll() is not None:
            raise RuntimeError('sibling server exited before probe')
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=.05):
                ready = True
                break
        except OSError:
            time.sleep(.02)
    if not ready:
        raise RuntimeError('sibling server did not listen')

    # Same shell recipe and port as cases.json's first Battleship product check.
    recipe = (
        f"PORT={port} node server.js > /dev/null 2>&1 & pid=$!; ok=1; "
        f"for i in $(seq 1 20); do curl -fsS http://127.0.0.1:{port}/ -o page.html 2>/dev/null "
        f"&& ok=0 && break; sleep 0.5; done; "
        "[ $ok -eq 0 ] && grep -qi battleship page.html; rc=$?; "
        "kill $pid 2>/dev/null; rm -f page.html; exit $rc"
    )
    checked = subprocess.run(['/bin/sh', '-c', recipe], cwd=candidate, capture_output=True, text=True, timeout=3)
    result = {
        'probe': 'fixed-port stale-sibling false-green reproduction',
        'port': port,
        'sibling_started': sibling_proc.poll() is None,
        'candidate_bind_expected_to_fail': True,
        'exact_case_check_exit_code': checked.returncode,
        'exact_case_check_passed': checked.returncode == 0,
        'candidate_server_still_running': False,
        'artifact_dir': str(probe),
        'scope': 'isolated temporary servers only; no repository source, model, or deployment touched'
    }
    (probe / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
finally:
    sibling_proc.terminate()
    try:
        sibling_proc.wait(timeout=1)
    except subprocess.TimeoutExpired:
        sibling_proc.kill()
        sibling_proc.wait(timeout=1)
