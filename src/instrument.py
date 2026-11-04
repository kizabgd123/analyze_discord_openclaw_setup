"""
instrument.py — First-Class Sentry Observability & Telemetry.
============================================================
First-import boundary required by backend-dev-guidelines.
Enforces:
- Structured exception capture (Sentry.capture_exception).
- Context breadcrumbs and transaction spans.
- Graceful degradation if Sentry SDK is absent or unconfigured.
"""

import sys
import logging
from typing import Optional, Dict, Any
from src.config.unified_config import config

logger = logging.getLogger("Observability")

_SENTRY_AVAILABLE = False

try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration

    if config.observability.enabled and config.observability.dsn:
        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR
        )
        sentry_sdk.init(
            dsn=config.observability.dsn,
            environment=config.observability.environment,
            traces_sample_rate=config.observability.traces_sample_rate,
            integrations=[sentry_logging],
            release=f"{config.project_name}@{config.version}"
        )
        _SENTRY_AVAILABLE = True
        logger.info("[Observability] Sentry SDK successfully initialized.")
    else:
        logger.info("[Observability] Sentry disabled or DSN omitted; running in structured logging mode.")
except ImportError:
    logger.info("[Observability] sentry_sdk package not installed; utilizing fallback observability layer.")


def capture_exception(exception: BaseException, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Captures an exception to Sentry and logs detailed context.
    Strictly prevents silent or swallowed failures.
    """
    logger.error(
        f"[Observability Capture] Exception: {type(exception).__name__}: {str(exception)} | Context: {context}",
        exc_info=True
    )
    if _SENTRY_AVAILABLE:
        try:
            with sentry_sdk.push_scope() as scope:
                if context:
                    for key, val in context.items():
                        scope.set_extra(key, val)
                sentry_sdk.capture_exception(exception)
        except Exception as e:
            logger.warning(f"[Observability] Failed to dispatch exception to Sentry: {e}")


def capture_message(message: str, level: str = "info", context: Optional[Dict[str, Any]] = None) -> None:
    """Captures an informational or warning audit event."""
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(f"[Observability Message] {message} | Context: {context}")
    if _SENTRY_AVAILABLE:
        try:
            with sentry_sdk.push_scope() as scope:
                if context:
                    for key, val in context.items():
                        scope.set_extra(key, val)
                sentry_sdk.capture_message(message, level=level)
        except Exception as e:
            logger.warning(f"[Observability] Failed to dispatch message to Sentry: {e}")
