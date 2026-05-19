#!/usr/bin/env python3
"""Validate sandbox.yaml. Exit non-zero on any error.

Schema enforced here is the source of truth for what counts as a valid app
in the plaize Sandbox platform. Keep in sync with the docs in the Notion
Sandbox Guide.
"""
from __future__ import annotations

import re
import sys
from datetime import date, timedelta
from pathlib import Path

import yaml

OWNER_RE = re.compile(r"^[a-z0-9]+$")           # no hyphens — must be a single segment
APP_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}[a-z0-9]$")
ALLOWED_RUNTIMES = {"python", "static", "node"}  # python template defaults to python
REQUIRED_FIELDS = {"name", "owner", "app", "runtime", "purpose"}
MAX_TEMPORARY_DAYS = 180


def validate(path: Path) -> list[str]:
    errors: list[str] = []

    if not path.exists():
        return [f"{path}: not found"]

    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        return [f"{path}: invalid YAML — {e}"]

    if not isinstance(data, dict):
        return [f"{path}: must be a mapping"]

    missing = REQUIRED_FIELDS - data.keys()
    if missing:
        errors.append(f"missing required fields: {sorted(missing)}")

    owner = data.get("owner", "")
    if not isinstance(owner, str) or not OWNER_RE.match(owner):
        errors.append(f"owner must match {OWNER_RE.pattern} (got {owner!r})")

    app = data.get("app", "")
    if not isinstance(app, str) or not APP_RE.match(app):
        errors.append(f"app must match {APP_RE.pattern} (got {app!r})")

    # Resulting Cloud Run service name: app--<owner>--<app>. Cloud Run limit is 49 chars.
    full_service_name = f"app--{owner}--{app}"
    if len(full_service_name) > 49:
        errors.append(f"resulting Cloud Run service name {full_service_name!r} exceeds 49 chars")

    runtime = data.get("runtime")
    if runtime not in ALLOWED_RUNTIMES:
        errors.append(f"runtime must be one of {sorted(ALLOWED_RUNTIMES)} (got {runtime!r})")

    # Lifetime: exactly one of expires_at / lifetime: permanent
    has_expires = "expires_at" in data
    is_permanent = data.get("lifetime") == "permanent"
    if has_expires and is_permanent:
        errors.append("set either expires_at OR lifetime: permanent, not both")
    if not has_expires and not is_permanent:
        errors.append("set expires_at (temporary) or lifetime: permanent")

    if has_expires:
        v = data["expires_at"]
        if not isinstance(v, date):
            errors.append("expires_at must be YYYY-MM-DD")
        else:
            today = date.today()
            if v < today:
                errors.append(f"expires_at is in the past: {v}")
            if v > today + timedelta(days=MAX_TEMPORARY_DAYS):
                errors.append(
                    f"expires_at must be within {MAX_TEMPORARY_DAYS} days from today "
                    f"({today + timedelta(days=MAX_TEMPORARY_DAYS)}). Got {v}."
                )

    # data section: shape check only — actual integration validity is checked at runtime.
    data_section = data.get("data") or {}
    if not isinstance(data_section, dict):
        errors.append("data must be a mapping (or omitted)")
    else:
        notion = data_section.get("notion")
        if notion is not None and not isinstance(notion, list):
            errors.append("data.notion must be a list of {id, access} entries")
        if "firestore" in data_section and not isinstance(data_section["firestore"], bool):
            errors.append("data.firestore must be a boolean")

    return errors


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("sandbox.yaml")
    errors = validate(path)
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(f"OK: {path} validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
