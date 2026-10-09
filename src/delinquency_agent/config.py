"""Settings loaded from .env (see .env.example)."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# src/delinquency_agent/config.py -> project root is two levels above the package
PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


def _path(env_var: str, default: str) -> Path:
    """Paths in .env are relative to the project root, not the current directory.

    The MCP server runs as a subprocess, so its working directory is not guaranteed.
    """
    return (PROJECT_ROOT / os.getenv(env_var, default)).resolve()


@dataclass(frozen=True)
class Settings:
    data_path: Path = _path("DATA_PATH", "../Delinquency_prediction_dataset.xlsx")
    dictionary_path: Path = _path("DICTIONARY_PATH", "../Updated_Dataset_Description_Guide.pdf")
    output_dir: Path = PROJECT_ROOT / "output"
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3.5:2b")
    mcp_transport: str = os.getenv("MCP_TRANSPORT", "stdio")
    mcp_port: int = int(os.getenv("MCP_PORT", "8000"))


settings = Settings()
