#!/usr/bin/env python3
"""Builds the illustrated explainer of what the spec-elaboration work learned (2026-11-20/21).

Every figure on the page is taken from docs/spec-elaboration-journal.md (and, where marked, from the Ratchet
session's docs/ratchet-pilot-journal.md), as verified in the session that wrote this. Charts are drawn here from
the numbers, to one scale each.
"""

from html import escape
from pathlib import Path

OUT = Path(__file__).with_name("spec-lessons.html")


def e(text):
    return escape(str(text), quote=True)


def bar_path(x0, x1, y, h, r=4.0):
    """A horizontal bar from the baseline x0 to the data end x1, rounded only at the data end."""
    if abs(x1 - x0) < 0.5:
        return ""
    r = min(r, abs(x1 - x0), h / 2)
    if x1 > x0:
        return (
            f"M{x0:.1f},{y:.1f} H{x1 - r:.1f} Q{x1:.1f},{y:.1f} {x1:.1f},{y + r:.1f} V{y + h - r:.1f} "
            f"Q{x1:.1f},{y + h:.1f} {x1 - r:.1f},{y + h:.1f} H{x0:.1f} Z"
        )
    return (
        f"M{x0:.1f},{y:.1f} H{x1 + r:.1f} Q{x1:.1f},{y:.1f} {x1:.1f},{y + r:.1f} V{y + h - r:.1f} "
        f"Q{x1:.1f},{y + h:.1f} {x1 + r:.1f},{y + h:.1f} H{x0:.1f} Z"
    )


def tipattrs(text):
    return f'tabindex="0" role="img" aria-label="{e(text)}" data-tip="{e(text)}"'


# ---------------------------------------------------------------- figure 1: where each thread looked
def fig_pipeline():
    nodes = [
        ("Request", "one sentence"),
        ("Spec", "requirements"),
        ("Plan", "how to build"),
        ("Build", "the product"),
        ("Tests", "the suite"),
        ("Report", "what was done"),
    ]
    w, gap, x0, y0, h = 100, 18, 20, 18, 50
    xs = [x0 + i * (w + gap) for i in range(len(nodes))]
    out = [
        (
            '<svg viewBox="0 0 720 286" class="diagram" aria-labelledby="f1t"><title id="f1t">The delivery pipeline '
            "and the part each thread measured</title>"
        ),
        (
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="f-muted"/></marker></defs>'
        ),
    ]
    for i, (name, sub) in enumerate(nodes):
        x = xs[i]
        out.append(
            f'<rect x="{x}" y="{y0}" width="{w}" height="{h}" rx="8" class="node"/>'
        )
        out.append(
            f'<text x="{x + w / 2}" y="{y0 + 22}" class="t-node" text-anchor="middle">{name}</text>'
        )
        out.append(
            f'<text x="{x + w / 2}" y="{y0 + 39}" class="t-sub" text-anchor="middle">{sub}</text>'
        )
        if i:
            out.append(
                f'<line x1="{xs[i - 1] + w + 2}" y1="{y0 + h / 2}" x2="{x - 3}" y2="{y0 + h / 2}" '
                'class="s-muted" marker-end="url(#arrow)"/>'
            )
    bands = [
        (
            0,
            1,
            "Thread 1 · the bench",
            "the spec stage alone, marked against a hidden checklist",
            "s1",
        ),
        (
            0,
            5,
            "Thread 2 · real deliveries",
            "31 finished ShipLoop runs, read afterwards with no model",
            "ink",
        ),
        (
            1,
            4,
            "Threads 3 and 4 · the Ratchet session",
            "built products, graded by held-out checks and a correct reference",
            "s3",
        ),
        (
            0,
            5,
            "Thread 5 · qualification",
            "two whole deliveries of a ShipLoop text fix",
            "ink",
        ),
    ]
    y = 100
    for a, b, label, desc, tone in bands:
        xa, xb = xs[a] + 4, xs[b] + w - 4
        out.append(
            f'<path d="M{xa},{y - 8} V{y} H{xb} V{y - 8}" class="bracket b-{tone}"/>'
        )
        out.append(f'<text x="{xa}" y="{y + 19}" class="t-band">{e(label)}</text>')
        out.append(f'<text x="{xa}" y="{y + 36}" class="t-sub">{e(desc)}</text>')
        y += 47
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------- figure 2: the bench's targeted cues
BENCH = [
    # arm, label, verdict, panel, (sonnet registered, sol registered), (sonnet second, sol second)
    (
        "M",
        "M · leave an unresolved limit open",
        "nothing shown",
        0,
        (0.5, 0.5),
        (0.0, 1.0),
    ),
    (
        "K",
        "K · take a default, record it",
        "shown, with limits nobody asked for",
        0,
        (3.0, 5.5),
        (3.0, 6.5),
    ),
    (
        "G",
        "G · the review's seven sentences",
        "nothing shown; worse on Sol overall",
        1,
        (0.0, -1.5),
        (0.0, -1.5),
    ),
    (
        "H",
        "H · G without “keep it open”",
        "shown on Sol, interim on Sonnet",
        1,
        (1.0, 2.0),
        (1.0, 3.0),
    ),
]


def fig_bench():
    lo, hi = -2.0, 6.0
    px0, px1 = 238, 668
    sc = (px1 - px0) / (hi - lo)

    def x(v):
        return px0 + (v - lo) * sc

    out = [
        (
            '<svg viewBox="0 0 690 330" class="chart" aria-labelledby="f2t"><title id="f2t">Gain over the released '
            "spec text in checklist items, rounds 7 to 10</title>"
        )
    ]
    top, bottom = 24, 298
    for t in range(-2, 7, 2):
        cls = "s-axis" if t == 0 else "s-grid"
        out.append(
            f'<line x1="{x(t):.1f}" y1="{top}" x2="{x(t):.1f}" y2="{bottom}" class="{cls}"/>'
        )
        label = f"+{t}" if t > 0 else str(t)
        out.append(
            f'<text x="{x(t):.1f}" y="{bottom + 18}" class="t-tick" text-anchor="middle">{label}</text>'
        )
    out.append(
        f'<line x1="{x(2):.1f}" y1="{top}" x2="{x(2):.1f}" y2="{bottom}" class="s-band"/>'
    )
    out.append(
        f'<text x="{x(2) + 5:.1f}" y="{top + 10}" class="t-tick">band: 2 items</text>'
    )
    panels = [
        "Rounds 7 and 8 · 22 target items (sets and limits)",
        "Rounds 9 and 10 · 6 limits a correct product needs",
    ]
    y = top + 4
    current = -1
    for arm, label, verdict, panel, reg, second in BENCH:
        if panel != current:
            current = panel
            if panel:
                y += 12
            out.append(
                f'<text x="0" y="{y + 12}" class="t-panel">{e(panels[panel])}</text>'
            )
            y += 26
        out.append(f'<text x="0" y="{y + 13}" class="t-row">{e(label)}</text>')
        out.append(f'<text x="0" y="{y + 30}" class="t-sub">{e(verdict)}</text>')
        for i, (driver, cls) in enumerate((("Sonnet", "f-s1"), ("Sol", "f-s2"))):
            v = reg[i]
            by = y + 2 + i * 17
            tip = (
                f"{arm}, {driver}: {v:+.1f} items over the released text under the registered judge (Opus); "
                f"{second[i]:+.1f} under the second judge (Astra). Mean of two rounds."
            )
            path = bar_path(x(0), x(v), by, 13)
            mark = f'<path d="{path}" class="{cls}"/>' if path else ""
            out.append(
                f'<g {tipattrs(tip)} class="hit"><rect x="{min(x(0), x(v)) - 2:.1f}" y="{by - 2}" '
                f'width="{abs(x(v) - x(0)) + 4:.1f}" height="17" class="hitbox"/>{mark}</g>'
            )
            if v > 0:
                out.append(
                    f'<text x="{x(v) + 6:.1f}" y="{by + 11}" class="t-val">{v:+.1f}</text>'
                )
            elif v < 0:
                out.append(
                    f'<text x="{x(v) - 6:.1f}" y="{by + 11}" class="t-val" text-anchor="end">{v:+.1f}</text>'
                )
            else:
                out.append(
                    f'<text x="{x(0) + 6:.1f}" y="{by + 11}" class="t-val">0</text>'
                )
        y += 48
    out.append("</svg>")
    return "".join(out)


