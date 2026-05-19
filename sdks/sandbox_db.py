"""
Firestore wrapper that auto-scopes every read/write to `apps/{owner}--{app}/...`
so your app can't accidentally touch another sandbox app's data.

Usage:
    from sdks.sandbox_db import client
    db = client()
    db.collection("notes").add({"text": "hello"})
    # → writes to apps/<owner>--<app>/notes (in named DB "sandbox")

The owner and app slug come from env vars set by the deploy workflow:
    SANDBOX_OWNER, SANDBOX_APP

This module is OPTIONAL — only import if your app uses Firestore. You also
need to add `google-cloud-firestore` to requirements.txt.
"""
from __future__ import annotations

import os

try:
    from google.cloud import firestore
except ImportError as e:
    raise ImportError(
        "google-cloud-firestore is not installed. "
        "Add 'google-cloud-firestore==2.18.0' to requirements.txt."
    ) from e

# Firestore named database created in plaize-sandbox-prod project.
_FIRESTORE_DB = os.environ.get("SANDBOX_FIRESTORE_DB", "sandbox")


def _prefix() -> str:
    owner = os.environ.get("SANDBOX_OWNER")
    app = os.environ.get("SANDBOX_APP")
    if not (owner and app):
        raise RuntimeError(
            "SANDBOX_OWNER / SANDBOX_APP env vars must be set "
            "(the deploy workflow injects them automatically)."
        )
    return f"apps/{owner}--{app}"


class SandboxFirestore:
    """Wraps google-cloud-firestore Client and prefixes collection paths."""

    def __init__(self) -> None:
        self._fs = firestore.Client(database=_FIRESTORE_DB)
        self._prefix = _prefix()

    def collection(self, name: str) -> "firestore.CollectionReference":
        """Returns a CollectionReference at apps/{owner}--{app}/<name>."""
        return self._fs.collection(f"{self._prefix}/{name}")

    def document(self, path: str) -> "firestore.DocumentReference":
        """Returns a DocumentReference at apps/{owner}--{app}/<path>."""
        return self._fs.document(f"{self._prefix}/{path}")

    @property
    def raw(self) -> "firestore.Client":
        """Escape hatch: the underlying Firestore client. Use sparingly."""
        return self._fs


def client() -> SandboxFirestore:
    return SandboxFirestore()
