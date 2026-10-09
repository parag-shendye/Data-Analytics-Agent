"""Load the delinquency dataset once and share it across tools."""

from functools import lru_cache

import pandas as pd

from delinquency_agent.config import settings

TARGET = "Delinquent_Account"
MONTH_COLS = [f"Month_{i}" for i in range(1, 7)]

# Columns added here (not in the Excel file), with what they mean
DERIVED_COLS = {
    "emp_clean": "Employment_Status with labels standardised (EMP/employed -> employed)",
    "n_ontime": "number of On-time months in Month_1-Month_6",
    "n_late": "number of Late months in Month_1-Month_6",
    "n_missed": "number of Missed months in Month_1-Month_6",
}


@lru_cache(maxsize=1)
def load_data() -> pd.DataFrame:
    """Return the dataset with derived columns. Read from Excel once, then served from memory.

    The same DataFrame object is shared by every tool: tools must not modify it.
    """
    df = pd.read_excel(settings.data_path)

    df["emp_clean"] = df["Employment_Status"].str.strip().str.lower().replace({"emp": "employed"})

    status = df[MONTH_COLS].apply(lambda s: s.str.strip().str.lower())
    df["n_ontime"] = (status == "on-time").sum(axis=1)
    df["n_late"] = (status == "late").sum(axis=1)
    df["n_missed"] = (status == "missed").sum(axis=1)

    return df
