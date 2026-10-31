import os

OUT = '/Users/dadleet/src/skill-craft/docs/experiments/prompt-template-review-20261031/conditions/claude-csv-report/witnesses'
W = {}

# ---------- R-1
W["R-1.2"] = '''
a = f(HDR + row()); b = f(HDR + row("1", "0.10", "south"))
c, o, e = run(a, b)
ok(c == 0 and js(o)["rows"] == 2 and js(o)["revenue"] == 7.6, (c, o, e))
'''
W["R-1.3"] = '''
a = f(HDR + row())
c, o, e = run(a, a)
j = js(o)
ok(c == 0 and j["rows"] == 2 and j["revenue"] == 15.0 and j["by_product"] == {"widget": 6}, (c, o, e))
'''
W["R-1.4"] = '''
c, o, e = run()
ok(e.startswith("usage:") and e.count("\\n") == 1, e)
'''
W["R-1.5"] = '''
c, o, e = run()
ok(o == "", o)
'''
W["R-1.6"] = '''
c, o, e = run()
ok(c == 1, c)
'''

# ---------- R-2
W["R-2.1"] = '''
# a first line that looks like a valid data row is still the header: skipped, not counted
p = f(b"a,b,c,5,5.00\\n" + row())
c, o, e = run(p)
ok((c, e, js(o)["rows"]) == (0, "", 1), (c, o, e))
'''
W["R-2.2"] = '''
p = f(b"a,b\\n" + row())
c, o, e = run(p)
ok((c, e, js(o)["rows"]) == (0, "", 1), (c, o, e))
'''
W["R-2.3"] = '''
p = f(HDR + row())
c, o, e = run(p)
j = js(o)
ok((c, e, j["rows"], j["revenue"]) == (0, "", 1, 7.5), (c, o, e))
'''
W["R-2.4"] = '''
p = f(HDR + b"2024-01-01,north,widget,3\\n")
c, o, e = run(p)
ok(e == "%s:2: expected 5 columns, got 4\\n" % p, e)
'''
W["R-2.5"] = '''
p = f(HDR + b"2024-01-01,north,widget,3,2.50,x\\n")
c, o, e = run(p)
ok(e == "%s:2: expected 5 columns, got 6\\n" % p, e)
'''
W["R-2.6"] = '''
p = f(HDR + b"\\n" + row())
c, o, e = run(p)
ok(e == "%s:2: expected 5 columns, got 0\\n" % p and js(o)["rows"] == 1, (c, o, e))
'''


def reason(units, price, expect, tag):
    return '''
p = f(HDR + row(%r, %r))
c, o, e = run(p)
ok(e == "%%s:2: %s\\n" %% p and c == 2, (c, e))
''' % (units, price, expect)


for cid, u in (("R-2.7", "abc"), ("R-2.8", "1.5"), ("R-2.9", "1_0"), ("R-2.10", "1e3"), ("R-2.11", "")):
    W[cid] = reason(u, "1", "non-numeric units '%s'" % u, cid)
W["R-2.12"] = reason("-1", "1", "negative units '-1'", "")
for cid, pz in (("R-2.13", "abc"), ("R-2.14", "nan"), ("R-2.15", "inf"), ("R-2.16", "1e3"), ("R-2.17", "")):
    W[cid] = reason("1", pz, "non-numeric unit_price '%s'" % pz, cid)
