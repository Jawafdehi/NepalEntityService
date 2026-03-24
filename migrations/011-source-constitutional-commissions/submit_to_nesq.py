#!/usr/bin/env python3
"""Bulk-submit CREATE_ENTITY requests from a migration JSON file to Jawafdehi NESQ.

Defaults target the constitutional commissions source JSON.
Requires an admin/moderator token because this script sets auto_approve=true.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib import error, request

DEFAULT_JSON_PATH = (
    "migrations/011-source-constitutional-commissions/"
    "source/constitutional_commissions.json"
)


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value.strip() == "":
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _http_json(
    method: str, url: str, token: str, payload: dict | None = None
) -> tuple[int, dict]:
    headers = {
        "Authorization": f"Token {token}",
        "Accept": "application/json",
    }
    body: bytes | None = None

    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")

    req = request.Request(url=url, data=body, headers=headers, method=method)

    try:
        with request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        return exc.code, parsed


def _load_entities(json_path: Path) -> list[dict]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("JSON root must be a list of entity objects.")
    return data


def _clean_entity_data(entity: dict) -> dict:
    blocked_keys = {"type", "sub_type", "created_at", "version_summary", "id"}
    return {k: v for k, v in entity.items() if k not in blocked_keys}


def main() -> int:
    base_url = os.getenv("JAWAFDEHI_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    token = _env("JAWAFDEHI_API_TOKEN")

    repo_root = Path(__file__).resolve().parents[2]
    json_path_raw = os.getenv("NESQ_JSON_PATH", DEFAULT_JSON_PATH)
    json_path = (repo_root / json_path_raw).resolve()

    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    submit_url = f"{base_url}/api/submit_nes_change"

    entities = _load_entities(json_path)
    total = len(entities)
    print(f"Loaded {total} entities from {json_path}")

    success_count = 0
    fail_count = 0
    failed: list[dict] = []

    for i, entity in enumerate(entities, start=1):
        payload_entity = _clean_entity_data(entity)
        slug = payload_entity.get("slug", "unknown-slug")

        request_payload = {
            "action": "CREATE_ENTITY",
            "payload": {
                "entity_data": payload_entity,
            },
            "change_description": f"Bulk NESQ submit from migration JSON: {slug}",
            "auto_approve": True,
        }

        status_code, resp_data = _http_json(
            method="POST",
            url=submit_url,
            token=token,
            payload=request_payload,
        )

        if status_code == 201:
            success_count += 1
            item_id = resp_data.get("id")
            item_status = resp_data.get("status")
            print(
                f"[{i}/{total}] OK slug={slug} item_id={item_id} status={item_status}"
            )
        else:
            fail_count += 1
            failed_item = {
                "index": i,
                "slug": slug,
                "http_status": status_code,
                "response": resp_data,
            }
            failed.append(failed_item)
            print(f"[{i}/{total}] FAIL slug={slug} status={status_code}")

    print("\nBulk submission summary")
    print(f"  Total:   {total}")
    print(f"  Success: {success_count}")
    print(f"  Failed:  {fail_count}")

    if failed:
        print("\nFailed items detail:")
        print(json.dumps(failed, indent=2, ensure_ascii=True))
        return 1

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - local utility script
        print(f"Fatal error: {exc}", file=sys.stderr)
        raise SystemExit(1)