def table_bench():
    rows = "".join(
        f"<tr><th scope='row'>{e(label)}</th><td>{reg[0]:+.1f}</td><td>{second[0]:+.1f}</td><td>{reg[1]:+.1f}</td>"
        f"<td>{second[1]:+.1f}</td></tr>"
        for _, label, _, _, reg, second in BENCH
    )
    return (
        "<table><thead><tr><th>Cue</th><th>Sonnet, Opus</th><th>Sonnet, Astra</th><th>Sol, Opus</th>"
        f"<th>Sol, Astra</th></tr></thead><tbody>{rows}</tbody></table>"
    )


# ---------------------------------------------------------------- figure 3: words at the spec stage
WORDS = [
    (
        "Sol · real runs",
        "f-s2",
        120,
        731,
        384,
        "26 real specifications: median 384 words, 120 to 731",
    ),
    (
        "Sol · the bench",
        "f-s2 faint",
        4400,
        6600,
        None,
        "rounds 5 to 10 on the bench: 4,400 to 6,600 words",
    ),
    (
        "Sonnet · real runs",
        "f-s1",
        1718,
        2288,
        2207,
        "5 real specifications: median 2,207 words, 1,718 to 2,288",
    ),
    (
        "Sonnet · the bench",
        "f-s1 faint",
        6000,
        10000,
        None,
        "rounds 5 to 10 on the bench: 6,000 to 10,000 words",
    ),
]


def fig_words():
    px0, px1, hi = 150, 670, 10000
    sc = (px1 - px0) / hi

    def x(v):
        return px0 + v * sc

    out = [
        (
            '<svg viewBox="0 0 690 236" class="chart" aria-labelledby="f3t"><title id="f3t">Words in the '
            "specification at the spec stage, real runs against the bench</title>"
        )
    ]
    top, bottom = 8, 206
    for t in range(0, 10001, 2000):
        out.append(
            f'<line x1="{x(t):.1f}" y1="{top}" x2="{x(t):.1f}" y2="{bottom}" class="{"s-axis" if t == 0 else "s-grid"}"/>'
        )
        out.append(
            f'<text x="{x(t):.1f}" y="{bottom + 18}" class="t-tick" text-anchor="middle">'
            f"{'0' if t == 0 else f'{t // 1000}K'}</text>"
        )
    y = 22
    for label, cls, a, b, med, tip in WORDS:
        out.append(f'<text x="0" y="{y + 12}" class="t-row">{e(label)}</text>')
        xa, xb = x(a), x(b)
        out.append(
            f'<g {tipattrs(tip)} class="hit"><rect x="{xa - 4:.1f}" y="{y - 4}" width="{xb - xa + 8:.1f}" '
            f'height="18" class="hitbox"/><rect x="{xa:.1f}" y="{y + 1}" width="{max(xb - xa, 6):.1f}" '
            f'height="10" rx="5" class="{cls}"/>'
        )
        if med is not None:
            out.append(
                f'<circle cx="{x(med):.1f}" cy="{y + 6}" r="5.5" class="{cls.split()[0]} ring"/>'
            )
        out.append("</g>")
        text = (
            f"median {med:,} · {a:,} to {b:,}" if med is not None else f"{a:,} to {b:,}"
        )
        anchor_x = xb + 8 if xb < 560 else xa - 8
        anchor = "start" if xb < 560 else "end"
        out.append(
            f'<text x="{anchor_x:.1f}" y="{y + 10}" class="t-val" text-anchor="{anchor}">{text}</text>'
        )
        y += 46
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------- figure 4: the due-times ceiling
def fig_ceiling():
    sonnet = ["100,000 hours", "87,600 hours", "8,760 hours", "8,760 hours"]
    out = [
        (
            '<svg viewBox="0 0 690 118" class="chart" aria-labelledby="f4t"><title id="f4t">Sixteen due-times '
            "builds: all enforce a ceiling on hours; only Sonnet writes it down</title>"
        )
    ]
    out.append('<text x="0" y="16" class="t-panel">Sonnet · 4 builds</text>')
    out.append('<text x="176" y="16" class="t-panel">Sol · 12 builds</text>')
    for i, ceiling in enumerate(sonnet):
        cx = 14 + i * 34
        tip = f"Sonnet build {i + 1}: ceiling {ceiling}, stated in the spec and in the final report"
        out.append(
            f'<g {tipattrs(tip)} class="hit"><circle cx="{cx}" cy="46" r="15" class="hitbox"/>'
            f'<circle cx="{cx}" cy="46" r="11" class="f-s1"/></g>'
        )
    for i in range(12):
        cx = 190 + i * 34
        tip = (
            f"Sol build {i + 1}: enforces a ceiling (somewhere from 1,000,000 hours up to the largest date "
            "JavaScript can hold) that appears in neither the spec nor the final report"
        )
        out.append(
            f'<g {tipattrs(tip)} class="hit"><circle cx="{cx}" cy="46" r="15" class="hitbox"/>'
            f'<circle cx="{cx}" cy="46" r="10" class="hollow-s2"/></g>'
        )
    out.append(
        '<circle cx="8" cy="94" r="6" class="f-ink"/><text x="20" y="98" class="t-sub">enforced, and '
        "written in the spec and the final report</text>"
    )
    out.append(
        '<circle cx="330" cy="94" r="5.5" class="hollow-ink"/><text x="342" y="98" class="t-sub">enforced, '
        "written nowhere</text>"
    )
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------- figure 5: built products, three texts
TEXTS = [("Reworded (R)", True), ("Lens text (L)", False), ("Pilot's own", False)]
CLAUSES = [102, 426, 499]
FAILING = [(8, 102, 7.8), (47, 426, 11.0), (59, 499, 11.8)]
FIRST_BUILD = [[8, 8], [3, 2], [3]]


