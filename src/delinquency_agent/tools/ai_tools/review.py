"""Human review of agent-written tools.

uv run python -m delinquency_agent.tools.ai_tools.review list
uv run python -m delinquency_agent.tools.ai_tools.review show NAME
uv run python -m delinquency_agent.tools.ai_tools.review approve NAME
uv run python -m delinquency_agent.tools.ai_tools.review reject NAME

Approved tools are available to the agent (as ai_NAME) the next time the server starts.
Rejected tools stay on disk and in the registry, so the experiment can count them.
"""

import argparse
import json
from datetime import datetime

from delinquency_agent.tools.ai_tools.registry import load_registry, save_registry, tool_path
from delinquency_agent.tools.ai_tools.sandbox import validate_source


def main() -> None:
    parser = argparse.ArgumentParser(description="Review agent-written tools.")
    parser.add_argument("action", choices=["list", "show", "approve", "reject"])
    parser.add_argument("name", nargs="?")
    args = parser.parse_args()

    if args.action == "list":
        list_tools()
        return
    if not args.name:
        parser.error(f"'{args.action}' needs a tool name")

    registry = load_registry()
    if args.name not in registry:
        parser.error(f"no tool named '{args.name}'. Run 'list' to see the tools.")
    if args.action == "show":
        show_tool(args.name, registry[args.name])
    else:
        set_status(args.name, registry, "approved" if args.action == "approve" else "rejected")


def list_tools() -> None:
    registry = load_registry()
    if not registry:
        print("No agent-written tools yet. Create one with: client --build \"...\"")
        return
    for name, entry in registry.items():
        print(f"{entry['status']:<9} {name:<30} {entry['description']}")


def show_tool(name: str, entry: dict) -> None:
    print(f"{name}  [{entry['status']}]  by {entry['model']} on {entry['created']}\n")
    print(tool_path(name).read_text(encoding="utf-8"))
    print(f"Test args:   {json.dumps(entry['test_args'])}")
    print(f"Test result: {json.dumps(entry['test_result'], indent=2)}")


def set_status(name: str, registry: dict, status: str) -> None:
    if status == "approved":
        errors = validate_source(name, tool_path(name).read_text(encoding="utf-8"))
        if errors:  # the file may have been edited since the agent submitted it
            print("Cannot approve, the code no longer passes the checks:\n- " + "\n- ".join(errors))
            return
    registry[name]["status"] = status
    registry[name]["reviewed"] = datetime.now().isoformat(timespec="seconds")
    save_registry(registry)
    print(f"{name}: {status}" + (" (available as ai_" + name + " after a server restart)" if status == "approved" else ""))


if __name__ == "__main__":
    main()
