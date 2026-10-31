"""Mutation table: condition id -> list of (old, new) exact replacements in report.py (product code only)."""

PRICE_OLD = r'''_PRICE = re.compile(r"-?(?:[0-9]+\.?[0-9]*|\.[0-9]+)", re.ASCII)'''
UNITS_OLD = r'''_UNITS = re.compile(r"-?[0-9]+", re.ASCII)'''
NEG_OLD = '''        if text.startswith("-"):\n'''
NUM_OLD = '''        if not pattern.fullmatch(text):\n'''
NEXT_OLD = '''        next(reader, None)\n'''
PRINT_OLD = '''    print(json.dumps(summary), file=stdout)\n'''
RET_OLD = '''    return rows, skipped\n'''
EXC_PRINT_OLD = '''            print("report.py: error: cannot read %s: %s" % (path, reason), file=stderr)\n            return 1\n'''
EXC_PRINT = '''            print("report.py: error: cannot read %s: %s" % (path, reason), file=stderr)\n'''
SUMMARY_OLD = '''            "by_region": {k: _money(v) for k, v in sorted(revenue_by_region.items())},\n            "by_product": dict(sorted(units_by_product.items())),\n'''
SIZE = '__import__("os").path.getsize(argv[0])'
HDRONLY1 = '(not rows and len(argv) == 1 and %s > 0)' % SIZE


def pr(new):
    return (PRICE_OLD, new)


def un(new):
    return (UNITS_OLD, new)


def neg_skip(name, text):
    return (NEG_OLD, '''        if text.startswith("-") and (name, text) != (%r, %r):\n''' % (name, text))


def verb_mut(exc):
    return (EXC_PRINT_OLD,
            '''            verb = "open" if isinstance(error, %s) else "read"\n'''
            '''            print("report.py: error: cannot %%s %%s: %%s" %% (verb, path, reason), file=stderr)\n'''
            '''            return 1\n''' % exc)


def exc_prefix(code):
    return (EXC_PRINT_OLD, code + EXC_PRINT_OLD)


M = {}

# ---- R-1
M["R-1.2"] = [("    for path in argv:\n", "    for path in argv[:1]:\n")]
M["R-1.3"] = [("    for path in argv:\n", "    for path in dict.fromkeys(argv):\n")]
M["R-1.4"] = [('USAGE = "usage: python3', 'USAGE = "Usage: python3')]
M["R-1.5"] = [("        print(USAGE, file=stderr)\n", "        print(USAGE, file=stderr)\n        print(USAGE, file=stdout)\n")]
M["R-1.6"] = [("        print(USAGE, file=stderr)\n        return 1\n", "        print(USAGE, file=stderr)\n        return 2\n")]

# ---- R-2
M["R-2.1"] = [(NEXT_OLD, "")]
M["R-2.2"] = [(NEXT_OLD,
               '        header = next(reader, None)\n'
               '        if header is not None and len(header) != COLUMNS:\n'
               '            print("%s:1: expected %d columns, got %d" % (path, COLUMNS, len(header)), file=stderr)\n'
               '            skipped += 1\n')]
M["R-2.3"] = [pr(r'''_PRICE = re.compile(r"-?(?:[0-9]+\.?(?![0-9]{2}\Z)[0-9]*|\.[0-9]+)", re.ASCII)''')]
M["R-2.4"] = [('(COLUMNS, len(fields))', '(COLUMNS, len(fields) - (len(fields) == 4))')]
M["R-2.5"] = [('(COLUMNS, len(fields))', '(COLUMNS, len(fields) - (len(fields) == 6))')]
M["R-2.6"] = [("            if fields is None:\n                break\n",
               "            if fields is None:\n                break\n            if not fields:\n                continue\n")]
