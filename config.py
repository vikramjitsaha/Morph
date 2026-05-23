"""
config.py — Loads all settings from .env
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── LLM Provider ────────────────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").lower()  # "openrouter" | "ollama"

# OpenRouter
OPENROUTER_API_KEY   = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL  = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL     = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku")

# Ollama
OLLAMA_BASE_URL      = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL         = os.getenv("OLLAMA_MODEL", "llama3.2")

# Generation
MAX_TOKENS           = int(os.getenv("MAX_TOKENS", "4096"))
TEMPERATURE          = float(os.getenv("TEMPERATURE", "0.3"))

# Paths
OUTPUT_DIR           = os.getenv("OUTPUT_DIR", "./output")
REQUIREMENTS_FILE    = os.getenv("REQUIREMENTS_FILE", "./requirements.md")

# Dashboard
DASHBOARD_REFRESH_RATE = float(os.getenv("DASHBOARD_REFRESH_RATE", "0.25"))


def get_active_model() -> str:
    if LLM_PROVIDER == "ollama":
        return OLLAMA_MODEL
    return OPENROUTER_MODEL


def validate():
    """Raise early if critical config is missing."""
    if LLM_PROVIDER == "openrouter" and not OPENROUTER_API_KEY:
        raise EnvironmentError(
            "LLM_PROVIDER=openrouter but OPENROUTER_API_KEY is not set in .env"
        )
    if LLM_PROVIDER not in ("openrouter", "ollama"):
        raise EnvironmentError(
            f"Unknown LLM_PROVIDER='{LLM_PROVIDER}'. Must be 'openrouter' or 'ollama'."
        )
