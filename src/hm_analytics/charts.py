"""Shared chart style so every figure in the project looks like one set."""
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

ROOT = Path(__file__).resolve().parents[2]
IMAGES = ROOT / "images"

# Categorical colors in a fixed order (colorblind-checked). Use them in this order.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
ACCENT = SERIES[0]
MUTED = "#c9c8c3"          # de-emphasized bars / context lines
TEXT = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e6e5e0"
POSITIVE, NEGATIVE = "#2a78d6", "#eb6834"   # diverging pair for gains vs losses


def apply_style():
    plt.rcParams.update({
        "figure.figsize": (9, 5),
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "font.size": 10.5,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad": 26,
        "axes.labelcolor": TEXT_SECONDARY,
        "axes.edgecolor": GRID,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,
        "xtick.color": TEXT_SECONDARY,
        "ytick.color": TEXT_SECONDARY,
        "text.color": TEXT,
        "legend.frameon": False,
        "lines.linewidth": 2,
        "axes.prop_cycle": plt.cycler(color=SERIES),
    })


def pct_axis(ax, axis="x", decimals=0):
    fmt = mtick.PercentFormatter(1.0, decimals=decimals)
    (ax.xaxis if axis == "x" else ax.yaxis).set_major_formatter(fmt)


def subtitle(ax, text):
    """Grey one-line explanation under the chart title."""
    ax.text(0, 1.012, text, transform=ax.transAxes, color=TEXT_SECONDARY, fontsize=9.5, va="bottom")


def barh(ax, labels, values, highlight=None, fmt="{:.0%}", color=ACCENT):
    """Horizontal bars, largest at the top, with value labels.

    highlight: optional collection of labels to draw in the accent color;
    everything else is muted. With no highlight, every bar uses `color`.
    """
    labels, values = list(labels)[::-1], list(values)[::-1]
    colors = [color if highlight is None or label in highlight else MUTED for label in labels]
    bars = ax.barh(labels, values, color=colors, height=0.7)
    ax.grid(axis="y", visible=False)
    span = max(abs(v) for v in values) or 1
    for bar, value in zip(bars, values):
        offset = span * 0.01 * (1 if value >= 0 else -1)
        ax.text(bar.get_width() + offset, bar.get_y() + bar.get_height() / 2, fmt.format(value),
                va="center", ha="left" if value >= 0 else "right", fontsize=9, color=TEXT_SECONDARY)
    return bars


def save(fig, name):
    IMAGES.mkdir(exist_ok=True)
    fig.savefig(IMAGES / f"{name}.png", bbox_inches="tight", facecolor="white")