def fig_ratchet():
    out = [
        (
            '<svg viewBox="0 0 720 212" class="chart" aria-labelledby="f5t"><title id="f5t">Three specification '
            "texts measured through built products</title>"
        )
    ]
    panels = [
        (120, 300, "Clauses written: over three cases", 500),
        (330, 510, "Failing on a: correct product", 15),
        (540, 712, "First due-times build: held-out checks of 8", 8),
    ]
    top = 42
    rows_y = [top + 16, top + 64, top + 112]
    for (label, strong), ry in zip(TEXTS, rows_y):
        out.append(
            f'<text x="0" y="{ry + 11}" class="t-row{" strong" if strong else ""}">{e(label)}</text>'
        )
    for pi, (a, b, title, hi) in enumerate(panels):
        out.append(
            f'<text x="{a}" y="14" class="t-panel">{e(title.split(":")[0])}</text>'
        )
        if ":" in title:
            out.append(
                f'<text x="{a}" y="30" class="t-sub">{e(title.split(": ")[1])}</text>'
            )
        sc = (b - a) / hi
        out.append(
            f'<line x1="{a}" y1="{top + 4}" x2="{a}" y2="{top + 140}" class="s-axis"/>'
        )
        ticks = {0: [0, 250, 500], 1: [0, 5, 10, 15], 2: [0, 4, 8]}[pi]
        for t in ticks[1:]:
            out.append(
                f'<line x1="{a + t * sc:.1f}" y1="{top + 4}" x2="{a + t * sc:.1f}" y2="{top + 140}" class="s-grid"/>'
            )
        for t in ticks:
            lab = f"{t}%" if pi == 1 else f"{t}"
            out.append(
                f'<text x="{a + t * sc:.1f}" y="{top + 156}" class="t-tick" text-anchor="middle">{lab}</text>'
            )
        for ri, ((name, strong), ry) in enumerate(zip(TEXTS, rows_y)):
            cls = "f-s3" if strong else "f-neutral"
            if pi == 0:
                v = CLAUSES[ri]
                tip = f"{name}: {v} clauses written over the three cases"
                out.append(
                    f'<g {tipattrs(tip)} class="hit"><path d="{bar_path(a, a + v * sc, ry, 16)}" class="{cls}"/></g>'
                )
                out.append(
                    f'<text x="{a + v * sc + 6:.1f}" y="{ry + 12}" class="t-val">{v}</text>'
                )
            elif pi == 1:
                n, d, pct = FAILING[ri]
                tip = f"{name}: {n} of {d} clauses fail on the correct reference product ({pct}%)"
                out.append(
                    f'<g {tipattrs(tip)} class="hit"><path d="{bar_path(a, a + pct * sc, ry, 16)}" class="{cls}"/></g>'
                )
                out.append(
                    f'<text x="{a + pct * sc + 6:.1f}" y="{ry + 12}" class="t-val">{pct}%</text>'
                )
            else:
                vals = FIRST_BUILD[ri]
                for k, v in enumerate(vals):
                    cy = ry + 8 + (k - (len(vals) - 1) / 2) * 12
                    tip = f"{name}, build {k + 1}: {v} of 8 held-out checks passed at its first build"
                    out.append(
                        f'<g {tipattrs(tip)} class="hit"><circle cx="{a + v * sc:.1f}" cy="{cy:.1f}" r="9" '
                        f'class="hitbox"/><circle cx="{a + v * sc:.1f}" cy="{cy:.1f}" r="5" class="{cls} ring"/></g>'
                    )
                text = " and ".join(str(v) for v in vals) + " of 8"
                lx = a + max(vals) * sc
                if max(vals) >= 7:
                    out.append(
                        f'<text x="{lx - 12:.1f}" y="{ry + 12}" class="t-val" text-anchor="end">{text}</text>'
                    )
                else:
                    out.append(
                        f'<text x="{lx + 12:.1f}" y="{ry + 12}" class="t-val">{text}</text>'
                    )
    out.append("</svg>")
    return "".join(out)


def table_ratchet():
    rows = "".join(
        f"<tr><th scope='row'>{e(name)}</th><td>{CLAUSES[i]}</td><td>{FAILING[i][0]} of {FAILING[i][1]} "
        f"({FAILING[i][2]}%)</td><td>{' and '.join(map(str, FIRST_BUILD[i]))} of 8</td><td>{d}</td></tr>"
        for i, ((name, _), d) in enumerate(
            zip(TEXTS, ["36 of 37", "36 of 37", "37 of 37"])
        )
    )
    return (
        "<table><thead><tr><th>Text</th><th>Clauses</th><th>Failing on a correct product</th>"
        f"<th>First due-times build</th><th>Planted defects caught</th></tr></thead><tbody>{rows}</tbody></table>"
    )


# ---------------------------------------------------------------- figure 6: where the answers live
def wrap_lines(x, y, lines, cls, step=15):
    return "".join(
        f'<text x="{x}" y="{y + i * step}" class="{cls}">{e(line)}</text>'
        for i, line in enumerate(lines)
    )


def fig_answers():
    out = [
        (
            '<svg viewBox="0 0 720 330" class="diagram" aria-labelledby="f6t"><title id="f6t">Open in the spec, '
            "answered in the plan, shared by the build and the tests</title>"
        ),
        (
            '<defs><marker id="arrow2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="f-muted"/></marker>'
            '<marker id="arrow3" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="f-bad"/></marker></defs>'
        ),
    ]
    # spec
    out.append('<rect x="4" y="16" width="228" height="164" rx="10" class="node"/>')
    out.append('<text x="18" y="40" class="t-node">Specification</text>')
    out.append(
        wrap_lines(
            18,
            62,
            [
                "C-6  Operators can configure",
                "the response hours for each",
                "priority without editing code.",
            ],
            "t-mono",
        )
    )
    out.append('<rect x="12" y="112" width="212" height="58" rx="6" class="open-box"/>')
    out.append(
        wrap_lines(
            20,
            130,
            [
                "Open: the requester decides",
                "the accepted range and",
                "precision for hours.",
            ],
            "t-mono open",
        )
    )
    # plan
    out.append('<rect x="262" y="16" width="208" height="164" rx="10" class="node"/>')
    out.append('<text x="276" y="40" class="t-node">Plan</text>')
    out.append(
        wrap_lines(
            276, 62, ["Default for this build:", "one setting per priority"], "t-small"
        )
    )
    out.append(
        wrap_lines(
            276,
            100,
            ["DUE_HOURS_URGENT", "DUE_HOURS_HIGH", "DUE_HOURS_NORMAL", "DUE_HOURS_LOW"],
            "t-mono strong",
        )
    )
    out.append(
        '<line x1="234" y1="98" x2="258" y2="98" class="s-muted" marker-end="url(#arrow2)"/>'
    )
    # build and tests
    out.append('<rect x="502" y="16" width="214" height="62" rx="10" class="node"/>')
    out.append('<text x="516" y="40" class="t-node">Build</text>')
    out.append('<text x="516" y="60" class="t-small">reads the plan’s settings</text>')
    out.append('<rect x="502" y="100" width="214" height="80" rx="10" class="node"/>')
    out.append('<text x="516" y="124" class="t-node">Tests</text>')
    out.append(
        wrap_lines(
            516, 143, ["written from the plan, with", "no build present"], "t-small"
        )
    )
    out.append(
        '<line x1="472" y1="72" x2="498" y2="52" class="s-muted" marker-end="url(#arrow2)"/>'
    )
    out.append(
        '<line x1="472" y1="124" x2="498" y2="136" class="s-muted" marker-end="url(#arrow2)"/>'
    )
    # outcomes
    out.append(
        '<g class="ok-row"><circle cx="276" cy="226" r="9" class="f-good"/>'
        '<path d="M271.5,226 l3,3 l6,-6.5" class="tick-mark"/>'
        '<text x="294" y="222" class="t-row">Pass on builds they never saw</text>'
        '<text x="294" y="240" class="t-sub">42 of 42 and 41 of 41: the builds took the same answers</text></g>'
    )
    out.append(
        '<g class="bad-row"><circle cx="276" cy="284" r="9" class="f-bad"/>'
        '<path d="M272,280 l8,8 M280,280 l-8,8" class="tick-mark"/>'
        '<text x="294" y="280" class="t-row">Fail on a correct product that chose differently</text>'
        '<text x="294" y="298" class="t-sub">it reads one RESPONSE_HOURS setting: the loops’ suites lose 10 to 12 items</text></g>'
    )
    out.append('<text x="262" y="204" class="t-panel">What the fork found</text>')
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------- figure 7: the overlay matrix
OVERLAY = [
    ("Loop a’s suite", 42, [41, 39, 30]),
    ("Loop b’s suite", 41, [41, 41, 31]),
    ("Test-strength cell’s suite", 39, [32, 32, 35]),
]