W["R-2.18"] = reason("1", "-0.5", "negative unit_price '-0.5'", "")
W["R-2.19"] = reason("abc", "xyz", "non-numeric units 'abc'", "")
W["R-2.20"] = '''
p = f(HDR + row(" abc ", "1"))
c, o, e = run(p)
ok(e == "%s:2: non-numeric units 'abc'\\n" % p, e)
'''
W["R-2.21"] = '''
p = f(HDR + row(" 7 ", "1"))
c, o, e = run(p)
ok((c, e, js(o)["by_product"]) == (0, "", {"widget": 7}), (c, o, e))
'''
W["R-2.22"] = '''
p = f(HDR + row("3", " 2.50 "))
c, o, e = run(p)
ok((c, e, js(o)["revenue"]) == (0, "", 7.5), (c, o, e))
'''
W["R-2.23"] = '''
p = f(HDR + row(date="not-a-date"))
c, o, e = run(p)
ok((c, e, js(o)["rows"]) == (0, "", 1), (c, o, e))
'''
W["R-2.24"] = '''
p = f(HDR + row(region=""))
c, o, e = run(p)
ok((c, e, js(o)["by_region"]) == (0, "", {"": 7.5}), (c, o, e))
'''
W["R-2.25"] = '''
p = f(HDR + row(product=""))
c, o, e = run(p)
ok((c, e, js(o)["by_product"]) == (0, "", {"": 3}), (c, o, e))
'''
W["R-2.26"] = '''
p = f(HDR + row("0", "1"))
c, o, e = run(p)
ok((c, e, js(o)["rows"]) == (0, "", 1), (c, o, e))
'''
W["R-2.27"] = '''
p = f(HDR + row("1", "0"))
c, o, e = run(p)
ok((c, e, js(o)["rows"]) == (0, "", 1), (c, o, e))
'''
W["R-2.28"] = '''
p = f(HDR + row("1", ".5"))
c, o, e = run(p)
ok((c, e, js(o)["revenue"]) == (0, "", 0.5), (c, o, e))
'''
W["R-2.29"] = '''
p = f(HDR + row("1", "5."))
c, o, e = run(p)
ok((c, e, js(o)["revenue"]) == (0, "", 5.0), (c, o, e))
'''
W["R-2.30"] = reason("-0", "1", "negative units '-0'", "")
W["R-2.31"] = reason("1", "-0", "negative unit_price '-0'", "")
W["R-2.32"] = reason("1", "-.5", "negative unit_price '-.5'", "")
W["R-2.33"] = '''
big = "9" * 5000
p = f(HDR + row() + row(big, "1") + row("1", "0.10", "south"))
c, o, e = run(p)
ok(e == "%s:3: units too large '%s'\\n" % (p, big) and c == 2 and js(o)["rows"] == 2, (c, e[:200]))
'''
W["R-2.34"] = '''
p = f((HDR + row()).replace(b"\\n", b"\\r\\n"))
c, o, e = run(p)
j = js(o)
ok((c, e, j["rows"], j["revenue"]) == (0, "", 1, 7.5), (c, o, e))
'''
W["R-2.35"] = '''
p = f(b"\\xef\\xbb\\xbf" + HDR + row())
c, o, e = run(p)
j = js(o)
ok((c, e, j["rows"], j["revenue"]) == (0, "", 1, 7.5), (c, o, e))
'''

# ---------- R-3
W["R-3.1"] = '''
a = f(HDR + row()); b = f(HDR + row("1", "0.10", "south"))
c, o, e = run(a, b)
ok(o.count("\\n") == 1 and len(o.splitlines()) == 1 and isinstance(js(o), dict), o)
'''
W["R-3.2"] = '''
c, o, e = run(f(HDR + row()))
ok(o.endswith("\\n") and o.count("\\n") == 1, repr(o))
'''
W["R-3.3"] = '''
c, o, e = run(f(HDR + row()))
ok(list(js(o)) == ["rows", "revenue", "by_region", "by_product"], o)
'''
W["R-3.4"] = '''
c, o, e = run(f(HDR + row() + row("x", "1") + row("1", "1")))
ok(js(o)["rows"] == 2, (c, o, e))
'''
W["R-3.5"] = '''
c, o, e = run(f(HDR + row("2", "1.50") + row("3", "0.25")))
ok(js(o)["revenue"] == 3.75, o)
'''
W["R-3.6"] = '''
# exact decimal sum 0.335 rounds to 0.34 (half-up and half-even agree); a float accumulation gives 0.33
c, o, e = run(f(HDR + row("1", "0.3") + row("1", "0.035")))
ok(js(o)["revenue"] == 0.34, o)
'''
W["R-3.7"] = '''
c, o, e = run(f(HDR + row("1", "1.234")))
ok(js(o)["revenue"] == 1.23, o)
'''
W["R-3.8"] = '''
# 1.005 rounds half up to 1.01 (half-even would give 1.0)
c, o, e = run(f(HDR + row("1", "1.005")))
ok(js(o)["revenue"] == 1.01, o)
'''
W["R-3.9"] = '''
c, o, e = run(f(HDR + row("1", "0.004") + row("1", "0.004", "south")))
ok(js(o)["revenue"] == 0.01, o)
'''
W["R-3.10"] = '''
c, o, e = run(f(HDR + row("1", "1.234")))
ok(js(o)["by_region"] == {"north": 1.23}, o)
'''
W["R-3.11"] = '''
c, o, e = run(f(HDR + row("1", "2.675")))
ok(js(o)["by_region"] == {"north": 2.68}, o)
'''
W["R-3.12"] = '''
c, o, e = run(f(HDR + row("3", "2.50", "north", "widget") + row("1", "0.10", "south", "gadget") + row("2", "1.00", "north", "gadget")))
ok(js(o)["by_region"] == {"north": 9.5, "south": 0.1}, o)
'''
W["R-3.13"] = '''
c, o, e = run(f(HDR + row("3", "1", "north", "widget") + row("1", "1", "south", "widget") + row("2", "1", "north", "gadget")))
ok(js(o)["by_product"] == {"gadget": 2, "widget": 4}, o)
'''
W["R-3.14"] = '''
c, o, e = run(f(HDR + row("3", "1") + row("1", "1")))
ok('"by_product": {"widget": 4}' in o, o)
'''
W["R-3.15"] = '''
c, o, e = run(f(HDR + row("1", "1", "south") + row("1", "1", "north") + row("1", "1", "east")))
ok(list(js(o)["by_region"]) == ["east", "north", "south"], o)
'''
W["R-3.16"] = '''
c, o, e = run(f(HDR + row("1", "1", "north", "zeta") + row("1", "1", "north", "alpha") + row("1", "1", "north", "mid")))
ok(list(js(o)["by_product"]) == ["alpha", "mid", "zeta"], o)
'''
EXACT = '{"rows": 2, "revenue": 7.6, "by_region": {"north": 7.5, "south": 0.1}, "by_product": {"widget": 4}}\\n'
W["R-3.17"] = '''
c, o, e = run(f(HDR + row() + row("1", "0.10", "south")))
ok(o == '%s', repr(o))
''' % EXACT
W["R-3.18"] = '''
c, o, e = run(f(HDR + row() + row("1", "0.10", "south")))
ok('"revenue": 7.6,' in o and '"north": 7.5,' in o and "7.60" not in o and "7.50" not in o, o)
'''

