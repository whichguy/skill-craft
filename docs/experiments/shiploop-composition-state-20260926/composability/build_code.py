"""Build prompts for the composability experiment: 2 scenarios x 2 rubric variants."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4] / "skills" / "shiploop" / "scripts"))
import shiploop_prompts as p

A = p.CODE_CRAFT
B = A.replace(
    "Add no\n   dependency, option or fallback without a present need.",
    "Add no\n   dependency, option or fallback without a present need. An argument\n"
    "   that lets an existing unit serve this change instead of a copy is a\n   present need.")
B = B.replace("KISS and YAGNI limit features and abstractions.",
              "KISS and YAGNI limit features and speculative abstractions.")
B += """9. Compose before you build. Before writing a new unit, evaluate reusing an
   existing one unchanged, composing existing ones, or augmenting one (a new
   argument, an extension point, or a shared piece extracted from existing
   code) while its current callers keep working. Augment only when the units
   share one meaning, not merely similar code: a near-copy of existing logic
   is a defect, and so is a parameter that fuses two different rules. State
   the option chosen and why in one line.
"""
assert A != B and B.count("present need") == 2

S1 = {"report.py": '''"""Export order rows for the finance team."""
import csv
import io

from errors import ExportError

REQUIRED = ("id", "amount", "currency")


def export_orders_csv(rows, *, include_header=True):
    """Return orders as CSV text.

    rows: iterable of dicts with id, amount (number) and currency (3-letter code).
    Raises ExportError naming the row index and missing field.
    """
    if rows is None:
        raise ExportError("export_orders_csv: rows is required, got None")
    buf = io.StringIO()
    writer = csv.writer(buf)
    if include_header:
        writer.writerow(REQUIRED)
    for i, row in enumerate(rows):
        missing = [k for k in REQUIRED if k not in row]
        if missing:
            raise ExportError(f"export_orders_csv: row {i} missing {missing}")
        writer.writerow([row["id"], f"{row['amount']:.2f}", row["currency"].upper()])
    return buf.getvalue()
''', "errors.py": 'class ExportError(ValueError):\n    """Raised when an export input is invalid."""\n'}
R1 = ("The warehouse team needs the same order export as tab-separated text "
      "(same fields, validation and formatting), for their label printer import.")

S2 = {"charges.py": '''"""Order charges computed at checkout."""
from decimal import Decimal, ROUND_HALF_UP

from errors import OrderError

CENT = Decimal("0.01")


def shipping_cost(order):
    """Return the shipping charge for an order as a Decimal.

    $0.50 per kg of line weight (weight_kg x qty), minimum $5.00; free when the
    merchandise subtotal (price x qty) is $100.00 or more.
    Raises OrderError when order has no lines or a line lacks a field.
    """
    lines = order.get("lines") if order else None
    if not lines:
        raise OrderError("shipping_cost: order has no lines")
    weight = Decimal(0)
    subtotal = Decimal(0)
    for i, line in enumerate(lines):
        for key in ("price", "qty", "weight_kg"):
            if key not in line:
                raise OrderError(f"shipping_cost: line {i} missing {key}")
        weight += Decimal(str(line["weight_kg"])) * line["qty"]
        subtotal += Decimal(str(line["price"])) * line["qty"]
    if subtotal >= 100:
        return Decimal("0.00")
    return max(Decimal("5.00"), (weight * Decimal("0.50"))).quantize(CENT, ROUND_HALF_UP)
''', "errors.py": 'class OrderError(ValueError):\n    """Raised when an order is invalid."""\n'}
R2 = ("Checkout now needs sales tax: 8.25% of price x qty summed over taxable lines "
      "(a line with taxable=False is exempt; taxable defaults to True), rounded half-up to cents.")

def prompt(files, request, rubric):
    body = "\n\n".join(f"### {name}\n```python\n{src}```" for name, src in files.items())
    return f"""You are the implement step of a ShipLoop work item. Make the requested change to this repository.

Request: {request}

Repository files:

{body}

Apply this rubric:

{rubric}
Return every file you change or create as a complete file in a fenced block whose first line is `# file: <name>`. Then write one short paragraph on your design decision. Do not use tools."""

out = pathlib.Path("prompts"); out.mkdir(exist_ok=True)
for sname, files, req in (("S1", S1, R1), ("S2", S2, R2)):
    for vname, rub in (("A", A), ("B", B)):
        (out / f"{sname}-{vname}.txt").write_text(prompt(files, req, rub))
print(sorted(x.name for x in out.iterdir()))
