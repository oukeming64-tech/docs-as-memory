# index.json schema v2

```json
{
  "schema_version": 2,
  "generated_at": "2026-07-26T12:00:00+08:00",
  "shard_root": "docs/shards",
  "shards_hash": "<sha256>",
  "l0_mode": "full",
  "l0_budget_est_tokens": 1500,
  "cold_shard_count": 0,
  "shards": [
    {
      "path": "docs/shards/backend/auth-login.md",
      "title": "Auth login flow",
      "summary": "...",
      "keywords": ["auth", "login"],
      "domain": "backend",
      "code_paths": ["src/auth/"],
      "trust_level": 1,
      "verified_at": "2026-07-01",
      "migration_status": null
    }
  ],
  "by_keyword": {
    "auth": ["docs/shards/backend/auth-login.md"]
  },
  "by_code_path": {
    "src/auth/": ["docs/shards/backend/auth-login.md"]
  },
  "domains": {"backend": {}}
}
```

## INDEX.md (L0)

- Hard budget: `est_tokens = ceil(normalized_utf8_bytes/4) ≤ 1500`
- Render modes, chosen deterministically: `full → compact → domains → minimal`
- Cold entries (`history|cold|archive`) are summarized rather than expanded
- `validate` treats an over-budget L0 as an error

## Cross-platform hashing

Before calculating `shards_hash` or per-shard `est_tokens`, Markdown CRLF and
CR line endings are normalized to LF. A Git checkout moving between Windows,
macOS and Linux therefore does not make an otherwise identical index stale.

## Atomic write

1. Create a unique temporary file in the destination directory
2. Write, flush, and `fsync`
3. `os.replace` into the final name
4. Clean up an uncommitted temporary file on failure