M["R-2.7"] = [un(r'''_UNITS = re.compile(r"-?(?:[0-9]+|abc)", re.ASCII)''')]
M["R-2.8"] = [un(r'''_UNITS = re.compile(r"-?[0-9]+(?:\.[0-9]+)?", re.ASCII)''')]
M["R-2.9"] = [un(r'''_UNITS = re.compile(r"-?[0-9][0-9_]*", re.ASCII)''')]
M["R-2.10"] = [un(r'''_UNITS = re.compile(r"-?[0-9]+(?:e[0-9]+)?", re.ASCII)''')]
M["R-2.11"] = [un(r'''_UNITS = re.compile(r"-?[0-9]*", re.ASCII)''')]
M["R-2.12"] = [neg_skip("units", "-1")]
M["R-2.13"] = [pr(r'''_PRICE = re.compile(r"-?(?:[0-9]+\.?[0-9]*|\.[0-9]+|abc)", re.ASCII)''')]
M["R-2.14"] = [pr(r'''_PRICE = re.compile(r"-?(?:[0-9]+\.?[0-9]*|\.[0-9]+|nan)", re.ASCII)''')]
M["R-2.15"] = [pr(r'''_PRICE = re.compile(r"-?(?:[0-9]+\.?[0-9]*|\.[0-9]+|inf)", re.ASCII)''')]
M["R-2.16"] = [pr(r'''_PRICE = re.compile(r"-?(?:[0-9]+\.?[0-9]*(?:e[0-9]+)?|\.[0-9]+)", re.ASCII)''')]
M["R-2.17"] = [pr(r'''_PRICE = re.compile(r"-?(?:[0-9]+\.?[0-9]*|\.[0-9]+|)", re.ASCII)''')]
M["R-2.18"] = [neg_skip("unit_price", "-0.5")]
M["R-2.19"] = [('(("units", units, _UNITS), ("unit_price", price, _PRICE))',
                '(("unit_price", price, _PRICE), ("units", units, _UNITS))')]
M["R-2.20"] = [("    fields = [f.strip() for f in fields]\n", "    raw = list(fields)\n    fields = [f.strip() for f in fields]\n"),
               ('''            return "non-numeric %s '%s'" % (name, text)''',
                '''            return "non-numeric %s '%s'" % (name, raw[3 if name == "units" else 4])'''),
               ('''            return "negative %s '%s'" % (name, text)''',
                '''            return "negative %s '%s'" % (name, raw[3 if name == "units" else 4])''')]
M["R-2.21"] = [("fields = [f.strip() for f in fields]", "fields = [f if i == 3 else f.strip() for i, f in enumerate(fields)]")]
M["R-2.22"] = [("fields = [f.strip() for f in fields]", "fields = [f if i == 4 else f.strip() for i, f in enumerate(fields)]")]
M["R-2.23"] = [("    _, region, product, units, price = fields\n",
                '    date, region, product, units, price = fields\n'
                '    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", date):\n'
                '        return "invalid date \'%s\'" % date\n')]
M["R-2.24"] = [("    _, region, product, units, price = fields\n",
                '    _, region, product, units, price = fields\n    if not region:\n        return "empty region"\n')]
M["R-2.25"] = [("    _, region, product, units, price = fields\n",
                '    _, region, product, units, price = fields\n    if not product:\n        return "empty product"\n')]
M["R-2.26"] = [(NEG_OLD, '''        if (name, text) == ("units", "0"):\n            return "negative %s '%s'" % (name, text)\n''' + NEG_OLD)]
M["R-2.27"] = [(NEG_OLD, '''        if (name, text) == ("unit_price", "0"):\n            return "negative %s '%s'" % (name, text)\n''' + NEG_OLD)]
M["R-2.28"] = [(NUM_OLD, '''        if not pattern.fullmatch(text) or (name, text) == ("unit_price", ".5"):\n''')]
M["R-2.29"] = [pr(r'''_PRICE = re.compile(r"-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)", re.ASCII)''')]
M["R-2.30"] = [neg_skip("units", "-0")]
M["R-2.31"] = [neg_skip("unit_price", "-0")]
M["R-2.32"] = [neg_skip("unit_price", "-.5")]
M["R-2.33"] = [('''    try:\n        count = int(units)\n    except ValueError:  # more digits than the interpreter's int<->str limit (4300 by default)\n        return "units too large '%s'" % units\n''',
                '''    count = int(units)\n''')]
M["R-2.34"] = [("        reader = csv.reader(handle)\n",
                '        reader = csv.reader(handle.read().replace("\\n", "\\r\\n").splitlines(True))\n')]
M["R-2.35"] = [('encoding="utf-8-sig"', 'encoding="ascii"')]

