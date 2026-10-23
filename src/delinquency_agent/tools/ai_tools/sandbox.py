"""Validation gate for agent-written tools.

1. validate_source: static checks on the code (it is parsed, never run).
2. run_in_subprocess: a test run in a separate process with a timeout.

This is not a security sandbox
"""

import ast
import builtins
import json
import re
import subprocess
import sys
from collections.abc import Callable

import numpy as np
import pandas as pd

TEST_TIMEOUT_SECONDS = 15

# Argument types the model can pass as JSON
BASIC_TYPES = {"int", "float", "str", "bool", "list", "dict", "None"}

FORBIDDEN_NAMES = {
    "open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars",
    "getattr", "setattr", "delattr", "input", "breakpoint", "print", "help",
    "os", "sys", "subprocess", "shutil", "pathlib", "importlib", "builtins",
}

# pandas methods starting with to_/read_ read or write files, except these
SAFE_IO_ATTRS = {"to_dict", "to_list", "to_numpy", "to_frame"}

# The only builtins available inside an agent-written tool
SAFE_BUILTINS = {name: getattr(builtins, name) for name in [
    "abs", "all", "any", "bool", "dict", "enumerate", "filter", "float", "int", "isinstance",
    "len", "list", "map", "max", "min", "range", "reversed", "round", "set", "sorted", "str",
    "sum", "tuple", "zip", "Exception", "KeyError", "TypeError", "ValueError",
]}


def validate_source(name: str, code: str) -> list[str]:
    """Return a list of problems with the code (empty list = passed). Messages are written for the model."""
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,40}", name):
        return [f"Tool name '{name}' must be snake_case: lowercase letters, digits and _, 3-41 characters."]
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"Syntax error on line {e.lineno}: {e.msg}"]

    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        return ["The code must contain exactly one function definition and nothing else "
                "(no imports, no code outside the function)."]

    fn = tree.body[0]
    errors = []
    if fn.name != name:
        errors.append(f"The function is named '{fn.name}' but the tool name is '{name}'. Use the same name.")
    if not ast.get_docstring(fn):
        errors.append("Add a docstring as the first line of the function, saying what the tool returns.")
    if fn.args.vararg or fn.args.kwarg:
        errors.append("Do not use *args or **kwargs.")
    for arg in fn.args.args + fn.args.kwonlyargs:
        errors.extend(_check_annotation(arg))
    if not (isinstance(fn.returns, ast.Name) and fn.returns.id == "dict"):
        errors.append('The return type must be "-> dict".')

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            errors.append("Do not write import statements: pd, np and load_data are already available.")
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            errors.append("Do not use global or nonlocal.")
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            errors.append(f"'{node.id}' is not allowed in a tool.")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                errors.append(f"Private attributes like '.{node.attr}' are not allowed.")
            elif node.attr.startswith(("to_", "read_")) and node.attr not in SAFE_IO_ATTRS:
                errors.append(f"'.{node.attr}' reads or writes files and is not allowed.")

    return list(dict.fromkeys(errors))  # remove duplicates, keep order


def _check_annotation(arg: ast.arg) -> list[str]:
    if arg.annotation is None:
        return [f"Add a type hint to argument '{arg.arg}'."]
    for node in ast.walk(arg.annotation):
        if isinstance(node, ast.Attribute) or (isinstance(node, ast.Name) and node.id not in BASIC_TYPES):
            return [f"Argument '{arg.arg}' has type '{ast.unparse(arg.annotation)}'. Arguments may only be "
                    "int, float, str, bool, list or dict. Do not pass the DataFrame: call load_data() inside."]
    return []


def make_namespace(name: str) -> dict:
    """Globals for an agent-written tool: pandas, numpy, a load_data that returns a copy, safe builtins."""
    from delinquency_agent.data.loader import load_data

    return {
        "__builtins__": SAFE_BUILTINS,
        "__name__": f"ai_tools.{name}",
        "pd": pd,
        "np": np,
        # a copy, so a tool can never modify the DataFrame shared by all tools
        "load_data": lambda: load_data().copy(),
    }


def load_function(name: str, code: str) -> Callable:
    """Execute the (already validated) code in the restricted namespace and return the function."""
    namespace = make_namespace(name)
    exec(compile(code, f"<ai_tool:{name}>", "exec"), namespace)
    return namespace[name]


def run_in_subprocess(name: str, code: str, args: dict) -> dict:
    """Test-run the tool in a separate Python process. Returns {"ok": True, "result": ...} or {"ok": False, "error": ...}."""
    request = json.dumps({"name": name, "code": code, "args": args})
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "delinquency_agent.tools.ai_tools.runner"],
            input=request, capture_output=True, text=True, timeout=TEST_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"The test run took longer than {TEST_TIMEOUT_SECONDS} seconds."}

    if proc.returncode != 0:
        # Last lines of the traceback: the failing line of the tool and the exception message
        tail = "\n".join(proc.stderr.strip().splitlines()[-3:])
        return {"ok": False, "error": f"The test run failed:\n{tail}"}
    return {"ok": True, "result": json.loads(proc.stdout)}
