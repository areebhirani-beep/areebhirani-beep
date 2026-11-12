"""Render the last year of GitHub contributions as a dark and a light SVG card.

Usage: GITHUB_TOKEN=... GH_USER=areebhirani-beep python3 contrib_graph.py <out_dir>
Standard library only, so the workflow needs no install step.
"""

import json
import os
import sys
import urllib.request
from datetime import date

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""

LEVELS = ["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]

THEMES = {
    "dark": {
        "card": "#161b22", "border": "#30363d", "text": "#e6edf3", "muted": "#8b949e",
        "accent": "#3fb950",
        "cells": ["#21262d", "#0e4429", "#006d32", "#26a641", "#39d353"],
    },
    "light": {
        "card": "#f6f8fa", "border": "#d0d7de", "text": "#1f2328", "muted": "#59636e",
        "accent": "#1a7f37",
        "cells": ["#e6e9ed", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
    },
}

FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
WIDTH, PAD, GAP = 880, 24, 3
GRID_TOP, ROWS = 82, 7
MONTHS = "jan feb mar apr may jun jul aug sep oct nov dec".split()


def fetch(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data:
        sys.exit(f"graphql error: {data['errors']}")
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def month_labels(weeks, pitch):
    """One label per month, at the first week column that starts in that month."""
    labels, prev = [], None
    for i, week in enumerate(weeks):
        month = date.fromisoformat(week["contributionDays"][0]["date"]).month
        if month != prev:
            labels.append((i, MONTHS[month - 1]))
            prev = month
    # Drop a leading partial month whose label would collide with the next one.
    if len(labels) > 1 and labels[1][0] - labels[0][0] < 3:
        labels.pop(0)
    return [(PAD + i * pitch, name) for i, name in labels]


def render(cal, theme):
    t = THEMES[theme]
    weeks = cal["weeks"]
    total = cal["totalContributions"]
    cell = (WIDTH - 2 * PAD - GAP * (len(weeks) - 1)) / len(weeks)
    pitch = cell + GAP
    height = GRID_TOP + ROWS * pitch - GAP + 24
    last_day = weeks[-1]["contributionDays"][-1]["date"]
    noun = "contribution" if total == 1 else "contributions"

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height:.0f}" '
        f'viewBox="0 0 {WIDTH} {height:.0f}" role="img" '
        f'aria-label="{total:,} {noun} in the last year">',
        f"<title>{total:,} {noun} in the last year</title>",
        "<style>"
        ".w{animation:in .5s ease-out both}"
        "@keyframes in{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}"
        ".now{animation:pulse 2.2s ease-in-out infinite}"
        "@keyframes pulse{50%{opacity:.35}}"
        "@media (prefers-reduced-motion:reduce){.w,.now{animation:none}}"
        "</style>",
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1:.0f}" rx="10" '
        f'fill="{t["card"]}" stroke="{t["border"]}"/>',
        f'<text x="{PAD}" y="40" font-family="{FONT}" font-size="14">'
        f'<tspan fill="{t["text"]}" font-weight="600">{total:,}</tspan>'
        f'<tspan fill="{t["muted"]}"> {noun} in the last year</tspan></text>',
    ]

    # Legend, right-aligned on the header row.
    sq, lx = 10, WIDTH - PAD
    lx -= 4 * 7  # width of "more"
    out.append(f'<text x="{lx}" y="39" font-family="{FONT}" font-size="11" fill="{t["muted"]}">more</text>')
    lx -= 6
    for color in reversed(t["cells"]):
        lx -= sq
        out.append(f'<rect x="{lx}" y="30" width="{sq}" height="{sq}" rx="2" fill="{color}"/>')
        lx -= 3
    out.append(
        f'<text x="{lx - 3}" y="39" font-family="{FONT}" font-size="11" fill="{t["muted"]}" '
        f'text-anchor="end">less</text>'
    )

    for x, name in month_labels(weeks, pitch):
        out.append(f'<text x="{x:.1f}" y="72" font-family="{FONT}" font-size="11" fill="{t["muted"]}">{name}</text>')

    for i, week in enumerate(weeks):
        x = PAD + i * pitch
        out.append(f'<g class="w" style="animation-delay:{i * 0.018:.3f}s">')
        for day in week["contributionDays"]:
            row = date.fromisoformat(day["date"]).isoweekday() % 7  # sunday = 0
            y = GRID_TOP + row * pitch
            level = LEVELS.index(day["contributionLevel"])
            today = day["date"] == last_day
            extra = f' class="now" stroke="{t["accent"]}" stroke-width="1.5"' if today else ""
            out.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{cell:.2f}" height="{cell:.2f}" rx="2.5" '
                f'fill="{t["cells"][level]}"{extra}>'
                f'<title>{day["contributionCount"]} on {day["date"]}</title></rect>'
            )
        out.append("</g>")

    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "dist"
    login = os.environ.get("GH_USER", "areebhirani-beep")
    cal = fetch(login, os.environ["GITHUB_TOKEN"])
    os.makedirs(out_dir, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(out_dir, f"graph-{theme}.svg"), "w") as f:
            f.write(render(cal, theme))
    print(f"{cal['totalContributions']} contributions, {len(cal['weeks'])} weeks -> {out_dir}")


if __name__ == "__main__":
    main()