# ---- R-3
M["R-3.1"] = [("json.dumps(summary)", "json.dumps(summary, indent=1)")]
M["R-3.2"] = [("print(json.dumps(summary), file=stdout)", 'print(json.dumps(summary), file=stdout, end="")')]
M["R-3.3"] = [(SUMMARY_OLD,
               '''            "by_product": dict(sorted(units_by_product.items())),\n            "by_region": {k: _money(v) for k, v in sorted(revenue_by_region.items())},\n''')]
M["R-3.4"] = [("                skipped += 1\n                continue\n", "                skipped += 1\n                rows += 1\n                continue\n")]
M["R-3.5"] = [("_MONEY.multiply(Decimal(units), price)", "_MONEY.multiply(Decimal(1), price)")]
M["R-3.6"] = [('''            revenue_by_region[region] = _MONEY.add(\n                revenue_by_region[region], _MONEY.multiply(Decimal(units), price))\n''',
               '''            revenue_by_region[region] = Decimal(str(float(revenue_by_region[region]) + float(units) * float(price)))\n''')]
M["R-3.7"] = [('"revenue": _money(total),', '"revenue": float(_MONEY.quantize(total, Decimal("0.001"))),')]
M["R-3.8"] = [('"revenue": _money(total),', '"revenue": float(Context(prec=200, rounding=decimal.ROUND_HALF_EVEN).quantize(total, CENT)),')]
M["R-3.9"] = [("            total = _MONEY.add(total, amount)\n", "            total = _MONEY.add(total, _MONEY.quantize(amount, CENT))\n")]
M["R-3.10"] = [("{k: _money(v) for k, v in sorted(revenue_by_region.items())}", "{k: float(v) for k, v in sorted(revenue_by_region.items())}")]
M["R-3.11"] = [("{k: _money(v) for k, v in sorted(revenue_by_region.items())}", "{k: round(float(v), 2) for k, v in sorted(revenue_by_region.items())}")]
M["R-3.12"] = [('''            revenue_by_region[region] = _MONEY.add(\n                revenue_by_region[region],''',
                '''            revenue_by_region[product] = _MONEY.add(\n                revenue_by_region[product],''')]
M["R-3.13"] = [("units_by_product[product] += units", "units_by_product[region] += units")]
M["R-3.14"] = [("dict(sorted(units_by_product.items()))", "{k: float(v) for k, v in sorted(units_by_product.items())}")]
M["R-3.15"] = [("{k: _money(v) for k, v in sorted(revenue_by_region.items())}", "{k: _money(v) for k, v in revenue_by_region.items()}")]
M["R-3.16"] = [("dict(sorted(units_by_product.items()))", "dict(units_by_product.items())")]
M["R-3.17"] = [("json.dumps(summary)", 'json.dumps(summary, separators=(",", ":"))')]
M["R-3.18"] = [(PRINT_OLD, '''    print(re.sub(r"(\\d+\\.\\d)(?=[,}])", r"\\g<1>0", json.dumps(summary)), file=stdout)\n''')]

# ---- R-4
LINE_PRINT = '''                print("%s:%d: %s" % (path, line, parsed), file=stderr)\n'''
M["R-4.1"] = [('"%s:%d: %s" % (path, line, parsed)', '"%s:%d:%s" % (path, line, parsed)')]
M["R-4.2"] = [(LINE_PRINT, "                if skipped == 0:\n    " + LINE_PRINT)]
M["R-4.3"] = [("% (path, line, parsed)", '% (path.rsplit("/", 1)[-1], line, parsed)')]
M["R-4.4"] = [("line = reader.line_num + 1", "line = reader.line_num")]
M["R-4.5"] = [("line = reader.line_num + 1", "line = rows + skipped + 2")]
# extra probes (not frozen conditions, not in the rate)
X = {}
X["R-4.5x"] = [("            line = reader.line_num + 1\n            fields = next(reader, None)\n",
                "            fields = next(reader, None)\n            line = reader.line_num\n")]
