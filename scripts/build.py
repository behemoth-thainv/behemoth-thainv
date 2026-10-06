#!/usr/bin/env python3
"""Render the retro profile cards (SVG) into dist/.

python3 scripts/build.py                 render from scripts/data.json
python3 scripts/build.py --fetch-scores  refresh yearly contribution totals via gh first (CI does this daily)
python3 scripts/build.py --fetch-repos   refresh repo/language counts too; run locally, it needs private repo access
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "scripts" / "data.json"
ICONS = ROOT / "scripts" / "icons.json"
DIST = ROOT / "dist"

W = 880
ADV = 6  # glyph advance in font pixels (5px glyph + 1px gap)

BG = "#0b0b16"
PANEL = "#15152a"
LINE = "#2c2c4a"
WHITE = "#f4f4ff"
DIM = "#7d84a8"
GREEN = "#3dff8f"
YELLOW = "#ffe14d"
AMBER = "#ffb000"
PINK = "#ff3e9a"
CYAN = "#2de2e6"
RED = "#ff4d4d"
RAINBOW = [RED, AMBER, YELLOW, GREEN, CYAN, "#6c8cff", "#c86bff"]
LANG_COLORS = {
    "TypeScript": "#3d8eff",
    "Python": "#ffd43b",
    "Vue": "#41d18f",
    "Go": "#2de2e6",
    "Ruby": "#ff4d4d",
    "JavaScript": "#f7e45a",
    "Dart": "#22c7bd",
    "Swift": "#ff7a45",
}
NON_SKILL_LANGUAGES = {"HTML", "CSS", "SCSS", "Dockerfile", "Makefile", "Shell", "Go Template", "Mustache", "Bicep", "Jupyter Notebook"}

# 5x7 bitmap font, one string per row.
FONT = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "D": ["###..", "#..#.", "#...#", "#...#", "#...#", "#..#.", "###.."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".####"],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": [".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "J": ["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": ["..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."],
    ".": [".....", ".....", ".....", ".....", ".....", ".##..", ".##.."],
    ",": [".....", ".....", ".....", ".....", ".##..", "..#..", ".#..."],
    ":": [".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."],
    "-": [".....", ".....", ".....", "#####", ".....", ".....", "....."],
    "_": [".....", ".....", ".....", ".....", ".....", ".....", "#####"],
    "/": [".....", "....#", "...#.", "..#..", ".#...", "#....", "....."],
    "(": ["...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."],
    ")": [".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."],
    "!": ["..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."],
    "?": [".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."],
    "&": [".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"],
    "'": ["..#..", "..#..", ".#...", ".....", ".....", ".....", "....."],
    "+": [".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."],
    "@": [".###.", "#...#", "....#", ".##.#", "#.#.#", "#.#.#", ".###."],
    "#": [".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."],
    "·": [".....", ".....", ".....", "..#..", ".....", ".....", "....."],
    "▶": ["#....", "##...", "###..", "####.", "###..", "##...", "#...."],
    "◀": ["....#", "...##", "..###", ".####", "..###", "...##", "....#"],
    "♥": [".....", ".#.#.", "#####", "#####", ".###.", "..#..", "....."],
    "★": ["..#..", "..#..", "#####", ".###.", ".###.", ".#.#.", "#...#"],
}

# 16x16 mascot: a small horned behemoth. Left half only; the right half is mirrored.
MASCOT_LEFT = [
    ".K......",
    "KHK.....",
    "KHHK.KKK",
    ".KHKKLLL",
    "..KLLPPP",
    ".KLPPPPP",
    ".KPWWWPP",
    "KPPWEEPP",
    "KPPWEEPP",
    "KPRPPPPP",
    "KPPPKWKK",
    ".KPPPPPP",
    ".KDPPPPP",
    "..KDDDDD",
    "..KDDKKK",
    "..KKKK..",
]
MASCOT = [row + row[::-1] for row in MASCOT_LEFT]
MASCOT_COLORS = {
    "K": "#1a0f2e",
    "H": "#f5e6c8",
    "L": "#c4a6ff",
    "P": "#8b5cf6",
    "D": "#5b2fb8",
    "W": "#ffffff",
    "E": "#1a0f2e",
    "R": "#ff7aa8",
}
# Closed eyes, drawn over the open ones while blinking.
MASCOT_BLINK = (
    ["." * 16] * 6
    + [
        "...PPP....PPP...",
        "...PPP....PPP...",
        "...KKK....KKK...",
    ]
    + ["." * 16] * 7
)

INVADERS = {
    "squid": (
        ["...##...", "..####..", ".######.", "##.##.##", "########", "..#..#..", ".#.##.#.", "#.#..#.#"],
        ["...##...", "..####..", ".######.", "##.##.##", "########", ".#.##.#.", "#......#", ".#....#."],
    ),
    "crab": (
        ["..#.....#..", "...#...#...", "..#######..", ".##.###.##.", "###########", "#.#######.#", "#.#.....#.#", "...##.##..."],
        ["..#.....#..", "#..#...#..#", "#.#######.#", "###.###.###", "###########", ".#########.", "..#.....#..", ".#.......#."],
    ),
    "octopus": (
        ["....####....", ".##########.", "############", "###..##..###", "############", "...##..##...", "..##.##.##..", "##........##"],
        ["....####....", ".##########.", "############", "###..##..###", "############", "..###..###..", ".##..##..##.", "..##....##.."],
    ),
}


def runs(rows: list[str], key: str = "#") -> str:
    d = []
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            if row[x] != key:
                x += 1
                continue
            n = 1
            while x + n < len(row) and row[x + n] == key:
                n += 1
            d.append(f"M{x} {y}h{n}v1h-{n}z")
            x += n
    return "".join(d)


def sprite(rows: list[str], colors: dict[str, str]) -> str:
    return "".join(
        f'<path fill="{color}" shape-rendering="crispEdges" d="{d}"/>' for key, color in colors.items() if (d := runs(rows, key))
    )


def text_width(s: str, scale: int) -> int:
    return (len(s) * ADV - 1) * scale


def align(x: float, width: int, anchor: str) -> int:
    if anchor == "middle":
        return round(x - width / 2)
    if anchor == "end":
        return round(x - width)
    return round(x)


def discrete(attr: str, values: list, times: list[float], dur: float, repeat: bool = False) -> str:
    tail = 'repeatCount="indefinite"' if repeat else 'fill="freeze"'
    return (
        f'<animate attributeName="{attr}" values="{";".join(map(str, values))}" '
        f'keyTimes="{";".join(f"{t:.4f}" for t in times)}" dur="{dur:.3f}s" calcMode="discrete" {tail}/>'
    )


def blink(period: float = 1.0) -> str:
    return discrete("opacity", [1, 0], [0, 0.5], period, repeat=True)


def hidden_until(t: float) -> str:
    """Hide the parent for the first t seconds after load; static renders still show it."""
    return f'<set attributeName="opacity" to="0" begin="0s" dur="{t:.2f}s"/>'


def ok_line(label: str, width: int = 38) -> str:
    return f"{label} {'.' * (width - len(label) - 4)} OK"


class Svg:
    def __init__(self, width: int, height: int, title: str):
        self.w, self.h, self.title = width, height, title
        self.chars: set[str] = set()
        self.defs: list[str] = []
        self.body: list[str] = []
        self._n = 0

    def uid(self, prefix: str) -> str:
        self._n += 1
        return f"{prefix}{self._n}"

    def add(self, *parts: str) -> None:
        self.body.extend(parts)

    def text(self, s: str, x: float, y: float, scale: int = 2, fill: str = WHITE, anchor: str = "start", inner: str = "") -> str:
        s = s.upper()
        missing = set(s) - FONT.keys() - {" "}
        if missing:
            raise ValueError(f"no glyph for {sorted(missing)} in {s!r}")
        self.chars.update(s)
        x = align(x, text_width(s, scale), anchor)
        uses = "".join(f'<use href="#g{ord(c):x}" x="{i * ADV}"/>' for i, c in enumerate(s) if c != " ")
        return f'<g transform="translate({x} {y}) scale({scale})" fill="{fill}">{uses}{inner}</g>'

    def reveal(self, content: str, x: int, y: int, w: int, h: int, start: float, steps: int, step: float, vertical: bool = False) -> str:
        """Clip content and grow the clip in discrete steps (typing / filling effect)."""
        cid = self.uid("rv")
        dur = start + steps * step
        sizes = [0] + [round((w if not vertical else h) * i / steps) for i in range(1, steps + 1)]
        times = [0] + [(start + (i - 1) * step) / dur for i in range(1, steps + 1)]
        if vertical:
            anim = discrete("height", sizes, times, dur) + discrete("y", [y + h - v for v in sizes], times, dur)
        else:
            anim = discrete("width", sizes, times, dur)
        self.defs.append(f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}">{anim}</rect></clipPath>')
        return f'<g clip-path="url(#{cid})">{content}</g>'

    def typed(self, s: str, x: float, y: float, scale: int, fill: str, start: float, step: float = 0.02, anchor: str = "start") -> str:
        width = text_width(s, scale)
        x = align(x, width, anchor)
        glyphs = self.text(s, x, y, scale, fill)
        return self.reveal(glyphs, x, y - scale, len(s) * ADV * scale, 9 * scale, start, len(s), step)

    def scanlines(self, x: int, y: int, w: int, h: int, opacity: float = 0.22) -> str:
        pid = self.uid("scan")
        self.defs.append(
            f'<pattern id="{pid}" width="4" height="4" patternUnits="userSpaceOnUse">'
            f'<rect y="2" width="4" height="2" fill="#000" fill-opacity="{opacity}"/></pattern>'
        )
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#{pid})" pointer-events="none"/>'

    def render(self) -> str:
        glyphs = "".join(
            f'<path id="g{ord(c):x}" shape-rendering="crispEdges" d="{runs(FONT[c])}"/>' for c in sorted(self.chars) if c != " "
        )
        title = escape(self.title)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
            f'role="img" aria-label="{title}"><title>{title}</title>'
            f"<defs>{glyphs}{''.join(self.defs)}</defs>{''.join(self.body)}</svg>\n"
        )


def pixel_box(x: int, y: int, w: int, h: int, border: str = WHITE, fill: str = BG, b: int = 4) -> str:
    """NES-style dialog box: solid border with notched pixel corners."""
    rects = [
        (x + b, y + b, w - 2 * b, h - 2 * b, fill),
        (x + 2 * b, y, w - 4 * b, b, border),
        (x + 2 * b, y + h - b, w - 4 * b, b, border),
        (x, y + 2 * b, b, h - 4 * b, border),
        (x + w - b, y + 2 * b, b, h - 4 * b, border),
        (x + b, y + b, b, b, border),
        (x + w - 2 * b, y + b, b, b, border),
        (x + b, y + h - 2 * b, b, b, border),
        (x + w - 2 * b, y + h - 2 * b, b, b, border),
    ]
    return "".join(
        f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" fill="{c}" shape-rendering="crispEdges"/>' for rx, ry, rw, rh, c in rects
    )


def card(svg: Svg, title: str | None, top: int = 14) -> tuple[int, int]:
    """Draw the card frame (and its title tab); return the inner content origin."""
    svg.add(pixel_box(2, top, svg.w - 4, svg.h - top - 2))
    if title:
        tw = text_width(title, 2)
        svg.add(pixel_box(24, top - 12, tw + 32, 30), svg.text(title, 40, top - 4, 2, YELLOW))
    return 2, top


def finish_card(svg: Svg, top: int = 14) -> None:
    svg.add(svg.scanlines(6, top + 4, svg.w - 12, svg.h - top - 10, 0.18))


def mascot(svg: Svg, x: int, y: int, scale: int, bob: int = 1) -> str:
    blink_layer = (
        f'<g opacity="0">{sprite(MASCOT_BLINK, MASCOT_COLORS)}{discrete("opacity", [0, 1, 0], [0, 0.9, 0.95], 4.2, repeat=True)}</g>'
    )
    bob_anim = (
        f'<animateTransform attributeName="transform" type="translate" values="0 0;0 {-bob * scale}" '
        f'dur="0.9s" calcMode="discrete" repeatCount="indefinite"/>'
    )
    return (
        f'<g transform="translate({x} {y})"><g>{bob_anim}'
        f'<g transform="scale({scale})">{sprite(MASCOT, MASCOT_COLORS)}{blink_layer}</g></g></g>'
    )


def invader(kind: str, x: int, y: int, scale: int, color: str) -> str:
    a, b = INVADERS[kind]
    frame_a = f"<g>{sprite(a, {'#': color})}{discrete('opacity', [1, 0], [0, 0.5], 0.8, repeat=True)}</g>"
    frame_b = f'<g opacity="0">{sprite(b, {"#": color})}{discrete("opacity", [0, 1], [0, 0.5], 0.8, repeat=True)}</g>'
    return f'<g transform="translate({x} {y}) scale({scale})">{frame_a}{frame_b}</g>'


# ---------------------------------------------------------------- cards


def build_hero(data: dict, scores: dict[int, int]) -> str:
    year = dt.date.today().year
    H = 470
    sx, sy, sw, sh = 36, 30, 808, 380
    boot_end = 3.4
    svg = Svg(W, H, f"{data['handle']}: {data['class'].lower()} and {data['rank'].lower()}, retro arcade title screen")

    svg.defs.append(
        '<linearGradient id="bezel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3b3b47"/>'
        '<stop offset="1" stop-color="#17171d"/></linearGradient>'
        '<radialGradient id="screen" cx="50%" cy="45%" r="70%"><stop offset="0" stop-color="#151d38"/>'
        '<stop offset="1" stop-color="#04050b"/></radialGradient>'
        '<radialGradient id="vignette" cx="50%" cy="50%" r="72%"><stop offset="0.62" stop-color="#000" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#000" stop-opacity="0.75"/></radialGradient>'
        '<linearGradient id="glass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0.09"/>'
        '<stop offset="0.35" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        '<linearGradient id="roll" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset="0.5" stop-color="#fff" stop-opacity="0.05"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        '<linearGradient id="logo" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="7"><stop offset="0" stop-color="#fff7b0"/>'
        '<stop offset="0.45" stop-color="#ffe14d"/><stop offset="0.55" stop-color="#ffb000"/><stop offset="1" stop-color="#ff6a00"/></linearGradient>'
        '<pattern id="pixgrid" width="1" height="1" patternUnits="userSpaceOnUse"><rect x="0.86" width="0.14" height="1" fill="#000" fill-opacity="0.35"/>'
        '<rect y="0.86" width="1" height="0.14" fill="#000" fill-opacity="0.35"/></pattern>'
        '<filter id="glow" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="2.4" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        f'<clipPath id="screenClip"><rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" rx="26"/></clipPath>'
    )

    svg.add(
        f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="30" fill="url(#bezel)" stroke="#000" stroke-width="2"/>',
        f'<rect x="{sx - 10}" y="{sy - 10}" width="{sw + 20}" height="{sh + 20}" rx="34" fill="#08080c"/>',
        f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" rx="26" fill="url(#screen)"/>',
    )

    # Boot sequence: only visible during the first seconds after load.
    boot_lines = [
        (f"BEHEMOTH BIOS V2.0   (C) {data['career_start']}-{year}", WHITE),
        ("CPU   CAFFEINE-POWERED CORE @ 4.2GHZ", GREEN),
        (ok_line("MEM   640K"), GREEN),
        (ok_line(f"LOAD  {data['base'].split(',')[0]}.SYS"), GREEN),
        (ok_line("LOAD  PLAYER_1.DAT"), GREEN),
        ("", GREEN),
        ("INSERTING COIN ...", YELLOW),
    ]
    boot = []
    t = 0.15
    for i, (line, color) in enumerate(boot_lines):
        if line:
            boot.append(svg.typed(line, sx + 40, sy + 34 + i * 30, 2, color, t, 0.012))
            t += len(line) * 0.012 + 0.12
    boot_cursor = (
        f'<rect x="{sx + 40 + text_width("INSERTING COIN ...", 2) + 8}" y="{sy + 34 + 6 * 30}" width="12" height="14" fill="{YELLOW}">'
        f"{blink(0.4)}</rect>"
    )
    svg.add(
        f'<g clip-path="url(#screenClip)">'
        f'<g opacity="0" filter="url(#glow)">{"".join(boot)}{boot_cursor}'
        f'<set attributeName="opacity" to="1" begin="0s" dur="{boot_end}s"/></g>'
    )

    # Title screen (the final, static state).
    best = max(scores.values())
    total = sum(scores.values())
    level = year - data["career_start"]
    title_scale = 10
    title_w = text_width(data["handle"], title_scale)
    tx, ty = round(W / 2 - title_w / 2) - 4, sy + 104

    def logo_layer(dx: int, dy: int, fill: str, extra: str = "") -> str:
        return svg.text(data["handle"], tx + dx, ty + dy, title_scale, fill, inner=extra)

    logo = logo_layer(8, 8, "#3a1060") + logo_layer(4, 4, PINK) + logo_layer(0, 0, "url(#logo)") + logo_layer(0, 0, "url(#pixgrid)")
    logo_drop = (
        f'<animateTransform attributeName="transform" type="translate" values="0 -320;0 -320;0 -160;0 -40;0 0" '
        f'keyTimes="0;{boot_end / (boot_end + 0.5):.4f};{(boot_end + 0.15) / (boot_end + 0.5):.4f};'
        f'{(boot_end + 0.3) / (boot_end + 0.5):.4f};1" dur="{boot_end + 0.5}s" calcMode="discrete" fill="freeze"/>'
    )

    hud = [
        svg.text("1UP", sx + 44, sy + 24, 2, PINK, inner=blink(0.9)),
        svg.text(f"{total:06d}", sx + 44, sy + 46, 2, WHITE),
        svg.text("HIGH SCORE", W / 2, sy + 24, 2, RED, "middle"),
        svg.text(f"{best:06d}", W / 2, sy + 46, 2, WHITE, "middle"),
        svg.text("LEVEL", sx + sw - 44, sy + 24, 2, CYAN, "end"),
        svg.text(f"{level:02d}", sx + sw - 44, sy + 46, 2, WHITE, "end"),
    ]

    march = ";".join(f"{v} 0" for v in [0, 12, 24, 36, 24, 12, 0, -12, -24, -36, -24, -12])
    row = [("squid", PINK), ("crab", CYAN), ("octopus", GREEN), ("crab", CYAN), ("squid", PINK)]
    invaders = "".join(
        invader(kind, round(W / 2 + (i - 2) * 76 - len(INVADERS[kind][0][0]) * 1.5), sy + 262, 3, color)
        for i, (kind, color) in enumerate(row)
    )
    invaders = (
        f'<g>{invaders}<animateTransform attributeName="transform" type="translate" values="{march}" '
        f'dur="4.8s" calcMode="discrete" repeatCount="indefinite"/></g>'
    )

    tagline = f"{data['base']} · CODING SINCE {data['career_start']}"
    title_screen = (
        "".join(hud)
        + svg.text(f"{data['guild']} PRESENTS", W / 2, sy + 80, 2, DIM, "middle")
        + f"<g>{logo}{logo_drop}</g>"
        + svg.typed(f"{data['class']} & {data['rank']}", W / 2, sy + 200, 3, CYAN, boot_end + 0.6, 0.03, "middle")
        + f"<g>{svg.text(tagline, W / 2, sy + 236, 2, WHITE, 'middle')}{hidden_until(boot_end + 1.6)}</g>"
        + invaders
        + svg.text("▶ PRESS START", W / 2, sy + 312, 3, YELLOW, "middle", inner=blink(1.1))
        + svg.text(f"(C) {year} {data['handle']} · ALL BUGS RESERVED", W / 2, sy + 352, 2, DIM, "middle")
    )
    svg.add(
        f'<g filter="url(#glow)">{title_screen}{hidden_until(boot_end)}</g>',
        f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="#fff" opacity="0">'
        f'<animate attributeName="opacity" values="0;0.55;0" begin="{boot_end}s" dur="0.25s"/></rect>',
        svg.scanlines(sx, sy, sw, sh),
        f'<rect x="{sx}" y="{sy - 90}" width="{sw}" height="90" fill="url(#roll)">'
        f'<animateTransform attributeName="transform" type="translate" values="0 0;0 {sh + 90}" dur="7s" repeatCount="indefinite"/></rect>',
        f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="url(#vignette)"/>',
        f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="url(#glass)"/>',
        "</g>",
    )

    chin = sy + sh + 30
    svg.add(
        svg.text(f"{data['guild']}-TRON 2000", sx + 6, chin - 7, 2, "#9a9aae"),
        "".join(f'<rect x="{W / 2 - 50 + i * 14}" y="{chin - 9}" width="8" height="18" rx="2" fill="#101015"/>' for i in range(8)),
        svg.text("PWR", W - 112, chin - 4, 1, "#9a9aae"),
        f'<circle cx="{W - 78}" cy="{chin}" r="5" fill="{GREEN}" filter="url(#glow)"/>',
    )
    return svg.render()


def build_player(data: dict, scores: dict[int, int]) -> str:
    year = dt.date.today().year
    H = 404
    svg = Svg(W, H, f"Player card: {data['handle']}, {data['class'].lower()}")
    _, top = card(svg, "PLAYER 1")

    bx, by = 36, top + 34
    svg.add(
        pixel_box(bx, by, 192, 192, LINE, PANEL, 2),
        f'<rect x="{bx + 20}" y="{by + 172}" width="152" height="4" fill="{LINE}"/>',
        mascot(svg, bx + 16, by + 12, 10),
        svg.text(data["handle"], bx + 96, by + 212, 3, WHITE, "middle"),
        svg.text(f"LV {year - data['career_start']:02d}", bx + 96, by + 246, 2, YELLOW, "middle"),
        svg.text("♥♥♥♥♥", bx + 96, by + 272, 2, RED, "middle"),
        svg.text("HP", bx + 30, by + 272, 2, DIM),
    )

    x0 = 268
    total = sum(scores.values())
    info = [
        ("CLASS", data["class"]),
        ("RANK", data["rank"]),
        ("GUILD", f"{data['guild']} · {data['guild_since']}-NOW"),
        ("BASE", data["base"]),
        ("XP", f"{total:,} CONTRIBUTIONS"),
        ("QUESTS", f"{data['repos']} REPOS"),
    ]
    for i, (label, value) in enumerate(info):
        y = top + 34 + i * 26
        svg.add(svg.text(label, x0, y, 2, CYAN), svg.text(value, x0 + 96, y, 2, WHITE))

    div_y = top + 196
    svg.add(
        "".join(f'<rect x="{x}" y="{div_y}" width="8" height="2" fill="{LINE}"/>' for x in range(x0, W - 36, 14)),
        svg.text("SKILL XP · REPOS PER LANGUAGE", x0, div_y + 16, 2, DIM),
    )

    langs = sorted(((k, v) for k, v in data["languages"].items() if k not in NON_SKILL_LANGUAGES), key=lambda kv: -kv[1])[:6]
    top_count = langs[0][1]
    seg_w, seg_gap, max_segs = 10, 2, 32
    bar_x = x0 + 132
    for i, (lang, count) in enumerate(langs):
        y = div_y + 44 + i * 22
        filled = max(1, round(count / top_count * max_segs))
        color = LANG_COLORS.get(lang, WHITE)
        empty = "".join(
            f'<rect x="{bar_x + s * (seg_w + seg_gap)}" y="{y}" width="{seg_w}" height="14" fill="{LINE}"/>' for s in range(max_segs)
        )
        full = "".join(
            f'<rect x="{bar_x + s * (seg_w + seg_gap)}" y="{y}" width="{seg_w}" height="14" fill="{color}"/>' for s in range(filled)
        )
        svg.add(
            svg.text(lang, x0, y, 2, WHITE),
            empty,
            svg.reveal(full, bar_x, y, filled * (seg_w + seg_gap), 14, 0.4 + i * 0.15, filled, 0.03),
            svg.text(str(count), bar_x + max_segs * (seg_w + seg_gap) + 10, y, 2, color),
        )
    finish_card(svg)
    return svg.render()


def build_stages(data: dict) -> str:
    H = 350
    svg = Svg(W, H, "Career stage select: " + ", ".join(f"{s['name']} {s['period']}" for s in data["stages"]))
    _, top = card(svg, "STAGE SELECT")
    stages = data["stages"]
    n = len(stages)
    xs = [round(W * (i + 0.5) / n) for i in range(n)]
    node_y = top + 86

    for i in range(n - 1):
        x_from, x_to = xs[i] + 34, xs[i + 1] - 34
        color = AMBER if i < n - 2 else PINK
        svg.add("".join(f'<rect x="{x}" y="{node_y + 22}" width="8" height="4" fill="{color}"/>' for x in range(x_from, x_to - 4, 16)))

    for i, (x, stage) in enumerate(zip(xs, stages)):
        current = i == n - 1
        border = PINK if current else GREEN
        svg.add(pixel_box(x - 26, node_y, 52, 48, border, PANEL), svg.text(str(i + 1), x, node_y + 14, 3, WHITE, "middle"))
        if current:
            svg.add(mascot(svg, x - 24, node_y - 52, 3, bob=2))
            status = svg.text("NOW PLAYING", x, node_y + 172, 2, PINK, "middle", inner=blink(1.0))
        else:
            svg.add(svg.text("★", x, node_y - 30, 3, YELLOW, "middle"))
            status = svg.text("CLEAR!", x, node_y + 172, 2, GREEN, "middle")
        svg.add(
            svg.text(f"STAGE {i + 1}", x, node_y + 66, 2, DIM, "middle"),
            svg.text(stage["period"], x, node_y + 88, 2, YELLOW, "middle"),
            svg.text(stage["name"], x, node_y + 112, 3, WHITE, "middle"),
            svg.text(stage["role"], x, node_y + 144, 2, CYAN, "middle"),
            status,
        )

    quests = "SIDE QUESTS: " + " · ".join(data["quests"])
    svg.add(svg.text(quests, W / 2, H - 42, 2, DIM, "middle"))
    finish_card(svg)
    return svg.render()


def build_inventory(data: dict, icons: dict) -> str:
    groups = data["inventory"]
    slot, pitch, row_h = 64, 96, 112
    H = 54 + len(groups) * row_h
    svg = Svg(W, H, "Inventory: " + ", ".join(label for g in groups for _, label in g["items"]))
    _, top = card(svg, "INVENTORY")

    slots = []
    for r, group in enumerate(groups):
        y = top + 30 + r * row_h
        svg.add(svg.text(group["label"], 36, y + 25, 2, CYAN))
        for c, (icon, label) in enumerate(group["items"]):
            x = 176 + c * pitch
            slots.append((x, y))
            art = icons[icon]
            colors = {str(k): color for k, color in enumerate(art["palette"])}
            svg.add(
                pixel_box(x, y, slot, slot, LINE, PANEL, 2),
                f'<g transform="translate({x + 8} {y + 8}) scale(3)">{sprite(art["rows"], colors)}</g>',
                svg.text(label, x + slot / 2, y + slot + 10, 2, WHITE, "middle"),
            )

    # Selection cursor hopping across the slots, like an RPG menu.
    corner = "M0 0h12v4h-8v8h-4z"
    brackets = "".join(
        f'<path d="{corner}" fill="{YELLOW}" transform="translate({dx} {dy}) scale({sx} {sy})"/>'
        for dx, dy, sx, sy in [(-6, -6, 1, 1), (slot + 6, -6, -1, 1), (-6, slot + 6, 1, -1), (slot + 6, slot + 6, -1, -1)]
    )
    path = ";".join(f"{x} {y}" for x, y in slots)
    svg.add(
        f'<g transform="translate({slots[0][0]} {slots[0][1]})">{brackets}'
        f'<animateTransform attributeName="transform" type="translate" values="{path}" dur="{len(slots) * 0.7:.1f}s" '
        f'calcMode="discrete" repeatCount="indefinite"/></g>'
    )
    finish_card(svg)
    return svg.render()


def build_scores(scores: dict[int, int]) -> str:
    this_year = dt.date.today().year
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    H = 346
    svg = Svg(W, H, "High scores: contributions per year, best " + ", ".join(f"{y} {v}" for y, v in ranked[:3]))
    _, top = card(svg, "HIGH SCORES")

    ox = 44
    header_y = top + 30
    svg.add(
        svg.text("RANK", ox, header_y, 2, DIM),
        svg.text("SCORE", ox + 84, header_y, 2, DIM),
        svg.text("YEAR", ox + 218, header_y, 2, DIM),
    )
    suffix = {1: "ST", 2: "ND", 3: "RD"}
    for i, (year, value) in enumerate(ranked):
        y = header_y + 26 + i * 30
        color = RAINBOW[i % len(RAINBOW)]
        row = (
            svg.text(f"{i + 1}{suffix.get(i + 1, 'TH')}", ox, y, 3, color)
            + svg.text(f"{value:06d}", ox + 84, y, 3, color)
            + svg.text(str(year), ox + 218, y, 3, color)
        )
        if year == this_year:
            row += svg.text("◀ NOW", ox + 306, y + 4, 2, PINK, inner=blink(0.8))
        svg.add(f"<g>{row}{hidden_until(0.3 + i * 0.18)}</g>")
    total_y = header_y + 26 + len(ranked) * 30 + 8
    svg.add(
        "".join(f'<rect x="{x}" y="{total_y - 10}" width="8" height="2" fill="{LINE}"/>' for x in range(ox, ox + 300, 14)),
        svg.text("TOTAL", ox, total_y + 4, 2, DIM),
        svg.text(f"{sum(scores.values()):06d}", ox + 84, total_y, 3, WHITE),
    )

    # Equalizer-style history chart.
    cx0, base_y, bar_w, gap, blocks = 470, top + 266, 36, 14, 20
    svg.add(svg.text("SCORE HISTORY", cx0, header_y, 2, DIM))
    best = max(scores.values())
    for i, (year, value) in enumerate(sorted(scores.items())):
        x = cx0 + 8 + i * (bar_w + gap)
        lit = max(1, round(value / best * blocks))
        stack = []
        for b in range(blocks):
            ratio = b / blocks
            color = (GREEN if ratio < 0.55 else YELLOW if ratio < 0.8 else RED) if b < lit else LINE
            stack.append(f'<rect x="{x}" y="{base_y - (b + 1) * 10}" width="{bar_w}" height="8" fill="{color}"/>')
        dark, glow = "".join(stack[lit:]), "".join(stack[:lit])
        svg.add(
            dark,
            svg.reveal(glow, x, base_y - lit * 10, bar_w, lit * 10, 0.4 + i * 0.12, lit, 0.035, vertical=True),
            svg.text(f"'{year % 100:02d}", x + bar_w / 2, base_y + 8, 2, YELLOW if year == this_year else WHITE, "middle"),
        )
    finish_card(svg)
    return svg.render()


def build_footer(data: dict) -> str:
    H = 168
    svg = Svg(W, H, "Thanks for visiting! Continue? Insert coin.")
    card(svg, None, top=2)
    countdown = []
    for d in range(9, -1, -1):
        i = 9 - d
        values = [1 if j == i else 0 for j in range(10)]
        times = [j / 10 for j in range(10)]
        countdown.append(
            f'<g opacity="{1 if d == 9 else 0}">{svg.text(str(d), W / 2 + 96, 72, 3, PINK)}'
            f"{discrete('opacity', values, times, 10, repeat=True)}</g>"
        )
    svg.add(
        svg.text("THANKS FOR VISITING!", W / 2, 26, 4, YELLOW, "middle"),
        svg.text("CONTINUE?", W / 2 - 18, 72, 3, WHITE, "middle"),
        "".join(countdown),
        svg.text("INSERT COIN", W / 2, 112, 2, CYAN, "middle", inner=blink(1.2)),
        svg.text(f"MADE WITH ♥ IN {data['base'].split(',')[0]}", W / 2, 140, 2, DIM, "middle"),
    )
    finish_card(svg, top=2)
    return svg.render()


# ---------------------------------------------------------------- data


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
    icons = json.loads(ICONS.read_text())
    DIST.mkdir(exist_ok=True)
    outputs = {
        "hero.svg": build_hero(data, scores),
        "player.svg": build_player(data, scores),
        "stages.svg": build_stages(data),
        "inventory.svg": build_inventory(data, icons),
        "highscores.svg": build_scores(scores),
        "footer.svg": build_footer(data),
    }
    for name, content in outputs.items():
        (DIST / name).write_text(content)
        print(f"dist/{name}  {len(content) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
