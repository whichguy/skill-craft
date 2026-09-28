
import os, sys, time, subprocess
mode, start, run, action, summary, verb, cli = sys.argv[1:8]
path = os.path.join(run, "inbox", action + ".md")
text = "---\n" if False else None
while time.time() < float(start):
    pass
if mode in ("write", "atomic"):
    sys.path.insert(0, os.path.dirname(cli))
    import shiploop_store as store
    body = store.dumps({"outcome": "done", "summary": summary}, "result")
    if mode == "write":
        with open(path, "w") as f:
            f.write(body)
    else:
        tmp = path + ".tmp-" + str(os.getpid())
        with open(tmp, "w") as f:
            f.write(body)
        os.replace(tmp, path)
args = [sys.executable, cli, verb, "--run-dir", run]
if verb == "complete":
    args += ["--action", action, "--result", path]
os.execv(sys.executable, args)