X["R-2.35x"] = [('encoding="utf-8-sig"', 'encoding="utf-8"')]
M["R-4.6"] = [("        rows += file_rows\n", "        rows += file_rows if not file_skipped else 0\n")]
M["R-4.7"] = [(PRINT_OLD + "    return 2 if skipped else 0\n", "    if skipped:\n        return 2\n" + PRINT_OLD + "    return 0\n")]
M["R-4.8"] = [("return 2 if skipped else 0", "return 1 if skipped else 0")]
M["R-4.9"] = [("        skipped += file_skipped\n", "        skipped = file_skipped\n")]
M["R-4.10"] = [("return 2 if skipped else 0", "return 2 if skipped else (3 if rows else 0)")]
M["R-4.11"] = [(PRINT_OLD, '    if rows and not skipped:\n        print("ok", file=stderr)\n' + PRINT_OLD)]
M["R-4.12"] = [("COLUMNS = 5\n", "COLUMNS = 5\n_SEEN = [0]\n"),
               ("line = reader.line_num + 1", "line = reader.line_num + 1 + _SEEN[0]"),
               (RET_OLD, "    _SEEN[0] += reader.line_num\n" + RET_OLD)]
M["R-4.13"] = [("        reader = csv.reader(handle)\n",
                '        lines = handle.read().splitlines(True)\n'
                '        if lines and not lines[-1].endswith(("\\n", "\\r")):\n'
                '            lines.pop()\n'
                '        reader = csv.reader(lines)\n')]
M["R-4.14"] = [(PRINT_OLD, '    if skipped:\n        print("%d rows skipped" % skipped, file=stderr)\n' + PRINT_OLD)]

# ---- R-5
M["R-5.1"] = [verb_mut("FileNotFoundError")]
M["R-5.2"] = [verb_mut("IsADirectoryError")]
M["R-5.3"] = [verb_mut("PermissionError")]
M["R-5.4"] = [verb_mut("UnicodeDecodeError")]
M["R-5.5"] = [exc_prefix('            if isinstance(error, UnicodeDecodeError):\n                print(json.dumps({"rows": rows}), file=stdout)\n')]
M["R-5.6"] = [exc_prefix('            if isinstance(error, FileNotFoundError):\n                __import__("traceback").print_exc(file=stderr)\n')]
M["R-5.7"] = [exc_prefix('            if isinstance(error, FileNotFoundError) and not rows:\n                print("{}", file=stdout)\n')]
M["R-5.8"] = [(EXC_PRINT_OLD, EXC_PRINT + "            return 3 if isinstance(error, FileNotFoundError) and not rows else 1\n")]
M["R-5.9"] = [(EXC_PRINT_OLD, EXC_PRINT + "            return 2 if skipped else 1\n")]
M["R-5.10"] = [exc_prefix('            if isinstance(error, FileNotFoundError) and rows and not skipped:\n                print(json.dumps({"rows": rows}), file=stdout)\n')]
M["R-5.11"] = [("except (OSError, UnicodeDecodeError, csv.Error) as error:", "except (OSError, UnicodeDecodeError) as error:")]
M["R-5.12"] = [("totals too large to summarise (beyond about 1e197)", "totals too large to summarise")]
M["R-5.13"] = [('(beyond about 1e197)", file=stderr)\n        return 1\n', '(beyond about 1e197)", file=stderr)\n        return 2\n')]

# ---- R-6
M["R-6.1"] = [('"revenue": _money(total),', '"revenue": (0 if %s else _money(total)),' % HDRONLY1)]
M["R-6.2"] = [("return 2 if skipped else 0", "return 2 if skipped else (3 if %s else 0)" % HDRONLY1)]
M["R-6.3"] = [(NEXT_OLD, "        header = next(reader, None)\n"),
              (RET_OLD, '    if header is not None and not rows and not skipped:\n        print("%s: no data rows" % path, file=stderr)\n' + RET_OLD)]
M["R-6.4"] = [("    revenue_by_region = defaultdict(Decimal)\n",
               '    if len(argv) == 1 and __import__("os").path.isfile(argv[0]) and %s == 0:\n'
               '        print("report.py: error: empty file", file=stderr)\n'
               '        return 1\n' % SIZE + "    revenue_by_region = defaultdict(Decimal)\n")]
M["R-6.5"] = [(NEXT_OLD, "        header = next(reader, None)\n"),
              (RET_OLD, '    if header is not None and not rows and not skipped:\n        revenue_by_region.clear()\n        units_by_product.clear()\n' + RET_OLD)]
M["R-6.6"] = [(NEXT_OLD, "        header = next(reader, None)\n"),
              (RET_OLD, '    if header is None:\n        revenue_by_region.clear()\n        units_by_product.clear()\n' + RET_OLD)]
