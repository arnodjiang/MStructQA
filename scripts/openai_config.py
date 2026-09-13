"""Project-wide OpenAI configuration."""
import os
from pathlib import Path

from dotenv import dotenv_values

MODEL = "gpt-6-astra"


def load(root):
    root = Path(root)
    config = dict(dotenv_values(root / ".env", interpolate=False))
    for key in ("OPENAI_API_KEY", "OPENAI_BASE_URL"):
        if os.environ.get(key):
            config[key] = os.environ[key]
    configured = os.environ.get("OPENAI_MODEL") or config.get("OPENAI_MODEL")
    config["OPENAI_MODEL"] = configured or MODEL
    return config
