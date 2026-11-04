#!/usr/bin/env python3
"""Render assets/achievements.svg (the animated trophy shelf) from data/achievements.json.

Run locally with `python3 scripts/build_achievements.py`; the "Achievement wall"
workflow runs it automatically whenever the JSON changes.
"""
import json
import math
import pathlib
from html import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "achievements.json"
OUT = ROOT / "assets" / "achievements.svg"

W = 1200
PAD = 44
GAP = 20
COLS_MAX = 4
CARD_H = 430
HEAD_H = 150

MR = 66  # medal radius

TIERS = {
    "gold":   {"label": "GOLD",   "c": "#f5c542", "ink": "#5e420a", "hi": "#fff6d0", "stops": ["#fff4c2", "#f3cd5a", "#cf9a1c", "#9c7012"], "rim": ["#fff1b8", "#d9a521", "#7c5a0e", "#e8b93a", "#6b4b0a"]},
    "silver": {"label": "SILVER", "c": "#cbd5e1", "ink": "#334155", "hi": "#ffffff", "stops": ["#ffffff", "#e5e9f0", "#a3adbd", "#5b6577"], "rim": ["#ffffff", "#c3cad6", "#5b6577", "#dfe4ec", "#475163"]},
    "bronze": {"label": "BRONZE", "c": "#d6925a", "ink": "#4a2610", "hi": "#ffe4cc", "stops": ["#ffe0c2", "#e2a46c", "#b06a34", "#7a4420"], "rim": ["#ffe0c2", "#c98448", "#6f3c18", "#dd9a5c", "#5c3014"]},
    "title":  {"label": "TITLE",  "c": "#c4b5fd", "ink": "#2e1065", "hi": "#ffffff", "stops": [], "rim": []},
}


