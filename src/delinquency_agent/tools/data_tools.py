"""Descriptive analysis tools. Plain functions returning JSON-serialisable dicts."""

import pandas as pd

from delinquency_agent.data.loader import DERIVED_COLS, TARGET, load_data

PLACEHOLDER = "placeholder - tool not implemented yet"
MAX_CATEGORIES = 10  # more distinct text values than this -> treated as an identifier


def get_schema() -> dict:
    """List all columns with their data types, the row count, and the target column."""
    df = load_data()
    columns = []
    for name in df.columns:
        s = df[name]
        if pd.api.types.is_numeric_dtype(s):
            col = {"name": name, "type": "numeric",
                   "min": round(float(s.min()), 3), "max": round(float(s.max()), 3)}
        elif s.nunique() <= MAX_CATEGORIES:
            col = {"name": name, "type": "categorical", "values": sorted(s.dropna().unique().tolist())}
        else:
            col = {"name": name, "type": "identifier"}
        if name in DERIVED_COLS:
            col["derived"] = DERIVED_COLS[name]
        columns.append(col)
    return {"rows": len(df), "target": TARGET, "columns": columns}


def describe_column(column: str) -> dict:
    """Summary statistics for one column: min/max/mean/median for numeric columns,
    top values for categorical ones. `column` must be an exact column name."""
    return {"note": PLACEHOLDER, "tool": "describe_column", "column": column}


def value_counts(column: str) -> dict:
    """Count of each distinct value in a categorical column (e.g. Employment_Status, Location)."""
    return {"note": PLACEHOLDER, "tool": "value_counts", "column": column}


def rate_by_group(column: str, bins: int | None = None) -> dict:
    """Delinquency rate and customer count for each group of `column`.
    Numeric columns are split into `bins` equal-sized groups (default 4)."""
    return {"note": PLACEHOLDER, "tool": "rate_by_group", "column": column, "bins": bins}


def correlation_with_target() -> dict:
    """Correlation of every numeric column with Delinquent_Account, strongest first."""
    return {"note": PLACEHOLDER, "tool": "correlation_with_target"}