# ---------- R-4
BADLINE = b"2024-01-01,north,widget,3\\n"
W["R-4.1"] = '''
import re
p = f(HDR + row() + b"2024-01-01,north,widget,3\\n")
c, o, e = run(p)
ok(re.fullmatch(re.escape(p) + r":[0-9]+: expected 5 columns, got 4\\n", e), e)
'''
W["R-4.2"] = '''
p = f(HDR + row() + b"2024-01-01,north,widget,3\\n" + b"2024-01-01,north,widget,x,1\\n")
c, o, e = run(p)
ok(e == "%s:3: expected 5 columns, got 4\\n%s:4: non-numeric units 'x'\\n" % (p, p), e)
'''
W["R-4.3"] = '''
os.makedirs(os.path.join(D, "sub"), exist_ok=True)
f(HDR + row() + b"2024-01-01,north,widget,3\\n", "sub/a.csv")
c, o, e = run("sub/a.csv", cwd=D)
ok(e == "sub/a.csv:3: expected 5 columns, got 4\\n", e)
'''
W["R-4.4"] = '''
p = f(HDR + b"2024-01-01,north,widget,3\\n" + row())
c, o, e = run(p)
ok(e == "%s:2: expected 5 columns, got 4\\n" % p, e)
'''
W["R-4.5"] = '''
p = f(HDR + b'2024-01-01,"no\\nrth",widget,1,1.00\\n2024-01-01,north,widget,abc,1\\n')
c, o, e = run(p)
ok(e == "%s:4: non-numeric units 'abc'\\n" % p and js(o)["rows"] == 1, (e, o))
'''
W["R-4.6"] = '''
p = f(HDR + row() + b"2024-01-01,north,widget,3\\n" + row("1", "0.10", "south"))
c, o, e = run(p)
ok(js(o)["rows"] == 2, (c, o, e))
'''
W["R-4.7"] = '''
p = f(HDR + row() + b"2024-01-01,north,widget,3\\n")
c, o, e = run(p)
ok(js(o)["rows"] == 1, (c, o, e))
'''
W["R-4.8"] = '''
p = f(HDR + row() + b"2024-01-01,north,widget,3\\n")
c, o, e = run(p)
ok(c == 2, c)
'''
W["R-4.9"] = '''
bad = f(HDR + b"2024-01-01,north,widget,3\\n"); good = f(HDR + row())
c, o, e = run(bad, good)
ok(c == 2, c)
'''
W["R-4.10"] = '''
c, o, e = run(f(HDR + row()))
ok(c == 0, c)
'''
W["R-4.11"] = '''
c, o, e = run(f(HDR + row()))
ok(e == "", e)
'''
W["R-4.12"] = '''
a = f(HDR + row() * 5)
b = f(HDR + row() + b"2024-01-01,north,widget,3\\n")
c, o, e = run(a, b)
ok(e == "%s:3: expected 5 columns, got 4\\n" % b, e)
'''
W["R-4.13"] = '''
p = f(HDR + row() + b"2024-01-01,north,widget,x,1")
c, o, e = run(p)
ok(e == "%s:3: non-numeric units 'x'\\n" % p and c == 2, (c, e))
'''
W["R-4.14"] = '''
p = f(HDR + row() + b"2024-01-01,north,widget,3\\n")
c, o, e = run(p)
ok(e == "%s:3: expected 5 columns, got 4\\n" % p, e)
'''

