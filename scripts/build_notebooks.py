"""Turn notebooks/source/*.py (cells separated by `# %%`) into .ipynb files.

Keeping notebook source as plain Python makes diffs readable on GitHub.
Execute the generated notebooks with:
    jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "notebooks" / "source"
CELL_MARKER = re.compile(r"^# %%(.*)$", re.MULTILINE)


def to_cells(text):
    cells = []
    markers = list(CELL_MARKER.finditer(text))
    for i, marker in enumerate(markers):
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        body = text[marker.end():end].strip("\n")
        if "[markdown]" in marker.group(1):
            lines = [line[2:] if line.startswith("# ") else line.lstrip("#") for line in body.splitlines()]
            cells.append({"cell_type": "markdown", "metadata": {}, "source": _lines("\n".join(lines))})
        elif body.strip():
            cells.append({"cell_type": "code", "metadata": {}, "execution_count": None,
                          "outputs": [], "source": _lines(body)})
    for i, cell in enumerate(cells):
        cell["id"] = f"cell-{i:02d}"
    return cells


def _lines(text):
    parts = text.split("\n")
    return [line + "\n" for line in parts[:-1]] + [parts[-1]]


def main():
    for path in sorted(SOURCE.glob("*.py")):
        notebook = {
            "cells": to_cells(path.read_text(encoding="utf-8")),
            "metadata": {
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }
        out = ROOT / "notebooks" / f"{path.stem}.ipynb"
        out.write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
