"""A small UML drawing kit on matplotlib (no PlantUML/Graphviz/Java is available here).

One data unit is one inch, so font sizes in points map directly onto the drawing. Diagrams are kept
black-and-white with a light fill so they suit the plain BITS report format and print legibly.
"""

import math
import textwrap
from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Ellipse, Polygon, Rectangle  # noqa: E402

plt.rcParams["font.family"] = ["Arial", "DejaVu Sans"]
INK = "#1b1b1b"
FILL = "#ffffff"
SOFT = "#eef2f8"
TINT = "#dde6f3"
GREY = "#5f6368"


def canvas(w: float, h: float):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def save(fig, path) -> None:
    fig.savefig(path, dpi=220, facecolor="white")
    plt.close(fig)


def text(ax, x, y, s, size=7.5, ha="center", va="center", bold=False, italic=False, color=INK, z=6, **kw):
    return ax.text(x, y, s, fontsize=size, ha=ha, va=va, fontweight="bold" if bold else "normal",
                   fontstyle="italic" if italic else "normal", color=color, zorder=z, linespacing=1.15, **kw)


def wrap(s: str, width: int) -> str:
    return "\n".join(textwrap.wrap(s, width))


def line(ax, pts, dashed=False, lw=0.9, color=INK, z=3):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=color, lw=lw, ls=(0, (4, 2.5)) if dashed else "-", zorder=z, solid_capstyle="butt")


def _unit(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy) or 1
    return dx / n, dy / n


def head(ax, tip, frm, kind="open", size=0.1):
    """Draw an arrowhead at `tip`, pointing away from `frm`. Returns where the line should end."""
    dx, dy = _unit(frm, tip)
    nx, ny = -dy, dx
    if kind == "open":
        for s in (1, -1):
            ax.plot([tip[0], tip[0] - dx * size + s * nx * size * 0.5], [tip[1], tip[1] - dy * size + s * ny * size * 0.5],
                    color=INK, lw=0.9, zorder=4, solid_capstyle="butt")
        return tip
    if kind == "filled":
        base = (tip[0] - dx * size * 1.2, tip[1] - dy * size * 1.2)
        ax.add_patch(Polygon([tip, (base[0] + nx * size * 0.5, base[1] + ny * size * 0.5),
                              (base[0] - nx * size * 0.5, base[1] - ny * size * 0.5)], closed=True, fc=INK, ec=INK, lw=0.6, zorder=4))
        return base
    if kind == "triangle":
        s2 = size * 1.5
        base = (tip[0] - dx * s2, tip[1] - dy * s2)
        ax.add_patch(Polygon([tip, (base[0] + nx * s2 * 0.5, base[1] + ny * s2 * 0.5),
                              (base[0] - nx * s2 * 0.5, base[1] - ny * s2 * 0.5)], closed=True, fc="white", ec=INK, lw=0.9, zorder=4))
        return base
    if kind in ("diamond", "diamond_filled"):
        s2 = size * 2.2
        mid = (tip[0] - dx * s2 / 2, tip[1] - dy * s2 / 2)
        base = (tip[0] - dx * s2, tip[1] - dy * s2)
        ax.add_patch(Polygon([tip, (mid[0] + nx * s2 * 0.32, mid[1] + ny * s2 * 0.32), base,
                              (mid[0] - nx * s2 * 0.32, mid[1] - ny * s2 * 0.32)], closed=True,
                             fc=INK if kind == "diamond_filled" else "white", ec=INK, lw=0.9, zorder=4))
        return base
    return tip


def arrow(ax, pts, kind="open", dashed=False, label=None, label_at=None, label_off=(0, 0.09), size=7, tail=None, lw=0.9, ha="center"):
    """Poly-line with an arrowhead at the end (and optionally a different one at the start)."""
    pts = list(pts)
    end = head(ax, pts[-1], pts[-2], kind)
    start = pts[0]
    if tail:
        start = head(ax, pts[0], pts[1], tail)
    line(ax, [start] + pts[1:-1] + [end], dashed=dashed, lw=lw)
    if label:
        lx, ly = label_at if label_at else ((pts[0][0] + pts[-1][0]) / 2, (pts[0][1] + pts[-1][1]) / 2)
        ax.text(lx + label_off[0], ly + label_off[1], label, fontsize=size, ha=ha, va="center", fontstyle="italic",
                color=INK, zorder=7, bbox=dict(fc="white", ec="none", pad=0.6))


