"""Dump the quick tier's selection (targeted ids) for EVERY tracked path of this checkout: python3 dump_selection.py OUT.json"""
import sys, json, subprocess, importlib.util
sys.dont_write_bytecode = True
root = "/Users/dadleet/src/skill-craft/.claude/worktrees/cifix-ece1d3"
spec = importlib.util.spec_from_file_location("suite_catalog", root + "/test/suite_catalog.py")
m = importlib.util.module_from_spec(spec); sys.modules["suite_catalog"] = m; spec.loader.exec_module(m)
paths = subprocess.run(["git", "-C", root, "ls-files"], capture_output=True, text=True, check=True).stdout.split("\n")
out = {p: sorted(m.targeted([p])) for p in paths if p}
json.dump(out, open(sys.argv[1], "w"))
print(len(out), "paths;", sum(1 for v in out.values() if v), "select at least one suite")
