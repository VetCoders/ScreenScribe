"""Configuration management with embedded defaults."""

import os
from dataclasses import dataclass
from pathlib import Path

# Default LibraxisAI configuration
LIBRAXIS_API_BASE = "https://api.libraxis.cloud"
LIBRAXIS_STT_ENDPOINT = f"{LIBRAXIS_API_BASE}/v1/audio/transcriptions"
LIBRAXIS_LLM_ENDPOINT = f"{LIBRAXIS_API_BASE}/v1/responses"
LIBRAXIS_VISION_ENDPOINT = f"{LIBRAXIS_API_BASE}/v1/responses"

# Default models
DEFAULT_STT_MODEL = "whisper-1"
DEFAULT_LLM_MODEL = "ai-suggestions"  # LibraxisAI default
DEFAULT_VISION_MODEL = "ai-suggestions"  # Same model, API router handles vision

# Config file locations (checked in order)
CONFIG_PATHS = [
    Path.cwd() / ".env",  # Local project .env first
    Path.home() / ".config" / "screenscribe" / "config.env",
    Path.home() / ".screenscribe.env",
    Path("/etc/screenscribe/config.env"),
]


@dataclass
class ScreenScribeConfig:
    """ScreenScribe configuration."""

    # API Configuration
    api_key: str = ""
    api_base: str = LIBRAXIS_API_BASE

    # Endpoints
    stt_endpoint: str = LIBRAXIS_STT_ENDPOINT
    llm_endpoint: str = LIBRAXIS_LLM_ENDPOINT
    vision_endpoint: str = LIBRAXIS_VISION_ENDPOINT

    # Models
    stt_model: str = DEFAULT_STT_MODEL
    llm_model: str = DEFAULT_LLM_MODEL
    vision_model: str = DEFAULT_VISION_MODEL

    # Processing options
    language: str = "pl"
    use_semantic_analysis: bool = True
    use_vision_analysis: bool = True
    max_tokens: int = 4096

    @classmethod
    def load(cls) -> "ScreenScribeConfig":
        """Load config from environment and config files."""
        config = cls()

        # Try config files first
        for config_path in CONFIG_PATHS:
            if config_path.exists():
                config._load_from_file(config_path)
                break

        # Environment variables override config files
        config._load_from_env()

        return config

    def _load_from_file(self, path: Path) -> None:
        """Load configuration from .env file."""
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    self._set_from_key(key, value)

    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        env_mapping = {
            "LIBRAXIS_API_KEY": "api_key",
            "SCREENSCRIBE_API_KEY": "api_key",
            "LIBRAXIS_API_BASE": "api_base",
            "SCREENSCRIBE_STT_MODEL": "stt_model",
            "SCREENSCRIBE_LLM_MODEL": "llm_model",
            "SCREENSCRIBE_VISION_MODEL": "vision_model",
            "SCREENSCRIBE_LANGUAGE": "language",
            "SCREENSCRIBE_SEMANTIC": "use_semantic_analysis",
            "SCREENSCRIBE_VISION": "use_vision_analysis",
        }

        for env_key, _attr in env_mapping.items():
            value = os.environ.get(env_key)
            if value:
                self._set_from_key(env_key, value)

    def _set_from_key(self, key: str, value: str) -> None:
        """Set attribute from key-value pair."""
        key_lower = key.lower()

        if "api_key" in key_lower:
            self.api_key = value
        elif "api_base" in key_lower:
            # Normalize api_base - remove trailing paths like /v1/responses, /v1, etc.
            normalized = value.rstrip("/")
            # Strip common API path suffixes
            for suffix in ["/v1/responses", "/v1/audio/transcriptions", "/v1/chat/completions", "/v1"]:
                if normalized.endswith(suffix):
                    normalized = normalized[: -len(suffix)]
                    break
            self.api_base = normalized
            # Update endpoints with normalized base
            self.stt_endpoint = f"{normalized}/v1/audio/transcriptions"
            self.llm_endpoint = f"{normalized}/v1/responses"
            self.vision_endpoint = f"{normalized}/v1/responses"
        elif "stt_model" in key_lower:
            self.stt_model = value
        elif "llm_model" in key_lower:
            self.llm_model = value
        elif "vision_model" in key_lower:
            self.vision_model = value
        elif "language" in key_lower:
            self.language = value
        elif "semantic" in key_lower:
            self.use_semantic_analysis = value.lower() in ("true", "1", "yes")
        elif "vision" in key_lower and "model" not in key_lower:
            self.use_vision_analysis = value.lower() in ("true", "1", "yes")

    def save_default_config(self) -> Path:
        """Save default config to user's config directory."""
        config_dir = Path.home() / ".config" / "screenscribe"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.env"

        content = f"""# ScreenScribe Configuration
# Made with (งಠ_ಠ)ง by ⌜ScreenScribe⌟ © 2025 — Maciej & Monika + Klaudiusz (AI) + Mikserka (AI)

# API Key (required)
LIBRAXIS_API_KEY={self.api_key}

# API Base URL
LIBRAXIS_API_BASE={self.api_base}

# Models
SCREENSCRIBE_STT_MODEL={self.stt_model}
SCREENSCRIBE_LLM_MODEL={self.llm_model}
SCREENSCRIBE_VISION_MODEL={self.vision_model}

# Processing
SCREENSCRIBE_LANGUAGE={self.language}
SCREENSCRIBE_SEMANTIC={str(self.use_semantic_analysis).lower()}
SCREENSCRIBE_VISION={str(self.use_vision_analysis).lower()}
"""

        with open(config_path, "w") as f:
            f.write(content)

        return config_path