@dataclass
class Box:
    x: float
    y: float  # bottom
    w: float
    h: float

    def T(self, f=0.5):
        return (self.x + self.w * f, self.y + self.h)

    def B(self, f=0.5):
        return (self.x + self.w * f, self.y)

    def L(self, f=0.5):
        return (self.x, self.y + self.h * f)

    def R(self, f=0.5):
        return (self.x + self.w, self.y + self.h * f)

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2


def rect(ax, x, y, w, h, fill=FILL, lw=0.9, ls="-", z=2):
    ax.add_patch(Rectangle((x, y), w, h, fc=fill, ec=INK, lw=lw, ls=ls, zorder=z))
    return Box(x, y, w, h)


def rbox(ax, cx, cy, w, h, label, fill=FILL, size=7.5, bold=False, r=0.07):
    from matplotlib.patches import FancyBboxPatch
    ax.add_patch(FancyBboxPatch((cx - w / 2 + r, cy - h / 2 + r), w - 2 * r, h - 2 * r, boxstyle=f"round,pad={r}", fc=fill, ec=INK, lw=0.9, zorder=2))
    text(ax, cx, cy, label, size=size, bold=bold)
    return Box(cx - w / 2, cy - h / 2, w, h)


def class_box(ax, x, y_top, w, name, stereo=None, attrs=(), methods=(), fs=7.0, fill=FILL, italic_name=False):
    lh = fs * 1.5 / 72
    head_h = 0.21 + (0.13 if stereo else 0)
    a_h = len(attrs) * lh + 0.07 if attrs else 0
    m_h = len(methods) * lh + 0.07 if methods else 0
    h = head_h + a_h + m_h
    y = y_top - h
    ax.add_patch(Rectangle((x, y), w, h, fc=fill, ec=INK, lw=0.9, zorder=2))
    if stereo:
        text(ax, x + w / 2, y_top - 0.10, f"«{stereo}»", size=fs - 0.5)
        text(ax, x + w / 2, y_top - 0.25, name, size=fs + 0.7, bold=True, italic=italic_name)
    else:
        text(ax, x + w / 2, y_top - head_h / 2, name, size=fs + 0.7, bold=True, italic=italic_name)
    cursor = y_top - head_h
    for block in (attrs, methods):
        if not block:
            continue
        line(ax, [(x, cursor), (x + w, cursor)], lw=0.7)
        for i, item in enumerate(block):
            text(ax, x + 0.06, cursor - 0.055 - lh * (i + 0.5), item, size=fs, ha="left")
        cursor -= len(block) * lh + 0.07
    return Box(x, y, w, h)


def note(ax, x, y, w, h, s, size=6.8):
    fold = 0.09
    ax.add_patch(Polygon([(x, y), (x + w, y), (x + w, y + h - fold), (x + w - fold, y + h), (x, y + h)], closed=True, fc="#fffbe6", ec=INK, lw=0.7, zorder=2))
    line(ax, [(x + w - fold, y + h), (x + w - fold, y + h - fold), (x + w, y + h - fold)], lw=0.6)
    text(ax, x + 0.06, y + h / 2, s, size=size, ha="left")
    return Box(x, y, w, h)


def actor(ax, x, y, label, size=7.5):
    """Stick figure with feet at (x, y)."""
    ax.add_patch(Circle((x, y + 0.5), 0.085, fc="white", ec=INK, lw=0.9, zorder=3))
    line(ax, [(x, y + 0.415), (x, y + 0.2)])
    line(ax, [(x - 0.14, y + 0.33), (x + 0.14, y + 0.33)])
    line(ax, [(x, y + 0.2), (x - 0.12, y)])
    line(ax, [(x, y + 0.2), (x + 0.12, y)])
    text(ax, x, y - 0.12, label, size=size, bold=True)
    return Box(x - 0.15, y, 0.3, 0.6)


def usecase(ax, cx, cy, w, h, label, size=7.2, fill=FILL):
    ax.add_patch(Ellipse((cx, cy), w, h, fc=fill, ec=INK, lw=0.9, zorder=2))
    text(ax, cx, cy, label, size=size)
    return Box(cx - w / 2, cy - h / 2, w, h)


