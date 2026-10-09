"""Ground truth from the notebook EDA (../eda.ipynb). Tools must reproduce these numbers."""

from delinquency_agent.tools import quality_tools


def test_missing_values():
    result = quality_tools.missing_values()
    missing = {c["column"]: c["missing"] for c in result["columns_with_missing"]}
    assert result["rows"] == 500
    assert missing == {"Income": 39, "Loan_Balance": 29, "Credit_Score": 2}


def test_check_payment_consistency():
    result = quality_tools.check_payment_consistency()
    assert result["violations"] == 141                  # summed from the notebook crosstab
    assert result["exact_match_pct"] == 14.4            # notebook: 0.144
    assert result["examples"][0]["customer"] == "CUST0003"  # 0 missed in 12m, 2 Missed months
    assert len(result["examples"]) == 5
