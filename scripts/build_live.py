#!/usr/bin/env python3
"""Render a live status card (live.svg) from the GitHub API.

Runs inside the "Profile automation" workflow with GITHUB_TOKEN. Locally:
    MOCK=1 python3 scripts/build_live.py --out /tmp/live.svg
Every number degrades to "—" if the API is unavailable, so the card never breaks.
"""
import argparse
import datetime as dt
import json
import os
import urllib.request
from html import escape

USER = os.environ.get("PROFILE_USER", "SamAfshar2011")
GOLD_DAY = dt.date(2026, 7, 5)       # IFIA gold medal, Geneva
W, H = 1200, 470

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, first: 100, orderBy: {field: PUSHED_AT, direction: DESC}) {
      totalCount
      nodes {
        name isFork stargazerCount pushedAt
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } }
        defaultBranchRef { target { ... on Commit { history(first: 8) { nodes { messageHeadline committedDate author { user { login } } } } } } }
      }
    }
    contributionsCollection {
      contributionCalendar { totalContributions weeks { contributionDays { contributionCount date } } }
    }
  }
}
"""


def fetch():
    if os.environ.get("MOCK"):
        return mock()
    token = os.environ.get("GITHUB_TOKEN", "")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "profile-live-card"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        print("GraphQL errors:", data["errors"])
    return data.get("data", {}).get("user") or {}


def mock():
    import random
    random.seed(4)
    days, start = [], dt.date.today() - dt.timedelta(days=364)
    for i in range(365):
        d = start + dt.timedelta(days=i)
        days.append({"date": d.isoformat(), "contributionCount": random.choice([0, 0, 1, 2, 3, 5, 8, 0, 4, 12])})
    weeks = [{"contributionDays": days[i:i + 7]} for i in range(0, 365, 7)]
    langs = lambda *p: {"edges": [{"size": s, "node": {"name": n, "color": c}} for n, c, s in p]}
    return {
        "followers": {"totalCount": 12},
        "repositories": {"totalCount": 10, "nodes": [
            {"name": "Persian_ALPR_project", "isFork": False, "stargazerCount": 3, "languages": langs(("Jupyter Notebook", "#DA5B0B", 900000), ("Python", "#3572A5", 300000)),
             "defaultBranchRef": {"target": {"history": {"nodes": [{"messageHeadline": "Add Kalman-based track consensus for video inference", "committedDate": dt.datetime.now(dt.timezone.utc).isoformat(), "author": {"user": {"login": USER}}}]}}}},
            {"name": "1i1w_competition", "isFork": False, "stargazerCount": 2, "languages": langs(("HTML", "#e34c26", 400000), ("JavaScript", "#f1e05a", 120000), ("CSS", "#563d7c", 60000))},
            {"name": "innoverse2026-Fiscora", "isFork": False, "stargazerCount": 2, "languages": langs(("Jupyter Notebook", "#DA5B0B", 500000), ("HTML", "#e34c26", 200000), ("Python", "#3572A5", 90000))},
        ]},
        "contributionsCollection": {"contributionCalendar": {"totalContributions": sum(d["contributionCount"] for d in days), "weeks": weeks}},
    }


# ------------------------------------------------------------------ data
def summarize(u):
    out = {"contrib": None, "streak": None, "longest": None, "repos": None, "stars": None, "followers": None,
           "langs": [], "weeks": [], "commit": None}
    try:
        cal = u["contributionsCollection"]["contributionCalendar"]
        out["contrib"] = cal["totalContributions"]
        days = [d for w in cal["weeks"] for d in w["contributionDays"]]
        out["weeks"] = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cal["weeks"]][-52:]
        cur = best = run = 0
        for d in days:
            run = run + 1 if d["contributionCount"] > 0 else 0
            best = max(best, run)
        # current streak: count back from today (today may still be empty)
        for i, d in enumerate(reversed(days)):
            if d["contributionCount"] > 0:
                cur += 1
            elif i == 0:
                continue
            else:
                break
        out["streak"], out["longest"] = cur, best
    except Exception as e:  # noqa: BLE001
        print("calendar unavailable:", e)
    try:
        repos = u["repositories"]
        out["repos"] = repos["totalCount"]
        own = [r for r in repos["nodes"] if not r.get("isFork")]
        out["stars"] = sum(r.get("stargazerCount", 0) for r in own)
        tot = {}
        for r in own:
            for e in (r.get("languages") or {}).get("edges", []):
                n = e["node"]["name"]
                tot.setdefault(n, [0, e["node"].get("color") or "#64748b"])[0] += e["size"]
        s = sum(v[0] for v in tot.values()) or 1
        top = sorted(tot.items(), key=lambda kv: -kv[1][0])[:6]
        short = {"Jupyter Notebook": "Jupyter", "JavaScript": "JS", "TypeScript": "TS"}
        out["langs"] = [(short.get(n, n), c, v / s) for n, (v, c) in top]
        for r in repos["nodes"]:
            if r["name"].lower() == USER.lower():
                continue  # skip the profile repo's own automation commits
            hist = (((r.get("defaultBranchRef") or {}).get("target") or {}).get("history") or {}).get("nodes") or []
            for c in hist:
                login = (((c.get("author") or {}).get("user")) or {}).get("login", "")
                if login.lower() == USER.lower():
                    out["commit"] = (r["name"], c["messageHeadline"], c["committedDate"])
                    break
            if out["commit"]:
                break
    except Exception as e:  # noqa: BLE001
        print("repositories unavailable:", e)
    out["followers"] = (u.get("followers") or {}).get("totalCount")
    return out


# ------------------------------------------------------------------ awards
def _awards():
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "achievements.json")
        with open(path, encoding="utf8") as f:
            return json.load(f)["achievements"]
    except Exception:  # noqa: BLE001
        return []


def medal_count():
    a = [x for x in _awards() if x.get("tier") in ("gold", "silver", "bronze")]
    return len(a) if a else None


def medal_line():
    a = _awards()
    parts = [f"{sum(1 for x in a if x.get('tier') == t)}× {t}" for t in ("gold", "silver", "bronze") if any(x.get("tier") == t for x in a)]
    return " · ".join(parts) or "—"


# ------------------------------------------------------------------ render
def odometer(uid, value, x, y, size=46, color="#f8fafc", delay=0.0):
    """Rolling digit reels landing on `value`."""
    if value is None:
        return f'<text class="s" x="{x}" y="{y}" font-size="{size}" font-weight="800" fill="#475569">—</text>'
    digits = f"{value:,}"
    lh = size * 1.1
    cw = size * 0.62
    parts, cx = [], x
    for k, ch in enumerate(digits):
        if not ch.isdigit():
            parts.append(f'<text class="s" x="{cx:.1f}" y="{y}" font-size="{size}" font-weight="800" fill="{color}">{ch}</text>')
            cx += size * 0.3
            continue
        d = int(ch)
        target = 10 + d
        cid = f"{uid}d{k}"
        parts.append(f'<clipPath id="{cid}"><rect x="{cx-2:.1f}" y="{y - size*0.86:.1f}" width="{cw+4:.1f}" height="{lh:.1f}"/></clipPath>')
        reel = "".join(f'<text x="{cx:.1f}" y="{y + i*lh:.1f}">{i % 10}</text>' for i in range(20))
        parts.append(f'<g clip-path="url(#{cid})"><g class="reel s" font-size="{size}" font-weight="800" fill="{color}" '
                     f'style="--to:translateY(-{target*lh:.1f}px);transform:translateY(-{target*lh:.1f}px);animation-delay:{delay + k*0.12:.2f}s">{reel}</g></g>')
        cx += cw
    return "".join(parts)


def ago(iso, now):
    try:
        t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return t.strftime("%d %b %Y · %H:%M UTC")
    except Exception:  # noqa: BLE001
        return ""


def render(s, now):
    o = []
    A = o.append
    days_gold = (now.date() - GOLD_DAY).days
    A(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">')
    A('<title id="t">Live from GitHub</title>')
    A(f'<desc id="d">Live profile card generated {now:%Y-%m-%d %H:%M} UTC: {s["contrib"]} contributions in the last 12 months, {medal_count()} medals, {s["repos"]} public repositories, {s["stars"]} stars, {days_gold} days since the Geneva gold medal.</desc>')
    A("""<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#06070d"/><stop offset=".55" stop-color="#0a0d18"/><stop offset="1" stop-color="#06070d"/></linearGradient>
  <radialGradient id="gl" cx=".85" cy=".1" r=".6"><stop stop-color="#22d3ee" stop-opacity=".10"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
  <radialGradient id="gl2" cx=".1" cy=".95" r=".6"><stop stop-color="#a78bfa" stop-opacity=".10"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
  <linearGradient id="acc" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#22d3ee"/><stop offset=".5" stop-color="#a78bfa"/><stop offset="1" stop-color="#f472b6"/></linearGradient>
  <linearGradient id="bar" x1="0" y1="1" x2="0" y2="0"><stop stop-color="#22d3ee" stop-opacity=".35"/><stop offset="1" stop-color="#a78bfa"/></linearGradient>
  <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#94a3b8" fill-opacity=".07"/></pattern>
  <clipPath id="c"><rect width="1200" height="470" rx="26"/></clipPath>
  <filter id="glw" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <style>
    .s{font-family:'Inter','Segoe UI',-apple-system,BlinkMacSystemFont,Arial,sans-serif}
    .m{font-family:'JetBrains Mono','SF Mono',ui-monospace,Menlo,Consolas,monospace}
    .reel{animation:roll 2.2s cubic-bezier(.15,.75,.2,1) both}
    @keyframes roll{from{transform:translateY(0)}to{transform:var(--to)}}
    .live{animation:pulse 1.4s ease-in-out infinite}
    @keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
    .ring{transform-box:fill-box;transform-origin:center;animation:ring 1.8s ease-out infinite}
    @keyframes ring{from{transform:scale(.6);opacity:.8}to{transform:scale(2.4);opacity:0}}
    .grow{transform-box:fill-box;transform-origin:bottom;animation:grow 1.4s cubic-bezier(.2,.8,.2,1) both}
    @keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
    .lang{transform-box:fill-box;transform-origin:left;animation:lang 1.6s cubic-bezier(.2,.8,.2,1) both}
    @keyframes lang{from{transform:scaleX(0)}to{transform:scaleX(1)}}
    .type{animation:type 2.6s steps(48) .6s both}
    @keyframes type{from{clip-path:inset(0 100% 0 0)}to{clip-path:inset(0 0 0 0)}}
    .cur{animation:blink 1s steps(1) infinite}
    @keyframes blink{50%{opacity:0}}
    .rise{animation:rise .9s cubic-bezier(.2,.7,.2,1) both}
    @keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
    @media (prefers-reduced-motion: reduce){*{animation:none!important}}
  </style>
