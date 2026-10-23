"""The validation gate must accept the builder prompt's example and reject unsafe or invalid code."""

from delinquency_agent.tools.ai_tools.sandbox import run_in_subprocess, validate_source

VALID = '''
def count_rows() -> dict:
    """Number of rows in the dataset."""
    df = load_data()
    return {"rows": int(len(df))}
'''


def test_valid_tool_passes_and_runs():
    assert validate_source("count_rows", VALID) == []
    assert run_in_subprocess("count_rows", VALID, {}) == {"ok": True, "result": {"rows": 500}}


def test_rejects_imports():
    code = VALID.replace("    df = load_data()", "    import os\n    df = load_data()")
    assert any("import" in e for e in validate_source("count_rows", code))


def test_rejects_dataframe_argument():
    code = VALID.replace("count_rows() -> dict", "count_rows(df: pd.DataFrame) -> dict")
    assert any("Do not pass the DataFrame" in e for e in validate_source("count_rows", code))


def test_rejects_file_writes():
    code = VALID.replace('return {"rows": int(len(df))}', 'df.to_csv("x.csv")\n    return {}')
    assert any("to_csv" in e for e in validate_source("count_rows", code))


def test_numpy_result_fails_test_run_with_clear_error():
    code = VALID.replace("int(len(df))", 'df["Age"].sum()')
    run = run_in_subprocess("count_rows", code, {})
    assert not run["ok"] and "not JSON serializable" in run["error"]
