"""Storage for agent-written tools: one .py file per tool plus registry.json with each tool's status.

Status: "pending" (saved by create_tool) -> "approved" or "rejected" (set by a human with review.py).
Only approved tools are loaded by the server.
"""

import ast
import json
import logging
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path

from delinquency_agent.config import settings
from delinquency_agent.tools.ai_tools.sandbox import load_function, validate_source

GENERATED_DIR = Path(__file__).parent / "generated"
REGISTRY_PATH = GENERATED_DIR / "registry.json"

log = logging.getLogger(__name__)


def load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        return {}
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def save_registry(registry: dict) -> None:
    GENERATED_DIR.mkdir(exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2), encoding="utf-8")


def tool_path(name: str) -> Path:
    return GENERATED_DIR / f"{name}.py"


def is_approved(name: str) -> bool:
    return load_registry().get(name, {}).get("status") == "approved"


def save_tool(name: str, code: str, test_args: dict, test_result: dict) -> None:
    """Save a tool that passed the gate as "pending". Resubmitting a pending or rejected tool replaces it."""
    GENERATED_DIR.mkdir(exist_ok=True)
    tool_path(name).write_text(code.strip() + "\n", encoding="utf-8")

    registry = load_registry()
    registry[name] = {
        "status": "pending",
        "description": ast.get_docstring(ast.parse(code).body[0]).splitlines()[0],
        "model": settings.ollama_model,  # the server reads the same .env as the client
        "created": datetime.now().isoformat(timespec="seconds"),
        "test_args": test_args,
        "test_result": test_result,
    }
    save_registry(registry)


def load_approved_tools() -> Iterator[tuple[str, Callable]]:
    """Yield (name, function) for each approved tool. A broken tool is logged and skipped,
    so it cannot stop the other tools or the server from loading."""
    for name, entry in load_registry().items():
        if entry.get("status") != "approved":
            continue
        try:
            code = tool_path(name).read_text(encoding="utf-8")
            # Re-check: the file may have been edited after approval
            errors = validate_source(name, code)
            if errors:
                log.warning("Skipping AI tool %s: %s", name, "; ".join(errors))
                continue
            yield name, load_function(name, code)
        except Exception:
            log.exception("Skipping AI tool %s: failed to load", name)