</defs>""")
    A('<g clip-path="url(#c)">')
    A(f'<rect width="{W}" height="{H}" fill="url(#bg)"/><rect width="{W}" height="{H}" fill="url(#dots)"/><rect width="{W}" height="{H}" fill="url(#gl)"/><rect width="{W}" height="{H}" fill="url(#gl2)"/>')

    # header
    A('<g class="m">')
    A('<rect x="44" y="34" width="86" height="28" rx="14" fill="#2a0b10" stroke="#ef4444" stroke-opacity=".6"/>')
    A('<circle class="ring" cx="62" cy="48" r="5" fill="none" stroke="#ef4444" stroke-width="1.5"/><circle class="live" cx="62" cy="48" r="4.5" fill="#ef4444"/>')
    A('<text x="74" y="53" font-size="12" font-weight="700" letter-spacing="2" fill="#fca5a5">LIVE</text>')
    A(f'<text x="146" y="53" font-size="11.5" letter-spacing="1.8" fill="#64748b">STRAIGHT FROM THE GITHUB API · UPDATED {now:%d %b %Y · %H:%M} UTC</text>')
    A('<text x="1156" y="53" font-size="11" letter-spacing="1.4" fill="#475569" text-anchor="end">refreshes every 6 hours</text>')
    A('</g>')

    # tiles
    tiles = [
        ("CONTRIBUTIONS", "last 12 months", s["contrib"], "#67e8f9"),
        ("MEDALS WON", medal_line(), medal_count(), "#a78bfa"),
        ("PUBLIC REPOS", f"{s['stars'] if s['stars'] is not None else '—'} stars earned", s["repos"], "#f472b6"),
        ("DAYS SINCE GOLD", "Geneva · 5 Jul 2026", days_gold, "#fbbf24"),
    ]
    tw, gap = 263, 20
    for i, (label, sub, val, col) in enumerate(tiles):
        x = 44 + i * (tw + gap)
        A(f'<g class="rise" style="animation-delay:{i*.1:.1f}s">')
        A(f'<rect x="{x}" y="84" width="{tw}" height="128" rx="18" fill="#0c1120" stroke="{col}" stroke-opacity=".28"/>')
        A(f'<rect x="{x+20}" y="84" width="{tw-40}" height="2" fill="{col}" opacity=".7"/>')
        A(f'<text class="m" x="{x+20}" y="114" font-size="11" letter-spacing="1.8" fill="#64748b">{label}</text>')
        A(odometer(f"t{i}", val, x + 20, 170, 46, "#f8fafc", .2 + i * .15))
        A(f'<text class="m" x="{x+20}" y="196" font-size="11" fill="{col}" opacity=".85">{escape(sub)}</text>')
        A('</g>')

    # latest commit
    A('<g class="rise" style="animation-delay:.4s">')
    A('<rect x="44" y="232" width="556" height="196" rx="18" fill="#0b0f1a" stroke="#a5b4fc" stroke-opacity=".16"/>')
    A('<rect x="44" y="232" width="556" height="36" rx="18" fill="#0f1426"/><rect x="44" y="250" width="556" height="18" fill="#0f1426"/>')
    for k, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        A(f'<circle cx="{68 + k*20}" cy="250" r="5.5" fill="{c}"/>')
    A('<text class="m" x="576" y="255" font-size="11" fill="#475569" text-anchor="end">latest commit</text>')
    A('<text class="m" x="68" y="300" font-size="13.5" fill="#64748b">$ <tspan fill="#e2e8f0">git log -1 --author=sam</tspan></text>')
    if s["commit"]:
        repo, msg, when = s["commit"]
        msg = msg if len(msg) <= 52 else msg[:51] + "…"
        A(f'<text class="m" x="68" y="330" font-size="12.5" fill="#fbbf24">● <tspan fill="#94a3b8">repo</tspan>  <tspan fill="#67e8f9">{escape(repo)}</tspan></text>')
        A(f'<g class="type"><text class="m" x="68" y="362" font-size="15" font-weight="700" fill="#f8fafc">{escape(msg)}</text></g>')
        A(f'<text class="m" x="68" y="392" font-size="12" fill="#64748b">{escape(ago(when, now))}</text>')
    else:
        A('<text class="m" x="68" y="345" font-size="14" fill="#64748b">no public commits found</text>')
    A('<text class="m" x="68" y="414" font-size="13" fill="#64748b">$ <tspan class="cur" fill="#a78bfa">▍</tspan></text>')
    A('</g>')

    # languages + activity
    A('<g class="rise" style="animation-delay:.5s">')
    A('<rect x="620" y="232" width="536" height="196" rx="18" fill="#0b0f1a" stroke="#a5b4fc" stroke-opacity=".16"/>')
    A('<text class="m" x="644" y="262" font-size="11" letter-spacing="1.8" fill="#64748b">LANGUAGES · BY BYTES ACROSS MY REPOS</text>')
    bx, bw = 644, 488
    if s["langs"]:
        cx = bx
        A(f'<clipPath id="lb"><rect x="{bx}" y="276" width="{bw}" height="12" rx="6"/></clipPath><g clip-path="url(#lb)">')
        for k, (n, c, f) in enumerate(s["langs"]):
            w = max(bw * f, 2)
            A(f'<rect class="lang" style="animation-delay:{.6 + k*.12:.2f}s" x="{cx:.1f}" y="276" width="{w:.1f}" height="12" fill="{c}"/>')
            cx += w
        A('</g>')
        for k, (n, c, f) in enumerate(s["langs"]):
            lx = bx + (k % 3) * 166
            ly = 312 + (k // 3) * 20
            A(f'<circle cx="{lx+5}" cy="{ly-4}" r="4.5" fill="{c}"/><text class="m" x="{lx+16}" y="{ly}" font-size="11.5" fill="#cbd5e1">{escape(n)} <tspan fill="#64748b">{f*100:.1f}%</tspan></text>')
    else:
        A(f'<text class="m" x="{bx}" y="290" font-size="12" fill="#475569">unavailable</text>')
    A('<text class="m" x="644" y="368" font-size="11" letter-spacing="1.8" fill="#64748b">ACTIVITY · 52 WEEKS</text>')
    if s["weeks"]:
        mx = max(s["weeks"]) or 1
        n = len(s["weeks"])
        step = bw / n
        for k, v in enumerate(s["weeks"]):
            h = 4 + 38 * (v / mx) ** 0.5
            A(f'<rect class="grow" style="animation-delay:{.8 + k*.012:.3f}s" x="{bx + k*step:.1f}" y="{414 - h:.1f}" width="{step-2:.1f}" height="{h:.1f}" rx="1.5" fill="url(#bar)" opacity="{.35 + .65*(v/mx) ** 0.5:.2f}"/>')
    A('</g>')

    A(f'<rect x=".75" y=".75" width="{W-1.5}" height="{H-1.5}" rx="25.5" fill="none" stroke="#a5b4fc" stroke-opacity=".15"/>')
    A('</g></svg>')
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist/live.svg")
    a = ap.parse_args()
    now = dt.datetime.now(dt.timezone.utc)
    try:
        u = fetch()
    except Exception as e:  # noqa: BLE001
        print("fetch failed:", e)
        u = {}
    svg = render(summarize(u), now)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf8") as f:
        f.write(svg)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
