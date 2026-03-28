# NESQ Local Testing Guide

For local development and testing, this migration folder includes helper scripts for submitting entities to the Jawafdehi NES Queue (NESQ) API.

## Prerequisites

- Running local Jawafdehi API instance (typically `http://127.0.0.1:8000`)
- Admin or moderator token from Jawafdehi API (required for `auto_approve` functionality)

## Bulk Submission: submit_to_nesq.py

Bulk-submits all 108 constitutional commission entities from the migration JSON as `CREATE_ENTITY` items with `auto_approve=true`.

> **Note**: The `auto_approve` flag only works with admin/moderator tokens.

### Usage

```bash
cd services/nes
export JAWAFDEHI_API_TOKEN=<admin_or_moderator_token>
poetry run python migrations/011-source-constitutional-commissions/submit_to_nesq.py
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JAWAFDEHI_API_TOKEN` | Yes | — | Admin/moderator token (required for auto_approve) |
| `JAWAFDEHI_API_BASE_URL` | No | `http://127.0.0.1:8000` | Jawafdehi API base URL |
| `NESQ_JSON_PATH` | No | `migrations/011-source-constitutional-commissions/source/constitutional_commissions.json` | Path to JSON file (relative to repo root) |

### Example

```bash
export JAWAFDEHI_API_TOKEN=eeece8bf9e175894329a10a0bf785559fb258f61
poetry run python migrations/011-source-constitutional-commissions/submit_to_nesq.py
```

### Expected Output

Per-item progress lines:
```
[1/108] OK slug=ciaa-regional-office-bardibas item_id=2 status=APPROVED
[2/108] OK slug=ciaa-regional-office-biratnagar item_id=3 status=APPROVED
...
[108/108] OK slug=tharu-commission item_id=109 status=APPROVED

Bulk submission summary
  Total:   108
  Success: 108
  Failed:  0
```

## Post-Submission: Processing the Queue

After submitting items with auto-approve, they appear in the Jawafdehi queue with status `APPROVED`. To apply the changes to the local NES database:

```bash
cd services/jawafdehi-api
export NES_DB_PATH=/path/to/nes-db/repository
poetry run python manage.py process_queue
```

This command:
1. Reads approved items from the queue
2. Applies changes to local NES file database
3. Marks items as `COMPLETED` or `FAILED`
4. (In production) Commits and pushes changes to `nes-db` repository

## Troubleshooting

### "Missing required environment variable: JAWAFDEHI_API_TOKEN"

**Cause**: Token not provided.

**Solution**: Export the token from Jawafdehi API before running the script:
```bash
export JAWAFDEHI_API_TOKEN=<your_admin_token>
```

### HTTP 403 on auto_approve

**Cause**: Submitted with a non-admin/moderator token.

**Solution**: Use `auto_approve=false` for regular users, or use an admin/moderator token.

## References

- [NESQ Architecture](https://github.com/Jawafdehi/jawafdehi-meta/blob/main/docs/2026-03-03-nesq/nesq_action_specs.md)
- [Constitutional Commissions Migration README](README.md)
- [Jawafdehi API Documentation](https://github.com/Jawafdehi/JawafdehiAPI)
