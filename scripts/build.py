#!/usr/bin/env python3
"""Render the bento profile card into dist/bento-light.svg and dist/bento-dark.svg.

python3 scripts/build.py                 render from scripts/data.json
python3 scripts/build.py --fetch-scores  refresh yearly contribution totals via gh first (CI does this daily)
python3 scripts/build.py --fetch-repos   refresh repo/language counts too; run locally, it needs private repo access
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import math
import subprocess
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "scripts" / "data.json"
ICONS = ROOT / "assets" / "icons"
FONTS = ROOT / "assets" / "fonts"
DIST = ROOT / "dist"

W, H, GAP, RADIUS = 880, 676, 12, 22
COL = (W - 3 * GAP) / 4
ROWS = [(0, 220), (232, 236), (480, 196)]
SANS = "'Be Vietnam Pro', -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace"

THEMES = {
    "light": {
        "card": "#ffffff",
        "tile": "#f4f6fa",
        "border": "#e5e8ef",
        "fg": "#0f172a",
        "muted": "#64748b",
        "accent": ("#7c3aed", "#0891b2"),
        "live": "#10b981",
        "hero": "#f6f4ff",
        "blobs": (("#c4b5fd", 0.9), ("#99f6e4", 0.8), ("#fbcfe8", 0.9)),
        "chip": 0.7,
        "grain": 0.05,
    },
    "dark": {
        "card": "#0e121b",
        "tile": "#161b26",
        "border": "#232a38",
        "fg": "#eef1f7",
        "muted": "#8a93a6",
        "accent": ("#a78bfa", "#22d3ee"),
        "live": "#34d399",
        "hero": "#0b0f1c",
        "blobs": (("#7c3aed", 0.75), ("#0891b2", 0.65), ("#db2777", 0.5)),
        "chip": 0.08,
        "grain": 0.1,
    },
}
# Logos whose brand colours disappear on a dark background.
DARK_RECOLOR = {
    "amazonwebservices-original-wordmark": {"#252f3e": "#e6edf3"},
    "mysql-original": {"#00618A": "#5fa8d3"},
}
LANG_COLORS = {
    "TypeScript": "#3178c6",
    "Python": "#ffd43b",
    "Vue": "#41b883",
    "Go": "#00add8",
    "Ruby": "#cc342d",
    "JavaScript": "#a371f7",
    "Dart": "#00b4ab",
    "Swift": "#f05138",
}
NON_SKILL_LANGUAGES = {"HTML", "CSS", "SCSS", "Dockerfile", "Makefile", "Shell", "Go Template", "Mustache", "Bicep", "Jupyter Notebook"}


def col_x(c: int) -> float:
    return c * (COL + GAP)


def span(n: int) -> float:
    return n * COL + (n - 1) * GAP


def text(
    x: float, y: float, s: str, size: int, fill: str, weight: int = 400, anchor: str = "start", mono: bool = False, extra: str = ""
) -> str:
    cls = "m" if mono else "s"
    return (
        f'<text class="{cls}" x="{x:g}" y="{y:g}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
        f'text-anchor="{anchor}"{extra}>{escape(s)}</text>'
    )


def card(x: float, y: float, w: float, h: float, t: dict) -> str:
    return f'<rect x="{x + 0.5:g}" y="{y + 0.5:g}" width="{w - 1:g}" height="{h - 1:g}" rx="{RADIUS}" fill="{t["card"]}" stroke="{t["border"]}"/>'


def label(x: float, y: float, s: str, t: dict) -> str:
    return text(x + 22, y + 34, s.upper(), 11, t["muted"], 500, mono=True)


def pulse(cx: float, cy: float, color: str, r: float = 4) -> str:
    return (
        f'<circle cx="{cx:g}" cy="{cy:g}" r="{r}" fill="{color}" fill-opacity="0.5">'
        f'<animate attributeName="r" values="{r};{r * 4}" dur="2.4s" repeatCount="indefinite"/>'
        f'<animate attributeName="fill-opacity" values="0.5;0" dur="2.4s" repeatCount="indefinite"/></circle>'
        f'<circle cx="{cx:g}" cy="{cy:g}" r="{r}" fill="{color}"/>'
    )


def font_css() -> str:
    rules = []
    for font in json.loads((FONTS / "fonts.json").read_text()):
        data = base64.b64encode((FONTS / font["file"]).read_bytes()).decode()
        rules.append(
            f"@font-face{{font-family:'{font['family']}';font-weight:{font['weight']};"
            f"src:url(data:font/woff2;base64,{data}) format('woff2');unicode-range:{font['unicode_range']}}}"
        )
    return "".join(rules) + f".s{{font-family:{SANS}}}.m{{font-family:{MONO};letter-spacing:.08em}}"


def icon_uri(name: str, theme: str) -> str:
    src = (ICONS / f"{name}.svg").read_text()
    if theme == "dark":
        for old, new in DARK_RECOLOR.get(name, {}).items():
            src = src.replace(old, new)
    return "data:image/svg+xml;base64," + base64.b64encode(src.encode()).decode()


def rotating_words(words: list[str], x: float, y: float, hold: float = 2.6, fade: float = 0.35) -> str:
    """Cycle through words with a cross-fade; static renders show the first word."""
    period = hold * len(words)
    parts = []
    for i, word in enumerate(words):
        start, end = i * hold, (i + 1) * hold
        if i == 0:
            values, times = [1, 1, 0, 0, 1], [0, end - fade, end, period - fade, period]
        elif i == len(words) - 1:
            values, times = [0, 0, 1, 1, 0], [0, start - fade, start, period - fade, period]
        else:
            values, times = [0, 0, 1, 1, 0, 0], [0, start - fade, start, end - fade, end, period]
        anim = (
            f'<animate attributeName="opacity" values="{";".join(map(str, values))}" '
            f'keyTimes="{";".join(f"{v / period:.4f}" for v in times)}" dur="{period:g}s" repeatCount="indefinite"/>'
        )
        parts.append(f'<g opacity="{1 if i == 0 else 0}">{text(x, y, word, 16, "url(#accent-text)", 600)}{anim}</g>')
    return "".join(parts)


def hero(data: dict, t: dict) -> str:
    w, h = span(3), ROWS[0][1]
    blobs = [
        ((110, 30, 190), "0 0;70 30;-20 50;0 0", 19),
        ((430, 210, 210), "0 0;-80 -30;40 -50;0 0", 23),
        ((620, 20, 160), "0 0;-50 60;-90 10;0 0", 27),
    ]
    gradients = "".join(
        f'<radialGradient id="blob{i}"><stop offset="0" stop-color="{color}" stop-opacity="{alpha}"/>'
        f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>'
        for i, (color, alpha) in enumerate(t["blobs"])
    )
    circles = "".join(
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#blob{i})">'
        f'<animateTransform attributeName="transform" type="translate" values="{path}" dur="{dur}s" repeatCount="indefinite"/></circle>'
        for i, ((cx, cy, r), path, dur) in enumerate(blobs)
    )
    chip_w = max(len(word) for word in data["building"]) * 9.6 + 32
    return (
        f'<defs>{gradients}<clipPath id="hero-clip"><rect width="{w:g}" height="{h}" rx="{RADIUS}"/></clipPath></defs>'
        f'<g clip-path="url(#hero-clip)"><rect width="{w:g}" height="{h}" fill="{t["hero"]}"/>{circles}'
        f'<rect width="{w:g}" height="{h}" filter="url(#grain)" opacity="{t["grain"]}"/></g>'
        f'<rect x="0.5" y="0.5" width="{w - 1:g}" height="{h - 1}" rx="{RADIUS}" fill="none" stroke="{t["border"]}"/>'
        + text(30, 54, "HELLO, I'M", 12, t["fg"], 500, mono=True, extra=' fill-opacity="0.65"')
        + text(28, 108, data["name"], 44, t["fg"], 800)
        + text(30, 144, data["headline"], 18, t["fg"], 500, extra=' fill-opacity="0.8"')
        + text(30, 189, "BUILDING", 12, t["fg"], 500, mono=True, extra=' fill-opacity="0.65"')
        + f'<rect x="108" y="166" width="{chip_w:g}" height="34" rx="17" fill="#ffffff" fill-opacity="{t["chip"]}" stroke="{t["border"]}"/>'
        + rotating_words(data["building"], 124, 189)
    )


def location(data: dict, t: dict) -> str:
    x, (y, h) = col_x(3), ROWS[0]
    loc = data["location"]
    return (
        card(x, y, COL, h, t)
        + f'<rect x="{x + 1:g}" y="{y + 48}" width="{COL - 2:g}" height="84" fill="url(#dots)" mask="url(#fade-down)"/>'
        + label(x, y, "Based in", t)
        + pulse(x + COL - 52, y + 88, t["live"], 5)
        + text(x + 22, y + 166, loc["city"], 32, t["fg"], 800)
        + text(x + 22, y + 192, f"{loc['country']} · {loc['tz']}", 13, t["muted"])
    )


def stack(data: dict, theme: str, t: dict) -> str:
    x, (y, h) = col_x(0), ROWS[1]
    w = span(2)
    tile, gap = 46, 12
    per_row = max(len(row) for row in data["stack"])
    x0 = x + (w - (per_row * tile + (per_row - 1) * gap)) / 2
    tiles = []
    for r, row in enumerate(data["stack"]):
        for c, (icon, _name) in enumerate(row):
            tx, ty = x0 + c * (tile + gap), y + 58 + r * (tile + gap)
            tiles.append(
                f'<rect x="{tx + 0.5:g}" y="{ty + 0.5:g}" width="{tile - 1}" height="{tile - 1}" rx="12" fill="{t["tile"]}" stroke="{t["border"]}"/>'
                f'<image href="{icon_uri(icon, theme)}" x="{tx + 10:g}" y="{ty + 10:g}" width="26" height="26"/>'
            )
    count = sum(len(row) for row in data["stack"])
    return (
        card(x, y, w, h, t)
        + label(x, y, "Stack", t)
        + text(x + w - 22, y + 34, f"{count} TOOLS", 11, t["muted"], 500, "end", mono=True)
        + "".join(tiles)
    )


def experience(data: dict, t: dict) -> str:
    x, (y, h) = col_x(2), ROWS[1]
    entries = data["experience"]
    first, step = y + 76, 58
    dot_x = x + 29
    parts = [
        card(x, y, COL, h, t),
        label(x, y, "Experience", t),
        f'<line x1="{dot_x:g}" y1="{first}" x2="{dot_x:g}" y2="{first + step * (len(entries) - 1)}" stroke="{t["border"]}" stroke-width="2"/>',
    ]
    for i, entry in enumerate(entries):
        ey = first + i * step
        if entry.get("current"):
            parts.append(pulse(dot_x, ey, t["live"]))
        else:
            parts.append(f'<circle cx="{dot_x:g}" cy="{ey}" r="4" fill="{t["card"]}" stroke="{t["muted"]}" stroke-width="2"/>')
        parts.append(
            text(x + 46, ey + 5, entry["company"], 15, t["fg"], 600)
            + text(x + 46, ey + 25, f"{entry['role']} · {entry['period']}", 12, t["muted"])
        )
    return "".join(parts)


def numbers(data: dict, scores: dict[int, int], t: dict) -> str:
    x, (y, h) = col_x(3), ROWS[1]
    years = dt.date.today().year - data["career_start"]
    return (
        card(x, y, COL, h, t)
        + label(x, y, "By the numbers", t)
        + text(x + 21, y + 104, f"{sum(scores.values()):,}", 38, "url(#accent-text)", 800)
        + text(x + 22, y + 128, f"contributions since {min(scores)}", 12, t["muted"])
        + f'<line x1="{x + 22:g}" y1="{y + 152.5}" x2="{x + COL - 22:g}" y2="{y + 152.5}" stroke="{t["border"]}"/>'
        + text(x + 22, y + 192, str(data["repos"]), 26, t["fg"], 700)
        + text(x + 22, y + 212, "repositories", 12, t["muted"])
        + text(x + 112, y + 192, f"{years}+", 26, t["fg"], 700)
        + text(x + 112, y + 212, "years building", 12, t["muted"])
    )


def activity(scores: dict[int, int], t: dict) -> str:
    x, (y, h) = col_x(0), ROWS[2]
    w = span(2)
    today = dt.date.today()
    years = sorted(scores)
    best = max(scores.values())
    bar_w, top, bottom = 34, y + 74, y + 152
    gap = (w - 44 - bar_w * len(years)) / max(1, len(years) - 1)
    splines = 'calcMode="spline" keySplines="0 0 1 1;0.2 0.8 0.2 1"'
    parts = [
        card(x, y, w, h, t),
        label(x, y, "Contributions / year", t),
        text(x + w - 22, y + 34, f"UPDATED {today:%b} {today.day}".upper(), 11, t["muted"], 500, "end", mono=True),
    ]
    for i, year in enumerate(years):
        bx = x + 22 + i * (bar_w + gap)
        bh = max(3, round(scores[year] / best * (bottom - top)))
        current = year == today.year
        delay, grow = 0.15 + i * 0.07, 0.7
        dur = delay + grow
        key = f"0;{delay / dur:.3f};1"
        parts.append(
            f'<rect x="{bx:.1f}" y="{bottom - bh}" width="{bar_w}" height="{bh}" rx="7" fill="url(#accent-bar)" fill-opacity="{1 if current else 0.45}">'
            f'<animate attributeName="height" values="0;0;{bh}" keyTimes="{key}" {splines} dur="{dur:.2f}s" fill="freeze"/>'
            f'<animate attributeName="y" values="{bottom};{bottom};{bottom - bh}" keyTimes="{key}" {splines} dur="{dur:.2f}s" fill="freeze"/></rect>'
            + text(
                bx + bar_w / 2,
                bottom - bh - 7,
                f"{scores[year]:,}",
                11,
                t["fg"] if current else t["muted"],
                600 if current else 400,
                "middle",
            )
            + text(bx + bar_w / 2, bottom + 22, str(year), 11, t["fg"] if current else t["muted"], 500, "middle", mono=True)
        )
    return "".join(parts)


def languages(data: dict, t: dict) -> str:
    x, (y, h) = col_x(2), ROWS[2]
    langs = sorted(((k, v) for k, v in data["languages"].items() if k not in NON_SKILL_LANGUAGES), key=lambda kv: -kv[1])[:6]
    total = sum(v for _, v in langs)
    cx, cy, r = x + 62, y + 116, 36
    circumference = 2 * math.pi * r
    parts = [card(x, y, COL, h, t), label(x, y, "Languages", t)]
    offset = 0.0
    for lang, count in langs:
        length = circumference * count / total
        parts.append(
            f'<circle cx="{cx:g}" cy="{cy}" r="{r}" fill="none" stroke="{LANG_COLORS.get(lang, t["muted"])}" stroke-width="14" '
            f'stroke-dasharray="{max(0.5, length - 3):.2f} {circumference:.2f}" stroke-dashoffset="{-offset:.2f}" '
            f'transform="rotate(-90 {cx:g} {cy})"/>'
        )
        offset += length
    parts.append(
        text(cx, cy + 4, str(len(langs)), 20, t["fg"], 800, "middle") + text(cx, cy + 18, "LANGS", 9, t["muted"], 500, "middle", mono=True)
    )
    for i, (lang, _count) in enumerate(langs):
        ly = y + 68 + i * 21
        parts.append(
            f'<circle cx="{x + 124:g}" cy="{ly - 4}" r="4" fill="{LANG_COLORS.get(lang, t["muted"])}"/>'
            + text(x + 134, ly, lang, 12, t["fg"], 500)
        )
    return "".join(parts)


def now(data: dict, t: dict) -> str:
    x, (y, h) = col_x(3), ROWS[2]
    lines = "".join(text(x + 22, y + 74 + i * 22, line, 15, t["fg"], 500) for i, line in enumerate(data["now"]) if line)
    return card(x, y, COL, h, t) + label(x, y, "Now", t) + pulse(x + COL - 30, y + 30, t["live"]) + lines


def build_bento(data: dict, scores: dict[int, int], theme: str) -> str:
    t = THEMES[theme]
    a, b = t["accent"]
    defs = (
        f"<style>{font_css()}</style>"
        f'<linearGradient id="accent-text" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>'
        f'<linearGradient id="accent-bar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>'
        '<filter id="grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch"/>'
        '<feColorMatrix type="saturate" values="0"/></filter>'
        f'<pattern id="dots" width="14" height="14" patternUnits="userSpaceOnUse"><circle cx="7" cy="7" r="1.2" fill="{t["muted"]}" fill-opacity="0.45"/></pattern>'
        '<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        '<mask id="fade-down" maskContentUnits="objectBoundingBox"><rect width="1" height="1" fill="url(#fade)"/></mask>'
    )
    body = (
        hero(data, t)
        + location(data, t)
        + stack(data, theme, t)
        + experience(data, t)
        + numbers(data, scores, t)
        + activity(scores, t)
        + languages(data, t)
        + now(data, t)
    )
    title = (
        f"{data['name']}: {data['headline']}, based in {data['location']['city']}. "
        f"{sum(scores.values()):,} contributions since {min(scores)}, {data['repos']} repositories."
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="{escape(title)}"><title>{escape(title)}</title><defs>{defs}</defs>{body}</svg>\n'
    )


def gh_graphql(query: str, *flags: str) -> str:
    return subprocess.run(["gh", "api", "graphql", *flags, "-f", f"query={query}"], check=True, capture_output=True, text=True).stdout


def fetch_scores(login: str) -> dict[str, int]:
    created = json.loads(gh_graphql(f'{{user(login:"{login}"){{createdAt}}}}'))["data"]["user"]["createdAt"]
    years = range(int(created[:4]), dt.date.today().year + 1)
    fields = " ".join(
        f'y{y}: contributionsCollection(from:"{y}-01-01T00:00:00Z", to:"{y}-12-31T23:59:59Z"){{contributionCalendar{{totalContributions}}}}'
        for y in years
    )
    user = json.loads(gh_graphql(f'{{user(login:"{login}"){{{fields}}}}}'))["data"]["user"]
    return {str(y): user[f"y{y}"]["contributionCalendar"]["totalContributions"] for y in years}


def fetch_repos(login: str) -> tuple[int, dict[str, int]]:
    """Count contributed repos, and per language the repos where it makes up at least 10% of the code."""
    query = (
        'query($endCursor:String){user(login:"%s"){repositoriesContributedTo(first:100, after:$endCursor, '
        "includeUserRepositories:true, contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY]){pageInfo{hasNextPage endCursor} "
        "nodes{languages(first:10, orderBy:{field:SIZE,direction:DESC}){totalSize edges{size node{name}}}}}}}" % login
    )
    out = gh_graphql(query, "--paginate", "--jq", ".data.user.repositoriesContributedTo.nodes[].languages")
    repos, counts = 0, {}
    for line in filter(None, out.splitlines()):
        langs = json.loads(line)
        repos += 1
        for edge in langs["edges"]:
            if langs["totalSize"] and edge["size"] / langs["totalSize"] >= 0.10:
                name = edge["node"]["name"]
                counts[name] = counts.get(name, 0) + 1
    return repos, dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fetch-scores", action="store_true")
    parser.add_argument("--fetch-repos", action="store_true")
    args = parser.parse_args()

    data = json.loads(DATA.read_text())
    if args.fetch_scores or args.fetch_repos:
        data["contributions"] = fetch_scores(data["login"])
    if args.fetch_repos:
        data["repos"], data["languages"] = fetch_repos(data["login"])
    if args.fetch_scores or args.fetch_repos:
        DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    scores = {int(y): v for y, v in data["contributions"].items()}
    DIST.mkdir(exist_ok=True)
    for theme in THEMES:
        content = build_bento(data, scores, theme)
        (DIST / f"bento-{theme}.svg").write_text(content)
        print(f"dist/bento-{theme}.svg  {len(content) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
