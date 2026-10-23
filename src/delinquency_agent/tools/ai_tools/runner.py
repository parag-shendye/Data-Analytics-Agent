"""Runs one agent-written tool in its own process (started by sandbox.run_in_subprocess).

Reads {"name", "code", "args"} as JSON from stdin and writes the result as JSON to stdout.
Any exception exits with a traceback on stderr, which is passed back to the model.
"""

import json
import sys

from delinquency_agent.tools.ai_tools.sandbox import load_function

MAX_RESULT_CHARS = 20_000 


def main() -> None:
    request = json.load(sys.stdin)
    fn = load_function(request["name"], request["code"])
    result = fn(**request["args"])

    if not isinstance(result, dict):
        raise TypeError(f"The tool must return a dict, but it returned {type(result).__name__}.")
    text = json.dumps(result)  # fails on numpy numbers: "Object of type int64 is not JSON serializable"
    if len(text) > MAX_RESULT_CHARS:
        raise ValueError(f"The result is too large ({len(text)} characters). Return a summary instead.")
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
