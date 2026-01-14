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
# User config has priority - local .env is for development/examples only
CONFIG_PATHS = [
    Path.home() / ".config" / "screenscribe" / "config.env",  # User config (primary)
    Path.home() / ".screenscribe.env",  # Alternative user config
    Path("/etc/screenscribe/config.env"),  # System-wide config
    # Note: Local .env is NOT auto-loaded - use env vars for overrides
]


@dataclass
class ScreenScribeConfig:
    """ScreenScribe configuration."""

    # API Configuration (generic fallback)
    api_key: str = ""
    api_base: str = LIBRAXIS_API_BASE

    # Per-endpoint API keys (use these for multi-provider setups)
    stt_api_key: str = ""  # Falls back to api_key if empty
    llm_api_key: str = ""  # Falls back to api_key if empty
    vision_api_key: str = ""  # Falls back to api_key if empty

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

    def get_stt_api_key(self) -> str:
        """Get API key for STT endpoint."""
        return self.stt_api_key or self.api_key

    def get_llm_api_key(self) -> str:
        """Get API key for LLM endpoint."""
        return self.llm_api_key or self.api_key

    def get_vision_api_key(self) -> str:
        """Get API key for Vision endpoint."""
        return self.vision_api_key or self.api_key

    def validate(self) -> list[str]:
        """Validate config and return list of warnings."""
        warnings = []

        # Check for endpoint/provider mismatch
        openai_endpoints = [
            ep for ep in [self.llm_endpoint, self.vision_endpoint] if "api.openai.com" in ep
        ]
        for ep in openai_endpoints:
            if "/v1/responses" in ep:
                warnings.append(
                    f"Invalid endpoint: {ep}\n"
                    "  OpenAI does not support /v1/responses - use /v1/chat/completions\n"
                    "  Fix in: ~/.config/screenscribe/config.env"
                )

        libraxis_endpoints = [
            ep for ep in [self.llm_endpoint, self.vision_endpoint] if "libraxis" in ep
        ]
        for ep in libraxis_endpoints:
            if "/v1/chat/completions" in ep:
                warnings.append(
                    f"Invalid endpoint: {ep}\n"
                    "  LibraxisAI uses /v1/responses, not /v1/chat/completions\n"
                    "  Fix in: ~/.config/screenscribe/config.env"
                )

        return warnings

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
            # Generic API Key (fallback for all endpoints)
            "SCREENSCRIBE_API_KEY": "api_key",
            # Per-provider keys (set appropriate per-endpoint key)
            "LIBRAXIS_API_KEY": "stt_api_key",  # LibraxisAI typically for STT
            "OPENAI_API_KEY": "llm_api_key",  # OpenAI typically for LLM/Vision
            # Explicit per-endpoint keys (highest priority)
            "SCREENSCRIBE_STT_API_KEY": "stt_api_key",
            "SCREENSCRIBE_LLM_API_KEY": "llm_api_key",
            "SCREENSCRIBE_VISION_API_KEY": "vision_api_key",
            # Base URL (auto-derives endpoints if explicit not set)
            "SCREENSCRIBE_API_BASE": "api_base",
            "LIBRAXIS_API_BASE": "api_base",
            # Explicit endpoints (full URLs, no normalization)
            "SCREENSCRIBE_STT_ENDPOINT": "stt_endpoint",
            "SCREENSCRIBE_LLM_ENDPOINT": "llm_endpoint",
            "SCREENSCRIBE_VISION_ENDPOINT": "vision_endpoint",
            # Models
            "SCREENSCRIBE_STT_MODEL": "stt_model",
            "SCREENSCRIBE_LLM_MODEL": "llm_model",
            "SCREENSCRIBE_VISION_MODEL": "vision_model",
            # Processing
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

        # Per-endpoint API keys (explicit)
        if "stt_api_key" in key_lower:
            self.stt_api_key = value
        elif "llm_api_key" in key_lower:
            self.llm_api_key = value
        elif "vision_api_key" in key_lower:
            self.vision_api_key = value
        # Provider-specific keys
        elif "openai_api_key" in key_lower:
            # OpenAI key → LLM + Vision
            self.llm_api_key = value
            self.vision_api_key = value
        elif "libraxis_api_key" in key_lower:
            # LibraxisAI key → STT (and fallback)
            self.stt_api_key = value
            if not self.api_key:
                self.api_key = value
        elif "api_key" in key_lower:
            self.api_key = value
        # Explicit endpoints (full URLs - use as-is, no normalization)
        elif "stt_endpoint" in key_lower:
            self.stt_endpoint = value.rstrip("/")
        elif "llm_endpoint" in key_lower:
            self.llm_endpoint = value.rstrip("/")
        elif "vision_endpoint" in key_lower:
            self.vision_endpoint = value.rstrip("/")
        # Base URL (derives endpoints if explicit not set)
        elif "api_base" in key_lower:
            # Normalize api_base - remove trailing paths
            normalized = value.rstrip("/")
            for suffix in [
                "/v1/responses",
                "/v1/audio/transcriptions",
                "/v1/chat/completions",
                "/v1",
            ]:
                if normalized.endswith(suffix):
                    normalized = normalized[: -len(suffix)]
                    break
            self.api_base = normalized
            # Only update endpoints if still at defaults (not explicitly set)
            if self.stt_endpoint == LIBRAXIS_STT_ENDPOINT:
                self.stt_endpoint = f"{normalized}/v1/audio/transcriptions"
            if self.llm_endpoint == LIBRAXIS_LLM_ENDPOINT:
                self.llm_endpoint = f"{normalized}/v1/responses"
            if self.vision_endpoint == LIBRAXIS_VISION_ENDPOINT:
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
        elif "vision" in key_lower and "model" not in key_lower and "endpoint" not in key_lower:
            self.use_vision_analysis = value.lower() in ("true", "1", "yes")

    def save_default_config(self) -> Path:
        """Save default config to user's config directory."""
        config_dir = Path.home() / ".config" / "screenscribe"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.env"

        content = f"""# ScreenScribe Configuration
# Made with (งಠ_ಠ)ง by ⌜ScreenScribe⌟ © 2025 — Maciej & Monika + Klaudiusz (AI) + Mikserka (AI)

# =============================================================================
# API KEY (required - pick one)
# =============================================================================
# Use any of these - first non-empty wins:
SCREENSCRIBE_API_KEY={self.api_key}
# OPENAI_API_KEY=sk-proj-xxx
# LIBRAXIS_API_KEY=xxx

# =============================================================================
# ENDPOINTS (explicit full URLs - recommended for clarity)
# =============================================================================
# STT: Speech-to-Text (OpenAI Whisper compatible)
SCREENSCRIBE_STT_ENDPOINT={self.stt_endpoint}

# LLM: Language Model (Responses API - supports previous_response_id chaining)
SCREENSCRIBE_LLM_ENDPOINT={self.llm_endpoint}

# Vision: Vision Model (same as LLM for unified APIs)
SCREENSCRIBE_VISION_ENDPOINT={self.vision_endpoint}

# =============================================================================
# ALTERNATIVE: Base URL (auto-derives endpoints with /v1/... paths)
# =============================================================================
# SCREENSCRIBE_API_BASE=https://api.openai.com
# SCREENSCRIBE_API_BASE=https://api.libraxis.cloud

# =============================================================================
# MODELS
# =============================================================================
SCREENSCRIBE_STT_MODEL={self.stt_model}
SCREENSCRIBE_LLM_MODEL={self.llm_model}
SCREENSCRIBE_VISION_MODEL={self.vision_model}

# =============================================================================
# PROCESSING OPTIONS
# =============================================================================
SCREENSCRIBE_LANGUAGE={self.language}
SCREENSCRIBE_SEMANTIC={str(self.use_semantic_analysis).lower()}
SCREENSCRIBE_VISION={str(self.use_vision_analysis).lower()}
"""

        with open(config_path, "w") as f:
            f.write(content)

        return config_path
