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

== Isolation model (PLAN A) ==

The sandbox cluster intentionally runs ONE shared Firestore DB (`sandbox`)
and relies on THIS SDK to keep apps in their own `apps/{owner}--{app}/`
prefix. There is NO IAM-level enforcement: every per-app SA holds
unconditional `roles/datastore.user` and can technically read or write any
document in the `sandbox` DB if it bypasses this wrapper.

We tried using IAM conditions (`resource.name.startsWith(...)`) to enforce
per-app prefixes, but Firestore Native evaluates the condition against the
database resource for Commit/write operations, not the document path — so
the condition is always false. Documented in plan §11-5.

This fits a 10-person trusted team. **Don't put PII in Firestore under this
model.** If you need stronger isolation, see PLAN B below.

== PLAN B — per-app named Firestore DB (upgrade path) ==

If an app needs true isolation (e.g. handling customer PII):

  1. Create a dedicated named DB at app-creation time:
        gcloud firestore databases create \\
          --database=sandbox-{owner}--{app} \\
          --location=asia-northeast1 --type=firestore-native
  2. Grant the per-app SA `roles/datastore.user` with condition:
        resource.name == "projects/.../databases/sandbox-{owner}--{app}"
     (This DOES enforce — the condition evaluates against the DB resource,
     which is unique per app.)
  3. Override `SANDBOX_FIRESTORE_DB` env var to the per-app DB name.

Limits to plan around: ~100 DBs per project. At 10 employees × ~5 apps
each ≈ 50 DBs, fine with headroom.
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