def pol(r, deg, cx=0.0, cy=0.0):
    a = math.radians(deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def wrap(text, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= width:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > 3:
        lines = lines[:3]
        lines[-1] = lines[-1].rstrip(" ,·") + "…"
    return lines


# ---------------------------------------------------------------- icons
def icon_laurel(s):
    out = []
    for side in (-1, 1):
        for k in range(8):
            th = 90 + side * (16 + k * 15)
            for off, rot in ((4.2 * s, 28), (-4.2 * s, -28)):
                x, y = pol(26 * s + off, th)
                ang = th + 90 * (-side) + rot * side
                z = 1 - k * 0.05
                out.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{6.2*s*z:.1f}" ry="{2.5*s*z:.1f}" transform="rotate({ang:.1f} {x:.1f} {y:.1f})"/>')
    pts = []
    for k in range(10):
        rr = (11 if k % 2 == 0 else 4.6) * s
        x, y = pol(rr, -90 + 36 * k)
        pts.append(f"{x:.1f} {y-2*s:.1f}")
    out.append(f'<path d="M{" L".join(pts)}Z"/>')
    return "".join(out)


def icon_bulb(s):
    return (f'<path d="M0 {-20*s:.1f}C{11*s:.1f} {-20*s:.1f} {17*s:.1f} {-12*s:.1f} {17*s:.1f} {-3*s:.1f}C{17*s:.1f} {5*s:.1f} {9*s:.1f} {9*s:.1f} {8*s:.1f} {15*s:.1f}H{-8*s:.1f}C{-9*s:.1f} {9*s:.1f} {-17*s:.1f} {5*s:.1f} {-17*s:.1f} {-3*s:.1f}C{-17*s:.1f} {-12*s:.1f} {-11*s:.1f} {-20*s:.1f} 0 {-20*s:.1f}Z"/>'
            f'<rect x="{-8*s:.1f}" y="{17*s:.1f}" width="{16*s:.1f}" height="{3.2*s:.1f}" rx="1"/>'
            f'<rect x="{-6.5*s:.1f}" y="{22*s:.1f}" width="{13*s:.1f}" height="{3.2*s:.1f}" rx="1"/>'
            + "".join(
                f'<rect x="{-1.3*s:.1f}" y="{-34*s:.1f}" width="{2.6*s:.1f}" height="{7*s:.1f}" rx="1.3" transform="rotate({a})"/>'
                for a in (-60, -30, 0, 30, 60)))


def icon_wings(s):
    out = []
    for side in (-1, 1):
        for k in range(4):
            L = (30 - k * 5) * s
            y0 = (-8 + k * 6) * s
            x0 = side * 6 * s
            x1 = x0 + side * L
            y1 = y0 - (14 - k * 3) * s
            out.append(f'<path d="M{x0:.1f} {y0:.1f}Q{x0+side*L*0.6:.1f} {y1-4*s:.1f} {x1:.1f} {y1:.1f}Q{x0+side*L*0.55:.1f} {y0-1*s:.1f} {x0:.1f} {y0+4.5*s:.1f}Z"/>')
    out.append(f'<path d="M{-9*s:.1f} {-6*s:.1f}H{9*s:.1f}V{8*s:.1f}Q{9*s:.1f} {18*s:.1f} 0 {23*s:.1f}Q{-9*s:.1f} {18*s:.1f} {-9*s:.1f} {8*s:.1f}Z"/>')
    out.append(f'<circle cx="0" cy="{-13*s:.1f}" r="{5*s:.1f}"/>')
    return "".join(out)


def icon_star(s):
    pts = []
    for k in range(10):
        rr = (18 if k % 2 == 0 else 7.5) * s
        x, y = pol(rr, -90 + 36 * k)
        pts.append(f"{x:.1f} {y:.1f}")
    return f'<path d="M{" L".join(pts)}Z"/>'


ICONS = {"laurel": icon_laurel, "bulb": icon_bulb, "wings": icon_wings, "star": icon_star}


# ---------------------------------------------------------------- medal
def medal(i, cx, cy, r, tier, icon):
    t = TIERS[tier]
    g = []
    g.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#rim-{tier})"/>')
    g.append(f'<circle cx="{cx}" cy="{cy}" r="{r-2}" fill="none" stroke="{t["ink"]}" stroke-opacity=".45" stroke-width="2.4" stroke-dasharray="1.3 2"/>')
    g.append(f'<circle cx="{cx}" cy="{cy}" r="{r-6}" fill="url(#rim2-{tier})"/>')
    g.append(f'<circle cx="{cx}" cy="{cy}" r="{r-10}" fill="url(#face-{tier})"/>')
    g.append(f'<g clip-path="url(#mc{i})" stroke-width="1.3">')
    for k in range(96):
        x, y = pol(r, 360 * k / 96, cx, cy)
        col, op = ("#ffffff", .18) if k % 2 else (t["ink"], .10)
        g.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{col}" stroke-opacity="{op}"/>')
    g.append("</g>")
    g.append(f'<circle cx="{cx}" cy="{cy}" r="{r-17}" fill="none" stroke="{t["ink"]}" stroke-opacity=".45"/>')
    inner = ICONS.get(icon, icon_star)(r / 60)
    word = f'<text class="serif" x="0" y="{r*0.70:.1f}" text-anchor="middle" font-size="{r*0.135:.1f}" font-weight="700" letter-spacing="2">{t["label"]}</text>'
    g.append(f'<g transform="translate({cx} {cy - r*0.06:.1f})"><g transform="translate(0 1)" fill="{t["hi"]}" opacity=".55">{inner}{word}</g><g fill="{t["ink"]}">{inner}{word}</g></g>')
    g.append(f'<g clip-path="url(#mc{i})"><rect class="sweep" style="animation-delay:{i*0.7:.1f}s" x="{cx-24}" y="{cy-r-30}" width="48" height="{2*r+60}" fill="url(#shine)" transform="rotate(22 {cx} {cy})"/></g>')
    return "".join(g)


def rosette(i, cx, cy):
    g = [f'<circle cx="{cx}" cy="{cy}" r="58" fill="#14111c" stroke="url(#holo)" stroke-width="1.4"/>']
    g.append(f'<g class="rot" style="transform-origin:{cx}px {cy}px" fill="none" stroke="url(#holo)" stroke-width=".8" opacity=".9">')
    g += [f'<ellipse cx="{cx}" cy="{cy}" rx="50" ry="16" transform="rotate({k*10} {cx} {cy})"/>' for k in range(18)]
    g.append("</g>")
    g.append(f'<g class="rot rev" style="transform-origin:{cx}px {cy}px" fill="none" stroke="#f5c542" stroke-width=".6" opacity=".55">')
    g += [f'<ellipse cx="{cx}" cy="{cy}" rx="36" ry="10" transform="rotate({k*15} {cx} {cy})"/>' for k in range(12)]
    g.append("</g>")
    g.append(f'<circle cx="{cx}" cy="{cy}" r="22" fill="#14111c" stroke="#f5c542" stroke-opacity=".7"/>')
    g.append(f'<text class="serif" x="{cx}" y="{cy+6}" text-anchor="middle" font-size="16" font-weight="700" fill="#fde68a">Inv.</text>')
    return "".join(g)


# ---------------------------------------------------------------- build
def build():
    items = json.loads(DATA.read_text(encoding="utf8"))["achievements"]
    n = len(items)
    cols = min(COLS_MAX, n)
    rows = math.ceil(n / cols)
    cw = (W - 2 * PAD - (cols - 1) * GAP) / cols
    H = HEAD_H + rows * CARD_H + (rows - 1) * GAP + 40

    counts = {}
    for it in items:
        counts[it["tier"]] = counts.get(it["tier"], 0) + 1

    o = []
    A = o.append
    desc = "; ".join(f'{TIERS[it["tier"]]["label"].title()} — {it["org"]}: {it["event"]}' + (f' (project: {it["project"]})' if it["project"] else "") for it in items)
    A(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H:.0f}" viewBox="0 0 {W} {H:.0f}" role="img" aria-labelledby="t d">')
    A('  <title id="t">Achievement wall</title>')
    A(f'  <desc id="d">{escape(desc)}</desc>')
    A("  <defs>")
    A('    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#07080e"/><stop offset=".5" stop-color="#0b0c16"/><stop offset="1" stop-color="#07070c"/></linearGradient>')
    A('    <radialGradient id="glowG" cx=".2" cy=".35" r=".5"><stop stop-color="#f5c542" stop-opacity=".10"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>')
    A('    <radialGradient id="glowV" cx=".9" cy=".1" r=".5"><stop stop-color="#a78bfa" stop-opacity=".09"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>')
    A('    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#94a3b8" stroke-opacity=".035"/></pattern>')
    A('    <linearGradient id="shine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".8"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>')
    A('    <linearGradient id="holo" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f5c542"/><stop offset=".25" stop-color="#22d3ee"/><stop offset=".5" stop-color="#a78bfa"/><stop offset=".75" stop-color="#f472b6"/><stop offset="1" stop-color="#f5c542"/>'
      '<animateTransform attributeName="gradientTransform" type="rotate" values="0 .5 .5;360 .5 .5" dur="8s" repeatCount="indefinite"/></linearGradient>')
    for name, t in TIERS.items():
        if not t["stops"]:
            continue
        s = t["stops"]
        A(f'    <radialGradient id="face-{name}" cx="40%" cy="34%" r="74%"><stop offset="0" stop-color="{s[0]}"/><stop offset=".35" stop-color="{s[1]}"/><stop offset=".78" stop-color="{s[2]}"/><stop offset="1" stop-color="{s[3]}"/></radialGradient>')
        rm = t["rim"]
        A(f'    <linearGradient id="rim-{name}" x1="0" y1="0" x2="1" y2="1">' + "".join(f'<stop offset="{k/4:.2f}" stop-color="{c}"/>' for k, c in enumerate(rm)) + "</linearGradient>")
        A(f'    <linearGradient id="rim2-{name}" x1="1" y1="1" x2="0" y2="0">' + "".join(f'<stop offset="{k/4:.2f}" stop-color="{c}"/>' for k, c in enumerate(rm)) + "</linearGradient>")
    for name, t in TIERS.items():
        A(f'    <radialGradient id="halo-{name}"><stop offset="0" stop-color="{t["c"]}" stop-opacity=".20"/><stop offset=".6" stop-color="{t["c"]}" stop-opacity=".05"/><stop offset="1" stop-color="{t["c"]}" stop-opacity="0"/></radialGradient>')
    A('    <pattern id="dots" width="7" height="7" patternUnits="userSpaceOnUse"><ellipse cx="3.5" cy="3.5" rx="1.3" ry="1.7" fill="#fff" fill-opacity=".85"/></pattern>')
    A('    <filter id="drop" x="-40%" y="-40%" width="180%" height="190%"><feDropShadow dx="0" dy="12" stdDeviation="10" flood-color="#000" flood-opacity=".6"/></filter>')
    A('    <filter id="glw" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    A(f'    <clipPath id="c"><rect width="{W}" height="{H:.0f}" rx="28"/></clipPath>')

    geo = []
    for i, it in enumerate(items):
        r_, c_ = divmod(i, cols)
        x = PAD + c_ * (cw + GAP)
        y = HEAD_H + r_ * (CARD_H + GAP)
        cx, cy = x + cw / 2, y + 138
        geo.append((x, y, cx, cy))
        A(f'    <clipPath id="mc{i}"><circle cx="{cx:.1f}" cy="{cy:.1f}" r="{MR-10}"/></clipPath>')
        A(f'    <clipPath id="cc{i}"><rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="{CARD_H}" rx="20"/></clipPath>')

    A("    <style>")
    A("      .s{font-family:'Inter','Segoe UI',-apple-system,BlinkMacSystemFont,Arial,sans-serif}")
    A("      .m{font-family:'JetBrains Mono','SF Mono',ui-monospace,Menlo,Consolas,monospace}")
    A("      .serif{font-family:'Cinzel','Trajan Pro',Georgia,'Times New Roman',serif}")
    A("      .swing{animation:swing 5s ease-in-out infinite}")
    A("      @keyframes swing{0%,100%{transform:rotate(-3deg)}50%{transform:rotate(3deg)}}")
    A("      .sweep{animation:sw 4.5s ease-in-out infinite}")
    A("      @keyframes sw{0%,45%{transform:translateX(-120px)}80%,100%{transform:translateX(120px)}}")
    A("      .rot{animation:spin 26s linear infinite}.rev{animation-duration:40s;animation-direction:reverse}")
    A("      @keyframes spin{to{transform:rotate(360deg)}}")
    A("      .card{animation:up .9s cubic-bezier(.2,.7,.2,1) both}")
    A("      @keyframes up{from{opacity:0;transform:translateY(22px)}to{opacity:1;transform:none}}")
    A("      .tw{transform-box:fill-box;transform-origin:center;animation:tw 3s ease-in-out infinite}")
    A("      @keyframes tw{0%,100%{opacity:0;transform:scale(.2)}50%{opacity:1;transform:scale(1) rotate(45deg)}}")
    A("      .halo{animation:halo 4s ease-in-out infinite}")
    A("      @keyframes halo{0%,100%{opacity:.35}50%{opacity:.8}}")
    A("      @media (prefers-reduced-motion: reduce){*{animation:none!important}}")
    A("    </style>")
    A("  </defs>")
    A('  <g clip-path="url(#c)">')
    A(f'    <rect width="{W}" height="{H:.0f}" fill="url(#bg)"/><rect width="{W}" height="{H:.0f}" fill="url(#grid)"/><rect width="{W}" height="{H:.0f}" fill="url(#glowG)"/><rect width="{W}" height="{H:.0f}" fill="url(#glowV)"/>')

    # header
    A(f'    <text class="m" x="{PAD}" y="56" font-size="11.5" letter-spacing="2.4" fill="#64748b">ACHIEVEMENT WALL · BUILT FROM data/achievements.json</text>')
    A(f'    <text class="s" x="{PAD-2}" y="104" font-size="40" font-weight="800" letter-spacing="-1.5" fill="#f8fafc">The trophy shelf.</text>')
    cx_ = W - PAD
    for tier in ("title", "bronze", "silver", "gold"):
        if tier not in counts:
            continue
        t = TIERS[tier]
        label = t["label"]
        w = 34 + len(label) * 9 + 30
        cx_ -= w
        A(f'    <g transform="translate({cx_:.0f} 66)"><rect width="{w-12}" height="48" rx="14" fill="#0e111c" stroke="{t["c"]}" stroke-opacity=".45"/>'
          f'<text class="s" x="16" y="33" font-size="26" font-weight="800" fill="{t["c"]}">{counts[tier]}</text>'
          f'<text class="m" x="{w-26}" y="30" font-size="11.5" letter-spacing="1.6" fill="#94a3b8" text-anchor="end">{label}</text></g>')

    # cards
    for i, (it, (x, y, cx, cy)) in enumerate(zip(items, geo)):
        t = TIERS[it["tier"]]
        A(f'    <g class="card" style="animation-delay:{0.15*i:.2f}s">')
        A(f'      <rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="{CARD_H}" rx="20" fill="#0c0f1a" stroke="{t["c"]}" stroke-opacity=".28"/>')
        A(f'      <g clip-path="url(#cc{i})"><circle class="halo" style="animation-delay:{i*.6:.1f}s" cx="{cx:.1f}" cy="{cy:.1f}" r="130" fill="url(#halo-{it["tier"]})"/></g>')
        A(f'      <rect x="{x+24:.1f}" y="{y:.1f}" width="{cw-48:.1f}" height="2" fill="{t["c"]}" opacity=".7"/>')
        if it["tier"] == "title":
            A("      " + rosette(i, cx, cy))
        else:
            rib = it.get("ribbon") or ["#1e3a8a", "#9f1239"]
            A(f'      <g class="swing" style="transform-origin:{cx:.1f}px {y:.1f}px;animation-delay:-{i*1.3:.1f}s">')
            A(f'        <path d="M{cx-30:.1f} {y:.1f}L{cx-6:.1f} {y:.1f}L{cx+9:.1f} {cy-MR+10:.1f}L{cx-9:.1f} {cy-MR+10:.1f}Z" fill="{rib[0]}"/>')
            A(f'        <path d="M{cx+30:.1f} {y:.1f}L{cx+6:.1f} {y:.1f}L{cx-9:.1f} {cy-MR+10:.1f}L{cx+9:.1f} {cy-MR+10:.1f}Z" fill="{rib[-1]}"/>')
            if it.get("ribbon_style") == "dots":
                A(f'        <path d="M{cx-30:.1f} {y:.1f}L{cx-6:.1f} {y:.1f}L{cx+9:.1f} {cy-MR+10:.1f}L{cx-9:.1f} {cy-MR+10:.1f}Z" fill="url(#dots)"/>')
                A(f'        <path d="M{cx+30:.1f} {y:.1f}L{cx+6:.1f} {y:.1f}L{cx-9:.1f} {cy-MR+10:.1f}L{cx+9:.1f} {cy-MR+10:.1f}Z" fill="url(#dots)"/>')
            else:
                A(f'        <path d="M{cx-21:.1f} {y:.1f}L{cx-15:.1f} {y:.1f}L{cx+1:.1f} {cy-MR+10:.1f}L{cx-2:.1f} {cy-MR+10:.1f}Z" fill="{t["c"]}" opacity=".85"/>')
            A(f'        <ellipse cx="{cx:.1f}" cy="{cy-MR-3:.1f}" rx="12" ry="6.5" fill="none" stroke="url(#rim-{it["tier"]})" stroke-width="4"/>')
            A(f'        <g filter="url(#drop)">{medal(i, cx, cy, MR, it["tier"], it.get("icon", "star"))}</g>')
            A("      </g>")
            if it["tier"] == "gold":
                A('      <g fill="#fffbeb" filter="url(#glw)">' + "".join(
                    f'<path class="tw" style="animation-delay:{(i*.5+k*.9):.1f}s" transform="translate({cx+dx:.1f} {cy+dy:.1f}) scale({sc})" d="M0 -10C1.2 -2 2 -1.2 10 0C2 1.2 1.2 2 0 10C-1.2 2 -2 1.2 -10 0C-2 -1.2 -1.2 -2 0 -10Z"/>'
                    for k, (dx, dy, sc) in enumerate([(-78, -40, .8), (74, -10, .6), (-60, 52, .5)])) + "</g>")
        # text
        ty = y + 248
        A(f'      <g transform="translate({cx:.1f} {ty})"><rect x="-38" y="-15" width="76" height="22" rx="11" fill="{t["c"]}" fill-opacity=".12" stroke="{t["c"]}" stroke-opacity=".6"/>'
          f'<text class="m" y="0.5" text-anchor="middle" font-size="10.5" font-weight="700" letter-spacing="2" fill="{t["c"]}">{t["label"]}</text></g>')
        A(f'      <text class="s" x="{cx:.1f}" y="{ty+38}" text-anchor="middle" font-size="22" font-weight="800" letter-spacing="-.5" fill="#f8fafc">{escape(it["org"])}</text>')
        for k, line in enumerate(wrap(it["event"], int(cw / 7.4))):
            A(f'      <text class="s" x="{cx:.1f}" y="{ty+60+k*17}" text-anchor="middle" font-size="12.5" fill="#94a3b8">{escape(line)}</text>')
        by = y + CARD_H - 20
        meta = [v for v in (it.get("place"), it.get("date")) if v]
        if it["tier"] == "title":
            if meta:
                A(f'      <text class="m" x="{cx:.1f}" y="{by-26}" text-anchor="middle" font-size="9.5" letter-spacing="1.8" fill="#64748b">{escape(meta[0].upper())}</text>')
            if len(meta) > 1:
                A(f'      <text class="m" x="{cx:.1f}" y="{by-4}" text-anchor="middle" font-size="14.5" font-weight="700" letter-spacing="1.6" fill="#e9d5ff">{escape(meta[1])}</text>')
        else:
            if it.get("project"):
                label = f'PROJECT · {it["project"].upper()}'
                pw = len(label) * 7 + 22
                A(f'      <g transform="translate({cx:.1f} {by-44})"><rect x="{-pw/2:.1f}" y="-14" width="{pw:.1f}" height="21" rx="6" fill="#111827" stroke="#334155"/>'
                  f'<text class="m" y="0.5" text-anchor="middle" font-size="10.5" font-weight="700" letter-spacing="1" fill="#e2e8f0">{escape(label)}</text></g>')
            for k, v in enumerate(meta[:2]):
                A(f'      <text class="m" x="{cx:.1f}" y="{by - (len(meta[:2]) - 1 - k) * 15}" text-anchor="middle" font-size="10.5" fill="#64748b">{escape(v)}</text>')
        A("    </g>")

    A(f'    <rect x=".75" y=".75" width="{W-1.5}" height="{H-1.5:.1f}" rx="27.5" fill="none" stroke="#a5b4fc" stroke-opacity=".15"/>')
    A("  </g>")
    A("</svg>")
    OUT.write_text("\n".join(o) + "\n", encoding="utf8")
    print(f"wrote {OUT.relative_to(ROOT)} ({n} achievements)")


if __name__ == "__main__":
    build()
