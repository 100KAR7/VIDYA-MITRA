import os
from dataclasses import dataclass, replace


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int, minimum: int | None = None) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    return parsed


@dataclass(frozen=True)
class RuntimeSettings:
    environment: str = "production"
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    testing: bool = False
    secret_key: str = "vidya-mitra-local-secret"
    platform_store_path: str = "outputs/platform_store.db"
    session_ttl_seconds: int = 1800
    max_live_sessions: int = 1000
    auth_token_ttl_seconds: int = 43200
    prediction_logging_enabled: bool = True
    waitress_threads: int = 8

    @classmethod
    def from_env(cls) -> "RuntimeSettings":
        env = os.getenv("VIDYA_ENV", "production").strip().lower()
        return cls(
            environment=env,
            host=os.getenv("VIDYA_HOST", "0.0.0.0"),
            port=_as_int(os.getenv("VIDYA_PORT"), 5000, minimum=1),
            debug=_as_bool(os.getenv("VIDYA_DEBUG"), env != "production"),
            testing=_as_bool(os.getenv("VIDYA_TESTING"), False),
            secret_key=os.getenv("VIDYA_SECRET_KEY", "vidya-mitra-local-secret"),
            platform_store_path=os.getenv("VIDYA_PLATFORM_STORE", "outputs/platform_store.db"),
            session_ttl_seconds=_as_int(os.getenv("VIDYA_SESSION_TTL_SECONDS"), 1800, minimum=60),
            max_live_sessions=_as_int(os.getenv("VIDYA_MAX_LIVE_SESSIONS"), 1000, minimum=10),
            auth_token_ttl_seconds=_as_int(os.getenv("VIDYA_AUTH_TOKEN_TTL_SECONDS"), 43200, minimum=300),
            prediction_logging_enabled=_as_bool(os.getenv("VIDYA_SAVE_PREDICTIONS"), True),
            waitress_threads=_as_int(os.getenv("VIDYA_WAITRESS_THREADS"), 8, minimum=2),
        )

    def with_overrides(self, **overrides) -> "RuntimeSettings":
        safe_overrides = {key: value for key, value in overrides.items() if hasattr(self, key)}
        return replace(self, **safe_overrides)
