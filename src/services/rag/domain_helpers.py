"""Domain-agnostic pack helper loader (no hard-coded fields.pharmacy imports)."""

from __future__ import annotations

import importlib
import logging
from typing import Any, Callable

logger = logging.getLogger("uvicorn.error")


def load_domain_helper(domain_key: str, module_name: str, attr: str) -> Callable[..., Any] | None:
    """Import ``fields.{domain_key}.{module_name}.{attr}`` if present."""
    if not domain_key or domain_key == "generic":
        return None
    try:
        mod = importlib.import_module(f"fields.{domain_key}.{module_name}")
    except ImportError:
        return None
    fn = getattr(mod, attr, None)
    if callable(fn):
        return fn
    return None


def call_domain_helper(
    domain_key: str,
    module_name: str,
    attr: str,
    *args: Any,
    **kwargs: Any,
) -> Any:
    fn = load_domain_helper(domain_key, module_name, attr)
    if fn is None:
        return None
    try:
        return fn(*args, **kwargs)
    except Exception:
        logger.debug(
            "domain_helper_failed domain=%s module=%s attr=%s",
            domain_key,
            module_name,
            attr,
            exc_info=True,
        )
        return None
