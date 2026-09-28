"""Run the named queries in sql/*.sql against the DuckDB database.

Each query in the SQL files starts with a line like `-- name: monthly_kpis`,
so the SQL files stay the single source of truth and the notebooks call
`hm.q("monthly_kpis")` instead of copying SQL into Python.
"""
import os
import re
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = ROOT / "sql"
DEFAULT_DB = ROOT / "data" / "hm.duckdb"
_NAME_LINE = re.compile(r"^--\s*name:\s*(\w+)\s*$", re.MULTILINE)


def load_queries(sql_dir=SQL_DIR):
    """Return {query_name: sql_text} for every named query in sql_dir."""
    queries = {}
    for path in sorted(Path(sql_dir).glob("*.sql")):
        text = path.read_text(encoding="utf-8")
        markers = list(_NAME_LINE.finditer(text))
        for i, marker in enumerate(markers):
            end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
            body = text[marker.end():end]
            body = body[: body.rfind(";")] if ";" in body else body
            name = marker.group(1)
            if name in queries:
                raise ValueError(f"Query name '{name}' is defined twice (second time in {path.name})")
            queries[name] = body.strip()
    return queries


class HM:
    """Read-only connection to the project database.

    The database path defaults to data/hm.duckdb and can be overridden with
    the HM_DB environment variable (for example to point at the sample database).
    """

    def __init__(self, db_path=None):
        path = Path(db_path or os.environ.get("HM_DB") or DEFAULT_DB)
        if not path.is_absolute():
            path = ROOT / path
        if not path.exists():
            raise FileNotFoundError(f"{path} not found. Run `python scripts/build_database.py` first.")
        self.path = path
        self.con = duckdb.connect(str(path), read_only=True)
        self.queries = load_queries()

    def q(self, name) -> pd.DataFrame:
        """Run a named query from the sql/ folder."""
        if name not in self.queries:
            raise KeyError(f"No query named '{name}'. Available: {', '.join(sorted(self.queries))}")
        return self.con.execute(self.queries[name]).df()

    def sql(self, text) -> pd.DataFrame:
        """Run ad-hoc SQL."""
        return self.con.execute(text).df()

    def show(self, name):
        """Print a named query's SQL (handy inside notebooks)."""
        print(self.queries[name])
