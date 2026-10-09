"""Data-quality tools."""

from delinquency_agent.data.loader import load_data


PLACEHOLDER = "placeholder - tool not implemented yet"


def missing_values() -> dict:
    """Number and percentage of missing values for each column that has gaps."""
    df = load_data()
    miss = df.isna().sum().to_frame("missing")
    miss["pct"] = (miss["missing"] / len(df) * 100).round(2)
    miss = miss[miss.missing > 0].sort_values("missing", ascending=False)
    return {
        "rows": len(df),
        "columns_with_missing": [
            {"column": col, "missing": int(row.missing), "pct": float(row.pct)}
            for col, row in miss.iterrows()
        ],
    }



def range_violations() -> dict:
    """Count of values outside expected ranges: Credit_Score outside 300-850,
    Credit_Utilization or Debt_to_Income_Ratio outside 0-1, Account_Tenure of 0, and similar."""
    return {"note": PLACEHOLDER, "tool": "range_violations"}


def check_payment_consistency(max_examples: int = 5) -> dict:
    """Customers whose Missed_Payments (past 12 months) is lower than their number of
    'Missed' months in Month_1-Month_6, which should be impossible.
    Also reports how often the two fields agree exactly and how strongly they are related."""
    df = load_data()
    # Month_1-Month_6 fall inside the 12-month window, so every Missed month must be counted
    violating = df[df["Missed_Payments"] < df["n_missed"]]
    consistent = df.drop(violating.index)
    return {
        "rows": len(df),
        "rule": "Missed_Payments (12 months) >= number of 'Missed' months in Month_1-Month_6",
        "violations": len(violating),
        "violations_pct": round(len(violating) / len(df) * 100, 1),
        "exact_match_pct": round((df["Missed_Payments"] == df["n_missed"]).mean() * 100, 1),
        "correlation_between_fields": round(float(df["Missed_Payments"].corr(df["n_missed"])), 3),
        "delinquency_rate_violating": round(float(violating["Delinquent_Account"].mean()), 3),
        "delinquency_rate_consistent": round(float(consistent["Delinquent_Account"].mean()), 3),
        "examples": [
            {"customer": row.Customer_ID, "missed_payments_12m": int(row.Missed_Payments),
             "missed_months_6m": int(row.n_missed)}
            for row in violating.head(max_examples).itertuples()
        ],
    }