def table_overlay():
    head = (
        "<thead><tr><th scope='col'>Suite</th><th scope='col'>On loop a’s build</th>"
        "<th scope='col'>On loop b’s build</th><th scope='col'>On the correct reference</th></tr></thead>"
    )
    rows = []
    for name, n, vals in OVERLAY:
        cells = []
        for v in vals:
            share = v / n
            mix = max(0, min(72, round((share - 0.6) / 0.4 * 72)))
            cells.append(
                f"<td class='heat' style='--mix:{mix}%'><b>{v}</b> of {n}</td>"
            )
        rows.append(f"<tr><th scope='row'>{e(name)}</th>{''.join(cells)}</tr>")
    return f"<table class='matrix'>{head}<tbody>{''.join(rows)}</tbody></table>"


# ---------------------------------------------------------------- figure 8: how processes were stopped
STOPS = [
    ("Chose the process by name or pattern", 3, 0),
    ("Stopped it by an id it had recorded", 1, 4),
]


def fig_stops():
    px0, px1, hi = 272, 640, 5
    sc = (px1 - px0) / hi
    out = [
        (
            '<svg viewBox="0 0 690 170" class="chart" aria-labelledby="f8t"><title id="f8t">How the Sonnet '
            "delivery of the shared-expenses case stopped processes, before and with the new rule</title>"
        )
    ]
    top, bottom = 6, 140
    for t in range(6):
        out.append(
            f'<line x1="{px0 + t * sc:.1f}" y1="{top}" x2="{px0 + t * sc:.1f}" y2="{bottom}" '
            f'class="{"s-axis" if t == 0 else "s-grid"}"/>'
        )
        out.append(
            f'<text x="{px0 + t * sc:.1f}" y="{bottom + 18}" class="t-tick" text-anchor="middle">{t}</text>'
        )
    y = 18
    for label, before, after in STOPS:
        out.append(f'<text x="0" y="{y + 20}" class="t-row">{e(label)}</text>')
        for k, (v, cls, who) in enumerate(
            (
                (before, "f-neutral", "20 November run, text without the rule"),
                (after, "f-s1", "21 November run, with the rule"),
            )
        ):
            by = y + k * 19
            tip = f"{who}: {v} {'command' if v == 1 else 'commands'} ({label.lower()})"
            path = bar_path(px0, px0 + v * sc, by, 15)
            mark = f'<path d="{path}" class="{cls}"/>' if path else ""
            out.append(
                f'<g {tipattrs(tip)} class="hit"><rect x="{px0 - 2}" y="{by - 2}" width="{max(v * sc, 10) + 4:.1f}" '
                f'height="19" class="hitbox"/>{mark}</g>'
            )
            out.append(
                f'<text x="{px0 + v * sc + 7:.1f}" y="{by + 12}" class="t-val">{v}</text>'
            )
        y += 64
    out.append("</svg>")
    return "".join(out)