def diamond(ax, cx, cy, w, h, label=None, size=6.8):
    ax.add_patch(Polygon([(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)], closed=True, fc=FILL, ec=INK, lw=0.9, zorder=2))
    if label:
        text(ax, cx, cy, label, size=size)
    return Box(cx - w / 2, cy - h / 2, w, h)


def initial(ax, cx, cy):
    ax.add_patch(Circle((cx, cy), 0.09, fc=INK, ec=INK, zorder=3))
    return Box(cx - 0.09, cy - 0.09, 0.18, 0.18)


def final(ax, cx, cy):
    ax.add_patch(Circle((cx, cy), 0.13, fc="white", ec=INK, lw=0.9, zorder=3))
    ax.add_patch(Circle((cx, cy), 0.08, fc=INK, ec=INK, zorder=4))
    return Box(cx - 0.13, cy - 0.13, 0.26, 0.26)


def bar(ax, cx, cy, w, horizontal=True):
    if horizontal:
        ax.add_patch(Rectangle((cx - w / 2, cy - 0.03), w, 0.06, fc=INK, ec=INK, zorder=3))
        return Box(cx - w / 2, cy - 0.03, w, 0.06)
    ax.add_patch(Rectangle((cx - 0.03, cy - w / 2), 0.06, w, fc=INK, ec=INK, zorder=3))
    return Box(cx - 0.03, cy - w / 2, 0.06, w)


def component(ax, x, y, w, h, name, items=(), fs=7.0, fill=SOFT):
    ax.add_patch(Rectangle((x, y), w, h, fc=fill, ec=INK, lw=0.9, zorder=2))
    # component icon, top-right
    ix, iy = x + w - 0.24, y + h - 0.2
    ax.add_patch(Rectangle((ix, iy), 0.16, 0.11, fc="white", ec=INK, lw=0.7, zorder=3))
    for dy in (0.02, 0.06):
        ax.add_patch(Rectangle((ix - 0.04, iy + dy), 0.08, 0.03, fc="white", ec=INK, lw=0.6, zorder=4))
    text(ax, x + 0.08, y + h - 0.1, "«component»", size=fs - 1, ha="left", color=GREY)
    text(ax, x + 0.08, y + h - 0.25, name, size=fs + 0.8, bold=True, ha="left")
    for i, it in enumerate(items):
        text(ax, x + 0.1, y + h - 0.44 - i * (fs * 1.45 / 72), "• " + it, size=fs - 0.3, ha="left")
    return Box(x, y, w, h)


def node3d(ax, x, y, w, h, title, stereo=None, fs=7.5, fill=SOFT, depth=0.1):
    ax.add_patch(Rectangle((x, y), w, h, fc=fill, ec=INK, lw=0.9, zorder=1))
    ax.add_patch(Polygon([(x, y + h), (x + depth, y + h + depth), (x + w + depth, y + h + depth), (x + w, y + h)], closed=True, fc="#f7f9fc", ec=INK, lw=0.9, zorder=1))
    ax.add_patch(Polygon([(x + w, y), (x + w + depth, y + depth), (x + w + depth, y + h + depth), (x + w, y + h)], closed=True, fc="#cfd8e6", ec=INK, lw=0.9, zorder=1))
    if stereo:
        text(ax, x + 0.1, y + h - 0.1, f"«{stereo}»", size=fs - 1, ha="left", color=GREY)
    text(ax, x + 0.1, y + h - (0.25 if stereo else 0.12), title, size=fs + 0.5, bold=True, ha="left")
    return Box(x, y, w, h)


def artifact(ax, x, y, w, h, label, fs=6.8):
    fold = 0.08
    ax.add_patch(Polygon([(x, y), (x + w, y), (x + w, y + h - fold), (x + w - fold, y + h), (x, y + h)], closed=True, fc="white", ec=INK, lw=0.8, zorder=3))
    line(ax, [(x + w - fold, y + h), (x + w - fold, y + h - fold), (x + w, y + h - fold)], lw=0.6)
    text(ax, x + w / 2, y + h / 2 - 0.01, label, size=fs)
    return Box(x, y, w, h)
