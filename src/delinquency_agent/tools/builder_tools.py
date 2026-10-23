"""Tools the model uses to write new tools (build mode)."""

import inspect

import pandas as pd

from delinquency_agent.tools.ai_tools.registry import is_approved, save_tool
from delinquency_agent.tools.ai_tools.sandbox import run_in_subprocess, validate_source

MAX_DOC_CHARS = 2500  # pandas docstrings are long; keep the useful start for a small model


def pandas_docs(name: str) -> dict:
    """Documentation of a pandas function or method from the installed pandas version,
    e.g. "DataFrame.isna", "Series.value_counts", "DataFrame.groupby" or "cut"."""
    if "__" in name:
        return {"error": "Private names are not available."}
    obj = pd
    for part in name.removeprefix("pandas.").removeprefix("pd.").split("."):
        obj = getattr(obj, part, None)
        if obj is None:
            return {"error": f"'{name}' was not found in pandas. Try e.g. 'DataFrame.isna' or 'Series.value_counts'."}
    try:
        signature = f"{name}{inspect.signature(obj)}"
    except (TypeError, ValueError):  # some pandas objects have no inspectable signature
        signature = name
    return {"signature": signature, "doc": (inspect.getdoc(obj) or "")[:MAX_DOC_CHARS]}


def create_tool(name: str, code: str, test_args: dict | None = None) -> dict:
    """Submit a new analysis tool: the source code of one Python function named `name`.
    It is checked, test-run with `test_args`, and saved for human review.
    Returns the errors to fix, or the test result if the tool was accepted."""
    if is_approved(name):
        return {"accepted": False, "errors": [f"An approved tool named '{name}' already exists. Choose another name."]}

    errors = validate_source(name, code)
    if errors:
        return {"accepted": False, "errors": errors}

    run = run_in_subprocess(name, code, test_args or {})
    if not run["ok"]:
        return {"accepted": False, "errors": [run["error"]]}

    save_tool(name, code, test_args or {}, run["result"])
    return {"accepted": True, "status": "pending human review", "tool": name, "test_result": run["result"]}