CSS = r"""
/* Layout: one reading column, figures at the column's width, each thread opened by a numbered marker in order of discovery. */
:root{
  --bg:#f4f6f9; --surface:#ffffff; --ink:#141922; --ink-2:#424c5c; --muted:#6c7586; --rule:#dce1e8;
  --grid:#e5e8ed; --axis:#bcc3ce; --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --neutral:#a2a9b5;
  --open-bg:#fff1bf; --open-line:#e9b300; --open-ink:#4d3a00; --good:#0ca30c; --bad:#d03b3b;
  --seq:#2a78d6; --code-bg:#edf0f5; --tip-bg:#141922; --tip-ink:#f4f6f9;
  --display:"Space Grotesk",ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
  --body:"Inter",ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"JetBrains Mono",ui-monospace,"SF Mono",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#0e1116; --surface:#161a21; --ink:#e9ecf1; --ink-2:#b6bdc9; --muted:#8891a1; --rule:#272c35;
  --grid:#232831; --axis:#3a404b; --s1:#3987e5; --s2:#d95926; --s3:#199e70; --neutral:#5d6573;
  --open-bg:rgba(250,178,25,.16); --open-line:#c98500; --open-ink:#f3d27a; --good:#0ca30c; --bad:#e66767;
  --seq:#3987e5; --code-bg:#1e232b; --tip-bg:#e9ecf1; --tip-ink:#0e1116; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#0e1116; --surface:#161a21; --ink:#e9ecf1; --ink-2:#b6bdc9; --muted:#8891a1; --rule:#272c35;
  --grid:#232831; --axis:#3a404b; --s1:#3987e5; --s2:#d95926; --s3:#199e70; --neutral:#5d6573;
  --open-bg:rgba(250,178,25,.16); --open-line:#c98500; --open-ink:#f3d27a; --good:#0ca30c; --bad:#e66767;
  --seq:#3987e5; --code-bg:#1e232b; --tip-bg:#e9ecf1; --tip-ink:#0e1116; color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font:16px/1.62 var(--body);-webkit-font-smoothing:antialiased;
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:0}
main{max-width:780px;margin:0 auto;padding-block:48px 72px}
h1,h2,h3{font-family:var(--display);text-wrap:balance;line-height:1.15;margin:0}
h1{font-size:clamp(2.1rem,5.4vw,3.2rem);font-weight:600;letter-spacing:-.02em}
h2{font-size:clamp(1.45rem,3.4vw,1.85rem);font-weight:600;letter-spacing:-.01em}
h3{font-size:1.08rem;font-weight:600}
p{margin:0}
.eyebrow{font:600 .74rem/1.3 var(--body);letter-spacing:.09em;text-transform:uppercase;color:var(--muted)}
.lede{font-size:1.14rem;color:var(--ink-2);max-width:62ch}
.stack{display:flex;flex-direction:column;gap:18px}
.stack-lg{display:flex;flex-direction:column;gap:30px}
header.top{display:flex;flex-direction:column;gap:18px;padding-bottom:34px;border-bottom:1px solid var(--rule)}
.meta{font-size:.86rem;color:var(--muted)}
code,.mono{font-family:var(--mono);font-size:.88em;background:var(--code-bg);padding:.1em .35em;border-radius:4px}
.open-tag{font-family:var(--mono);font-size:.88em;background:var(--open-bg);color:var(--open-ink);padding:.1em .35em;border-radius:4px}
.minute{background:var(--surface);border:1px solid var(--rule);border-radius:14px;padding:24px 26px}
.minute ul{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:14px}
.minute li{display:grid;grid-template-columns:22px 1fr;gap:10px}
.minute li::before{content:"";width:9px;height:9px;border-radius:50%;background:var(--ink-2);margin-top:.55em}
.minute li>div{min-width:0}
section.thread{display:flex;flex-direction:column;gap:20px;padding-top:44px;margin-top:8px;border-top:1px solid var(--rule)}
.thread-head{display:grid;grid-template-columns:auto 1fr;gap:16px;align-items:start}
.num{font:600 1.05rem/1 var(--display);width:38px;height:38px;border-radius:50%;display:grid;place-items:center;
  border:1.5px solid var(--ink);color:var(--ink);margin-top:2px}
.thread-head>div{display:flex;flex-direction:column;gap:6px;min-width:0}
figure{margin:0;display:flex;flex-direction:column;gap:10px}
.stack-lg>*,.stack>*,section.thread>*,figure>*,header.top>*,main>*{min-width:0}
p code,li code,figcaption code,.meta code{overflow-wrap:anywhere}
.fig-box{background:var(--surface);border:1px solid var(--rule);border-radius:12px;padding:18px 18px 14px;overflow-x:auto}
.fig-box svg{display:block;width:100%;height:auto;min-width:560px}
figcaption{font-size:.88rem;color:var(--muted);max-width:68ch}
figcaption b{color:var(--ink-2);font-weight:600}
.legend{display:flex;flex-wrap:wrap;gap:16px;font-size:.84rem;color:var(--ink-2);margin-bottom:8px}
.legend span{display:inline-flex;align-items:center;gap:7px}
.sw{width:12px;height:12px;border-radius:3px;display:inline-block}
.sw.s1{background:var(--s1)}.sw.s2{background:var(--s2)}.sw.s3{background:var(--s3)}.sw.neutral{background:var(--neutral)}
.timeline{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:0}
.timeline li{display:grid;grid-template-columns:104px 1fr;gap:14px;padding:12px 0;border-top:1px solid var(--rule)}
.timeline li:first-child{border-top:0}
.timeline .when{font:600 .82rem/1.5 var(--display);color:var(--ink-2);padding-top:2px}
.timeline li>div{min-width:0}
.note{border-left:3px solid var(--open-line);background:var(--surface);padding:16px 18px;border-radius:0 10px 10px 0}
.note h3{margin-bottom:6px}
.verdict{display:flex;gap:14px;align-items:flex-start;background:var(--surface);border:1px solid var(--rule);border-radius:12px;padding:18px 20px}
.verdict .pill{font:600 .78rem/1 var(--body);letter-spacing:.05em;text-transform:uppercase;padding:7px 10px;border-radius:999px;
  border:1.5px solid currentColor;white-space:nowrap;color:var(--ink)}
.verdict>div{min-width:0}
.clause{font-family:var(--mono);font-size:.84rem;line-height:1.55;background:var(--surface);border:1px solid var(--rule);
  border-radius:10px;padding:16px 18px;display:flex;flex-direction:column;gap:6px;overflow-x:auto}
.clause .id{font-weight:700}
.clause .k{color:var(--muted)}
.clause .open-line{background:var(--open-bg);color:var(--open-ink);margin:2px -10px 0;padding:6px 10px;border-radius:6px;
  border-left:3px solid var(--open-line)}
table{border-collapse:collapse;width:100%;font-size:.88rem;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--rule);vertical-align:top}
thead th{font-weight:600;color:var(--muted);font-size:.78rem;letter-spacing:.04em;text-transform:uppercase}
.table-wrap{overflow-x:auto;background:var(--surface);border:1px solid var(--rule);border-radius:12px;padding:6px 14px}
.matrix td.heat{background:color-mix(in oklab,var(--seq) var(--mix),var(--surface));text-align:center}
.matrix td.heat b{font-weight:700}
.matrix th[scope=col]{text-align:center}
.matrix th[scope=col]:first-child{text-align:left}
.ok{color:var(--good);font-weight:700}
details.data{font-size:.86rem;color:var(--ink-2)}
details.data summary{cursor:pointer;color:var(--muted);width:max-content}
details.data summary:focus-visible{outline:2px solid var(--s1);outline-offset:2px;border-radius:4px}
details.data .table-wrap{margin-top:8px}
.lessons{counter-reset:l;list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.lessons li{counter-increment:l;background:var(--surface);border:1px solid var(--rule);border-radius:12px;padding:16px 18px;
  display:flex;flex-direction:column;gap:6px;min-width:0}
.lessons li::before{content:counter(l);font:600 .8rem/1 var(--display);color:var(--muted)}
.lessons b{font-family:var(--display);font-weight:600;font-size:1rem;line-height:1.3}
.open-list{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:12px}
.open-list li{display:grid;grid-template-columns:16px 1fr;gap:10px}
.open-list li::before{content:"";width:10px;height:10px;border:2px solid var(--muted);border-radius:3px;margin-top:.45em}
.open-list li>div{min-width:0}
dl.gloss{display:grid;grid-template-columns:minmax(120px,190px) 1fr;gap:10px 18px;margin:0}
dl.gloss dt{font-weight:600}
dl.gloss dd{margin:0;color:var(--ink-2);min-width:0}
footer{margin-top:56px;padding-top:22px;border-top:1px solid var(--rule);font-size:.84rem;color:var(--muted);display:flex;flex-direction:column;gap:8px}
a{color:var(--s1)}
/* svg */
.node{fill:var(--surface);stroke:var(--axis);stroke-width:1.2}
.open-box{fill:var(--open-bg);stroke:var(--open-line);stroke-width:1}
.bracket{fill:none;stroke-width:1.6}
.b-s1{stroke:var(--s1)}.b-s3{stroke:var(--s3)}.b-ink{stroke:var(--ink-2)}
.s-muted{stroke:var(--muted);stroke-width:1.4;fill:none}
.s-grid{stroke:var(--grid);stroke-width:1}
.s-axis{stroke:var(--axis);stroke-width:1}
.s-band{stroke:var(--muted);stroke-width:1.2}
.f-muted{fill:var(--muted)}.f-bad{fill:var(--bad)}.f-good{fill:var(--good)}.f-ink{fill:var(--ink-2)}
.f-s1{fill:var(--s1)}.f-s2{fill:var(--s2)}.f-s3{fill:var(--s3)}.f-neutral{fill:var(--neutral)}
.faint{fill-opacity:.38}
.ring{stroke:var(--surface);stroke-width:2;fill-opacity:1}
.hollow-s2{fill:var(--surface);stroke:var(--s2);stroke-width:2.5}
.hollow-ink{fill:var(--surface);stroke:var(--ink-2);stroke-width:2}
.tick-mark{fill:none;stroke:#fff;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.hitbox{fill:transparent}
.hit{cursor:default;outline:none}
.hit:focus-visible .hitbox{stroke:var(--s1);stroke-width:2}
svg text{font-family:var(--body)}
.t-node{font:600 15px var(--display);fill:var(--ink)}
.t-sub{font-size:11.5px;fill:var(--muted)}
.t-small{font-size:12px;fill:var(--ink-2)}
.t-band{font:600 12.5px var(--body);fill:var(--ink)}
.t-panel{font:600 12px var(--body);fill:var(--ink-2)}
.t-row{font-size:13px;fill:var(--ink)}
.t-row.strong{font-weight:700}
.t-val{font-size:12px;fill:var(--ink-2);font-variant-numeric:tabular-nums}
.t-tick{font-size:11px;fill:var(--muted);font-variant-numeric:tabular-nums}
.t-mono{font:11.5px var(--mono);fill:var(--ink)}
.t-mono.open{fill:var(--open-ink)}
.t-mono.strong{font-weight:700}
#tip{position:fixed;z-index:20;max-width:300px;background:var(--tip-bg);color:var(--tip-ink);font-size:.8rem;line-height:1.45;
  padding:8px 10px;border-radius:8px;pointer-events:none;box-shadow:0 6px 20px rgba(0,0,0,.18)}
@media (max-width:640px){
  .lessons{grid-template-columns:minmax(0,1fr)}
  .timeline li{grid-template-columns:minmax(0,1fr);gap:4px}
  dl.gloss{grid-template-columns:minmax(0,1fr);gap:2px}
  dl.gloss dd{margin-bottom:10px}
  .minute{padding:20px}
  .thread-head{gap:12px}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
"""