# ---------- R-5
W["R-5.1"] = '''
m = os.path.join(D, "missing.csv")
c, o, e = run(m)
ok(e.startswith("report.py: error: cannot read %s:" % m), e)
'''
W["R-5.2"] = '''
m = os.path.join(D, "adir"); os.mkdir(m)
c, o, e = run(m)
ok(e.startswith("report.py: error: cannot read %s:" % m), e)
'''
W["R-5.3"] = '''
ok(os.geteuid() != 0, "cannot test permissions as root")
p = f(HDR + row()); os.chmod(p, 0)
c, o, e = run(p)
os.chmod(p, 0o644)
ok(e.startswith("report.py: error: cannot read %s:" % p), e)
'''
W["R-5.4"] = '''
p = f(HDR + row() + b"\\xff\\n")
c, o, e = run(p)
ok(e.startswith("report.py: error: cannot read %s:" % p), e)
'''
W["R-5.5"] = '''
p = f(HDR + row() + b"\\xff\\n")
c, o, e = run(p)
ok(o == "", o)
'''
W["R-5.6"] = '''
m = os.path.join(D, "missing.csv")
c, o, e = run(m)
ok("Traceback" not in e and "cannot read" in e, e)
'''
W["R-5.7"] = '''
c, o, e = run(os.path.join(D, "missing.csv"))
ok(o == "", o)
'''
W["R-5.8"] = '''
c, o, e = run(os.path.join(D, "missing.csv"))
ok(c == 1, c)
'''
W["R-5.9"] = '''
a = f(HDR + row() + b"d,n\\n"); m = os.path.join(D, "nope.csv")
c, o, e = run(a, m)
ok(c == 1, c)
'''
W["R-5.10"] = '''
a = f(HDR + row()); m = os.path.join(D, "nope.csv")
c, o, e = run(a, m)
ok(o == "" and c == 1, (c, o))
'''
W["R-5.11"] = '''
p = f(HDR + b"2024-01-01,north,widget,1," + b"9" * 200000 + b"\\n")
c, o, e = run(p)
ok(e.startswith("report.py: error: cannot read %s:" % p) and "Traceback" not in e and o == "" and c == 1, (c, o, e[:200]))
'''
W["R-5.12"] = '''
p = f(HDR + b"2024-01-01,north,widget,1" + b"0" * 250 + b",1\\n")
c, o, e = run(p)
ok(e == "report.py: error: totals too large to summarise (beyond about 1e197)\\n", e)
'''
W["R-5.13"] = '''
p = f(HDR + b"2024-01-01,north,widget,1" + b"0" * 250 + b",1\\n")
c, o, e = run(p)
ok(o == "" and c == 1 and "Traceback" not in e, (c, o, e[:200]))
'''

# ---------- R-6
W["R-6.1"] = '''
c, o, e = run(f(HDR))
ok(o == EMPTY, repr(o))
'''
W["R-6.2"] = '''
c, o, e = run(f(HDR))
ok(c == 0, c)
'''
W["R-6.3"] = '''
c, o, e = run(f(HDR))
ok(e == "", e)
n = f(HDR + row()); h = f(HDR)
c, o, e = run(n, h)
ok(e == "", e)
'''
W["R-6.4"] = '''
c, o, e = run(f(b""))
ok((c, o, e) == (0, EMPTY, ""), (c, o, e))
'''
W["R-6.5"] = '''
n = f(HDR + row()); h = f(HDR)
alone = run(n)
ok(alone[0] == 0 and run(n, h) == alone and run(h, n) == alone, (alone, run(n, h), run(h, n)))
'''
W["R-6.6"] = '''
n = f(HDR + row()); z = f(b"")
alone = run(n)
ok(alone[0] == 0 and run(n, z) == alone and run(z, n) == alone, (alone, run(n, z), run(z, n)))
'''

for cid, body in W.items():
    with open(os.path.join(OUT, cid + ".py"), "w") as handle:
        handle.write("import os\nfrom _lib import *\n" + body.lstrip("\n"))
print(len(W), "witnesses")
