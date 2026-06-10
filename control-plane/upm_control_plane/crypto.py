"""Symmetric encryption for connection credentials (§4 — never store plaintext).

Key comes from UPM_SECRET_KEY (any string; we derive a Fernet key from it). If unset, a
clearly-marked dev key is used so local runs work — production MUST set UPM_SECRET_KEY via
a Docker secret. Credentials are never committed and never returned to clients.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

log = logging.getLogger("upm.crypto")

_DEV_KEY_SOURCE = "upm-dev-insecure-secret"


def _derive_fernet_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    secret = os.environ.get("UPM_SECRET_KEY")
    if not secret:
        log.warning("UPM_SECRET_KEY not set — using an INSECURE dev key. Set it in production.")
        secret = _DEV_KEY_SOURCE
    return Fernet(_derive_fernet_key(secret))


def encrypt(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(token: str | None) -> str | None:
    if token is None:
        return None
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        log.error("failed to decrypt a stored credential (key rotated?)")
        raise


def reset_cache() -> None:
    _fernet.cache_clear()