JS = r"""
(function(){
  var tip=document.getElementById('tip');
  function place(x,y){var w=tip.offsetWidth,h=tip.offsetHeight,vw=window.innerWidth,vh=window.innerHeight;
    var left=Math.min(Math.max(8,x+14),vw-w-8),top=y+16;if(top+h>vh-8){top=y-h-12}tip.style.left=left+'px';tip.style.top=Math.max(8,top)+'px'}
  function show(el,ev){tip.textContent=el.getAttribute('data-tip');tip.hidden=false;
    if(ev&&ev.clientX!==undefined){place(ev.clientX,ev.clientY)}else{var r=el.getBoundingClientRect();place(r.left+r.width/2,r.bottom)}}
  function hide(){tip.hidden=true}
  document.querySelectorAll('[data-tip]').forEach(function(el){
    el.addEventListener('pointerenter',function(ev){show(el,ev)});
    el.addEventListener('pointermove',function(ev){if(!tip.hidden)place(ev.clientX,ev.clientY)});
    el.addEventListener('pointerleave',hide);
    el.addEventListener('focus',function(){show(el)});
    el.addEventListener('blur',hide);
  });
  window.addEventListener('scroll',hide,{passive:true});
})();
"""


def page():
    return f"""<title>Spec Elaboration Lessons</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&family=Space+Grotesk:wght@500;600&display=swap">
<style>{CSS}</style>
<main>
<header class="top">
  <p class="eyebrow">ShipLoop · the spec stage · 20 and 21 November 2026</p>
  <h1>Mark the open points. Decide each one once.</h1>
  <p class="lede">You asked for a prompt that turns a one-sentence request into a full specification. Two days of
  experiments here, and results from two neighbouring sessions, changed our picture of what the specification stage
  needs. This page walks through what we learned, in the order we learned it.</p>
  <p class="meta">Sources: <code>docs/spec-elaboration-journal.md</code> (sections cited in each part) and the Ratchet
  session's <code>docs/ratchet-pilot-journal.md</code>, both on <code>main</code>. Hover or tab to any mark for its exact value.</p>
</header>

<div class="stack-lg" style="padding-top:34px">
<section class="minute" aria-labelledby="m1">
  <div class="stack">
  <h2 id="m1" style="font-size:1.2rem">In one minute</h2>
  <ul>
    <li><div><b>More elaboration did not hold up.</b> On a test bench, longer and more searching spec prompts covered
    more of a hidden checklist. The gains were mostly points the released text already touched, plus limits nobody
    asked for. ShipLoop's prompt was not changed.</div></li>
    <li><div><b>The bench and the real runs differ in three ways.</b> Bench specs were many times longer (11 to 17
    times on Sol). But the bench gave one sentence where real cases give a page, had no repository, and its sessions
    read ShipLoop's reference guides, which real builders almost never open. Real deliveries also showed a gap of
    their own: on Sol, builders pick limits and never write them down.</div></li>
    <li><div><b>Leaving a point open beat deciding it.</b> In the Ratchet session, a text that marks undecided points
    <span class="open-tag">Open:</span> wrote a quarter of the clauses, fewer of them failed on a correct product, and its
    first builds of the due-times case passed all 8 held-out checks where texts that decide had passed 2 or 3.</div></li>
    <li><div><b>The answers then belong in the plan.</b> Tests written from the plan passed on builds they had never
    seen. On a correct product that chose different answers, they lost 10 to 12 items.</div></li>
    <li><div><b>A ShipLoop text fix qualified.</b> The fix released as ShipLoop 2.4.1 passed checks that were written
    down before any result was read.</div></li>
  </ul>
  </div>
</section>

<figure>
  <div class="fig-box">{fig_pipeline()}</div>
  <figcaption><b>Figure 1.</b> Each thread measured a different part of the same pipeline. Only threads 3 to 5 looked
  at products that were actually built.</figcaption>
</figure>
</div>

<section class="thread" aria-labelledby="t1">
  <div class="thread-head"><span class="num" aria-hidden="true">1</span><div>
    <p class="eyebrow">Journal sections 1 to 28 · 20 and 21 November</p>
    <h2 id="t1">A test bench for the spec stage on its own</h2></div></div>
  <p>Each prompt text was given four one-sentence requests and wrote the specification alone, with no repository and
  nothing after it: <code>grokbot-salesforce</code> (your Grok bot in a Salesforce org), <code>gym-waitlist</code>,
  <code>invoice-reminders</code> and <code>csv-user-import</code>. Before any run this session wrote a hidden checklist
  of 89 points a good specification should cover, in ten categories (edge cases, unhappy paths, data, permissions,
  operators and more). Two judge models, Opus and Astra, marked every specification against it. The drivers were the
  ones you named: Sonnet at high effort and GPT 6.2 Sol at medium.</p>
  <ol class="timeline">
    <li><span class="when">Round 1</span><div>A six-pass recursive prompt beat a single pass: 72 against 46 of the 89
    points covered on Sonnet, 50 against 38 on Sol, at 2.6 to 4 times the minutes.</div></li>
    <li><span class="when">Round 4</span><div>A leak check found Codex showing your own installed skills, from the real
    home folder, to the Sol sessions (7 of 8 in that round). With them switched off, Sol's single pass fell from about
    39 to 29, so earlier Sol numbers had been lifted by the leak.</div></li>
    <li><span class="when">Round 5</span><div>One pass through five "lenses" did as well as iterating, at about half the
    minutes. And the released stage, run alone, already touched 80 to 87 of the 89 points under both judges. The
    elaborate prompts mostly turned "partly covered" into "covered".</div></li>
    <li><span class="when">Round 6</span><div>Adding the lens block to the released stage moved it a little, and not
    enough. An independent review said not to ship it; checking its claims showed it was right.</div></li>
    <li><span class="when">Rounds 7 to 10</span><div>One- or two-sentence cues added to the released text, scored only on
    checklist items sorted by two outside models (figure 2).</div></li>
  </ol>
  <p>Why the outside sort: a coverage count rewards a specification for deciding things, and your rule (27 September)
  is that product capability the request does not need is overbuilding. So two models that had written none of this
  sorted the 89 items. They marked 22 as target items about a set or a limit (6 of them limits a correct product
  cannot do without), and only 4 as capability nobody asked for.</p>
  <figure>
    <div class="fig-box">
      <div class="legend"><span><i class="sw s1"></i>Sonnet, high</span><span><i class="sw s2"></i>Sol, medium</span></div>
      {fig_bench()}
    </div>
    <figcaption><b>Figure 2.</b> Gain over the released spec text, in checklist items, mean of two rounds under the
    registered judge (Opus). To count as shown, a gain had to average at least the band of 2 items and be above zero in
    every round, under both judges.</figcaption>
    <details class="data"><summary>Numbers behind figure 2, both judges</summary><div class="table-wrap">{table_bench()}</div></details>
  </figure>
  <div class="note">
    <h3>What K's gain was made of</h3>
    <p>K told the stage to pick a default for any limit the request leaves to choice, and to record it. It did, and
    some of those limits nobody asked for: 3 of its 4 gym-waitlist specs capped the waitlist (at 10, 10 and 20 people),
    one added pausing reminders for a single invoice, and one assumed a cutoff 60 minutes before class. The released
    text had assumed no cap. H allowed a new limit only where the behaviour "cannot work correctly or safely without
    it", and none of its 4 waitlist specs capped the waitlist.</p>
  </div>
  <p><b>The lesson from the bench:</b> a count over a specification rewards deciding. It cannot tell rigour from
  capability nobody asked for, and it cannot tell whether a decision was the right one.</p>
</section>

<section class="thread" aria-labelledby="t2">
  <div class="thread-head"><span class="num" aria-hidden="true">2</span><div>
    <p class="eyebrow">Journal sections 26 and 38 · no model</p>
    <h2 id="t2">What 31 real deliveries show</h2></div></div>
  <p>Before concluding, this session read deliveries that had already run on the latest ShipLoop: 26 on Sol and 5 on
  Sonnet, across five cases. No model was called. Two things stood out.</p>
  <figure>
    <div class="fig-box">
      <div class="legend"><span><i class="sw s1"></i>Sonnet</span><span><i class="sw s2"></i>Sol</span><span>solid: real runs</span><span>faint: the bench</span></div>
      {fig_words()}
    </div>
    <figcaption><b>Figure 3.</b> Words in the specification at the spec stage, same stage text. On Sol the bench drew
    out 11 to 17 times the words of a real run, on Sonnet 3 to 4 times, so every bench number describes the bench's
    frame more than the real stage. Dots mark the median.</figcaption>
  </figure>
  <figure>
    <div class="fig-box">{fig_ceiling()}</div>
    <figcaption><b>Figure 4.</b> The due-times case asks for deadlines in hours. Every one of the 16 builds enforces a
    ceiling on the hours. Only Sonnet's 4 builds write that ceiling into the spec and the final report; Sol's 12
    write it nowhere.</figcaption>
  </figure>
  <p>The same pattern shows elsewhere. The one Sonnet expenses service caps a request at 1 MiB, answers 413 above
  it, and tests both sides of the line; none of the 10 Sol expenses services has a cap. A Sol chat app had nine limits
  its builder chose (64 KB requests, 80-character names, 8,000-character messages and more). None is in its spec,
  knowledge files or README, and no test sends a value that is too long.</p>
  <div class="note">
    <h3>Three differences, not one (added 21 November, late morning)</h3>
    <p>Figure 3 was first read as the bench distorting the stage. A second look found the two differ in three
    things at once. The bench's requests are 7 to 15 words; the real cases' are 76 to 322. The bench has no
    repository. And the reference guides, which state what a specification should consider, were read on the bench
    and are not read in real runs.</p>
  </div>
  <div class="table-wrap"><table>
    <thead><tr><th>Opened the requirements guide</th><th>Sessions</th></tr></thead>
    <tbody>
      <tr><th scope="row">Bench, guides beside the session</th><td>116 to 120 of 120</td></tr>
      <tr><th scope="row">Real deliveries, Sol</th><td>0 of 26</td></tr>
      <tr><th scope="row">Real deliveries, Sonnet</th><td>0 of 9</td></tr>
      <tr><th scope="row">Real delivery, Grok (opened all 39 guides)</th><td>1 of 1</td></tr>
    </tbody></table></div>
  <p>So your case, a vague one-sentence request, was only ever run on the bench, and there the released stage with
  its guides read touched at least 89% of every category of the checklist. In real runs the guides are named in
  every packet and left unopened, so today they cannot be doing much for the specification.</p>
  <div class="verdict"><span class="pill">Concluded</span><div><p><b>No template change</b> (07:16, 21 November, at your
  word). For detailed requests the released stage writes a short, complete specification. Whether it is full enough
  for a one-sentence request in a real run is not tested. One real difference between the drivers stands: on Sol,
  a limit nobody stated is chosen silently or not built.</p></div></div>
</section>

<section class="thread" aria-labelledby="t3">
  <div class="thread-head"><span class="num" aria-hidden="true">3</span><div>
    <p class="eyebrow">Journal sections 29 to 31 and 37 · results received from the Ratchet session</p>
    <h2 id="t3">A text that decides less did better on built products</h2></div></div>
  <p>The Ratchet session measures a specification through what gets built from it. A test suite is graded against a
  correct reference product, against 37 planted defects, and against held-out checks of the built product. Into its
  pipeline went a reworded text drafted here, arm R. R tells the writer to mark what the request leaves undecided as an
  <span class="open-tag">Open:</span> line instead of choosing, and tells the later stages that the build takes a
  reasonable answer and reports it. Here is a real clause written with it:</p>
  <div class="clause" aria-label="Clause C-6 from a due-times specification written with the reworded text">
    <span><span class="id">C-6:</span> Operators can configure the response hours for each priority without editing code.</span>
    <span><span class="k">Observable:</span> Set different hours for urgent, high, normal or low through the service's
    environment configuration. A ticket newly assigned a due time for that priority uses its configured number of
    hours. An unset or empty hours setting uses that priority's default.</span>
    <span><span class="k">Source:</span> request</span>
    <span class="open-line"><b>Open:</b> The requester decides the accepted range and precision for hours, including zero
    and fractional values. The configuration needs to support changing the stated defaults to usable response durations.</span>
  </div>
  <figure>
    <div class="fig-box">
      <div class="legend"><span><i class="sw s3"></i>Reworded text (R)</span><span><i class="sw neutral"></i>texts that decide every point</span></div>
      {fig_ratchet()}
    </div>
    <figcaption><b>Figure 5.</b> Three specification texts through built products, pooled over three cases (orders,
    ticket assignment, due times), on Codex with GPT 6.2 Sol at high, one run a cell. In the due-times case Sol's
    deciding texts chose, four times in five, to refuse starting on a data file without due times, which the request
    did not ask for.</figcaption>
    <details class="data"><summary>Numbers behind figure 5</summary><div class="table-wrap">{table_ratchet()}</div></details>
  </figure>
  <p>Planted defects caught were level: 36 of 37 for R and for the lens text, 37 of 37 for the pilot's own text. R
  missed one defect in existing behaviour that its shorter specification no longer pinned. With Sonnet as the writer,
  R did the same: 3 choice clauses in five specifications against 51, and 42 <span class="open-tag">Open:</span> lines.
  Sonnet never made the due-times mistake that R repaired on Sol, so that repair is a Sol result.</p>
  <p>At medium effort Sonnet wrote the same kind of specification with R (16 to 22 clauses against 21 to 32 at high),
  and tests built from it caught the same 26 of 27 planted defects, in 5.8 minutes and $1.37 against 14.2 minutes and
  $2.45. One count from these single runs looked like a price of brevity: five of those 26 catches came only from
  clauses that run the product's own existing test suite, against none for the lens text's 153 clauses on Sol. Three
  later runs of that same cell gave 5, 3 and 0, so the count is not shown to follow the specification's length. What
  stands is the one defect in existing behaviour that the short text's cells miss: anything that adopts it has to say
  where existing behaviour is pinned.</p>
</section>

<section class="thread" aria-labelledby="t4">
  <div class="thread-head"><span class="num" aria-hidden="true">4</span><div>
    <p class="eyebrow">Journal section 36 · the Ratchet session's fork · this morning</p>
    <h2 id="t4">Open in the spec, answered in the plan</h2></div></div>
  <p>If the spec leaves a point open, something still has to pick an answer before anything is built. In these runs
  the plan does: it lists a default for every open point, and the setting names that go with it. The Ratchet session's
  fork then laid each run's test suite over the other products, and had two new sessions write tests from the plan
  alone, with no build present.</p>
  <figure>
    <div class="fig-box">{fig_answers()}</div>
    <figcaption><b>Figure 6.</b> Clause C-6 again. The spec leaves the hours open; the plan fixes four settings; the
    build and the tests both read the plan. A correct product that chose one <code>RESPONSE_HOURS</code> setting
    instead fails tests that never assert an hours value, because they cannot start it the same way.</figcaption>
  </figure>
  <figure>
    <div class="table-wrap">{table_overlay()}</div>
    <figcaption><b>Figure 7.</b> Items passed when a suite is run on another product. Loops a and b are two due-times
    runs built from specifications written with R. Every cross failure is about how a test starts or configures the
    product at an open point, or about the product's own tests. None is about what a clause asserts.</figcaption>
  </figure>
  <p><b>The lesson:</b> no test asserted an answer to an open point, but every test still has to start and configure
  the product, and that is where the answer comes in. So the answers and the names a plan fixes need to be written
  down before the build, where tests are written from. Reporting them afterwards is too late for anything written
  separately. The evidence is thin: two sessions, one request, one model, and nobody has yet measured whether tests
  written this way catch planted defects.</p>
</section>

<section class="thread" aria-labelledby="t5">
  <div class="thread-head"><span class="num" aria-hidden="true">5</span><div>
    <p class="eyebrow">Journal sections 32 to 35 · this morning</p>
    <h2 id="t5">A qualification check, written down first</h2></div></div>
  <p>You asked for a qualification evaluation. The SDLC session had a fix ready, since released as ShipLoop 2.4.1, with
  three text corrections: run options are the user's to set, and planning reviews default to on; every stage packet
  now says to stop a background process by the id recorded when it started, never by name; and one guide sentence
  now sends the spec to the knowledge folder. Before opening any result, this session wrote down what "qualified"
  would mean, then read that session's two whole deliveries.</p>
  <div class="table-wrap"><table>
    <thead><tr><th>Check</th><th>ticket-assignment · Sol, high</th><th>shared-expenses · Sonnet, high</th></tr></thead>
    <tbody>
      <tr><th scope="row">Built from the fix and shown the new text</th><td><span class="ok">✓</span> yes</td><td><span class="ok">✓</span> yes</td></tr>
      <tr><th scope="row">Every harness verdict passes</th><td><span class="ok">✓</span> 5 of 5</td><td><span class="ok">✓</span> 5 of 5</td></tr>
      <tr><th scope="row">Case checks</th><td><span class="ok">✓</span> 3 of 3, and 18 of 18 held out</td><td><span class="ok">✓</span> 6 of 6</td></tr>
      <tr><th scope="row">No refusal names the changed text</th><td><span class="ok">✓</span> 0 of 5</td><td><span class="ok">✓</span> 0 of 10</td></tr>
      <tr><th scope="row">Time</th><td>16.5 minutes</td><td>83.0 minutes, $20.48</td></tr>
    </tbody></table></div>
  <div class="verdict"><span class="pill">Qualified</span><div><p>By the rule registered beforehand. It covers what was
  observed: one change to an existing Node service on Sol and one new Node service on Sonnet, each run once. It
  cannot show that the new wording changes behaviour. Both runs had planning reviews on, but so did 20 of 27 earlier
  Sol starts, and neither session ever opened the two guide files that were corrected.</p></div></div>
  <figure>
    <div class="fig-box">
      <div class="legend"><span><i class="sw neutral"></i>20 Nov run, text without the rule</span><span><i class="sw s1"></i>21 Nov run, with the rule</span></div>
      {fig_stops()}
    </div>
    <figcaption><b>Figure 8.</b> How the Sonnet delivery of the same case stopped processes, before and with the new
    rule (one run each). The earlier run used <code>pkill -f "server.js"</code>; the new one wrote each server's id to a
    file when it started it, and once stopped its own timed-out command through the host's task tool. In the new run a
    check for leftovers matched another project's server by name, up for 14 hours. Nothing was stopped, but a stop by
    that pattern would have reached it.</figcaption>
  </figure>
  <p><b>Left open:</b> this delivery took 83 minutes against 49 for the same case before, most of the extra in
  mutation testing. Nothing ties it to the changed text, but one run each cannot rule it out.</p>
</section>

<section class="thread" aria-labelledby="t6">
  <h2 id="t6">How we worked: seven lessons</h2>
  <ol class="lessons">
    <li><b>Read deliveries that already ran before building a bench.</b><span>Section 26 took an hour and no model. It
    should have been section 1.</span></li>
    <li><b>Check a bench against the real thing on a plain measure first.</b><span>Words in the spec would have shown the
    tenfold gap on day one.</span></li>
    <li><b>A count that rewards deciding needs its items sorted by someone else.</b><span>Into what must be settled and
    what need not, by models that did not write the arms.</span></li>
    <li><b>Write the prediction down before the run.</b><span>Eight were registered and six held. The two misses, and one
    surprise, were the informative results.</span></li>
    <li><b>Decide after the first round.</b><span>Dropping the two dead cues after one round would have saved 16 of 96
    sessions and 48 of 192 judge calls.</span></li>
    <li><b>Take the review before the write-up goes anywhere, and check it.</b><span>Both reviews withdrew claims already
    made, and both were right on every fact checked.</span></li>
    <li><b>Judge a wording by what gets built.</b><span>Three wordings that offered to leave a point open changed nothing
    in a count over the spec. Through built products, leaving points open did better.</span></li>
  </ol>
</section>

<section class="thread" aria-labelledby="t7">
  <h2 id="t7">Still open, and yours to decide</h2>
  <ul class="open-list">
    <li><div><b>Do the reference guides make real specifications fuller?</b> On the bench, where sessions read them,
    the released stage was broad. In real runs they are not opened. A small real test is designed, reviewed twice and
    rehearsed offline, and waits for your word: three real runs from one sentence (the stage as released, with one cue
    sentence, and with two guide sections put into its packet), each ended when its specification is accepted. About a
    quarter of an hour and about a dollar. One set can say "worth repeating" or "no sign of it", not more.</div></li>
    <li><div><b>Try "open in the spec, answered in the plan" in ShipLoop?</b> Nothing is proposed yet. It would need your
    word, a candidate build and real end-to-end deliveries, and it is untested where one session writes the plan, the
    tests and the product in turn.</div></li>
    <li><div><b>The 83-minute delivery.</b> The SDLC session has the figures to read.</div></li>
    <li><div><b>Your skills are visible to Codex sessions in the end-to-end harness.</b> The harness was left unchanged as
    your call, because fixing it breaks comparison with earlier Codex runs.</div></li>
  </ul>
</section>

<section class="thread" aria-labelledby="t8">
  <h2 id="t8">Words used on this page</h2>
  <dl class="gloss">
    <dt>Spec stage</dt><dd>The step of a ShipLoop run that turns the request into numbered requirements, each with lines
    saying how it will be checked.</dd>
    <dt>Prompt text, or arm</dt><dd>One version of the instructions given to that stage. P is the released text; letters
    such as K, G, H and R are variants.</dd>
    <dt>Driver</dt><dd>The model that runs the stage: Claude Sonnet, or GPT 6.2 Sol (through Codex).</dd>
    <dt>Hidden checklist</dt><dd>The 89 points a good specification should cover, written before any run and never shown
    to the models.</dd>
    <dt>Judge</dt><dd>A model that marks which checklist points a specification covers. Opus was registered first; Astra
    was the second judge.</dd>
    <dt>Band</dt><dd>The smallest difference counted as real, set from how much two runs of the same text differ.</dd>
    <dt>Open point</dt><dd>Something the request leaves undecided. With the reworded text it is written as an
    <span class="open-tag">Open:</span> line, not chosen.</dd>
    <dt>Held-out check</dt><dd>A test of the built product written beforehand, which the run never sees.</dd>
    <dt>Correct reference</dt><dd>A hand-built product that does what was asked, used to see whether a test suite wrongly
    fails a correct product.</dd>
    <dt>Qualification</dt><dd>Evidence that a ShipLoop change still delivers whole projects end to end.</dd>
  </dl>
</section>

<footer>
  <p>Every figure comes from <code>docs/spec-elaboration-journal.md</code> on <code>main</code>; threads 3 and 4 are the Ratchet
  session's results as recorded there, checked against its journal and not re-run here. Prepared 21 November 2026.</p>
</footer>
</main>
<div id="tip" role="tooltip" hidden></div>
<script>{JS}</script>
"""


if __name__ == "__main__":
    OUT.write_text(page())
    print(OUT, OUT.stat().st_size, "bytes")
