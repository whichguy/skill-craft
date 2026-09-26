import ast, re, pathlib, collections
res = collections.defaultdict(list)
for f in sorted(pathlib.Path("out").glob("S*.md")):
    t = f.read_text(); cell = f.stem.rsplit("-", 1)[0]
    blocks = re.findall(r"# file: (\S+)\n```python\n(.*?)```|```python\n# file: (\S+)\n(.*?)```", t, re.S)
    blocks=[(a or c, b or d) for a,b,c,d in blocks]
    src = "\n".join(b for n, b in blocks if n.endswith(".py") and "errors" not in n)
    try: tree = ast.parse(src)
    except Exception as e: res[cell].append(f"PARSE-FAIL"); continue
    fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    if cell.startswith("S1"):
        writers = [n for n, fn in fns.items() if "csv.writer" in ast.unparse(fn)]
        v = "PASS-compose" if len(writers) == 1 else f"FAIL-dup{writers}"
    else:
        sc = fns.get("shipping_cost")
        args = [a.arg for a in sc.args.args + sc.args.kwonlyargs] if sc else None
        tax = [n for n, fn in fns.items() if "taxable" in ast.unparse(fn)]
        helper = [n for n in fns if n not in ("shipping_cost",) and n not in tax]
        v = ("PASS-separate" if args == ["order"] and tax and "shipping_cost" not in tax
             else f"FAIL-fused args={args} tax={tax}") + (f" +helper{helper}" if helper else "")
    res[cell].append(v)
for c, v in res.items(): print(c, v)
