# Shard format (schema v1)

## Path

- Default root: `docs/shards/`
- Extension: `.md`
- Nested dirs allowed; `domain` field should still be set for L0 grouping

## Frontmatter (YAML between `---`)

| Field | Required | Notes |
|-------|----------|--------|
| `title` | yes | short |
| `summary` | yes | ≤80 Chinese chars or ≤160 English chars (soft limit; validate warns over) |
| `keywords` | yes | list; include **both** EN and ZH when possible |
| `domain` | yes | slug-like string for L0 grouping, e.g. `backend`, `product` |
| `code_paths` | recommended | list of existing repo-relative paths; no absolute path, `..`, or symlink escape; may be file or dir prefix |
| `trust_level` | recommended | int **1–4**, **lower = more authoritative** (1 implementation, 2 API, 3 test, 4 prose) |
| `verified_at` | optional | ISO date `YYYY-MM-DD`; stale threshold default 90 days → warn |
| `migration_status` | optional | `needs-review` or `reviewed`; generated migration copies start as `needs-review` |
| `source_path` | optional | provenance label for a generated migration copy |
| `source_sha256` | optional | SHA-256 of the unchanged source at migration time |
| `migrated_at` | optional | copy creation date; does not mean the content was verified |

Parser/validator rules:

- `title`、`summary`、`domain` and every list item must be strings;
- duplicate keys and unclosed quotes are errors;
- only the documented YAML subset is supported (scalar, inline list, block list);
- shard files and managed `docs/` paths may not be symlinks escaping the project root.

`code_paths: []` 表示作者明确声明“当前没有代码映射”，不会产生缺字段 warning；
字段完全省略仍会提示。迁移副本即使为空，也会通过 `needs-review` 聚合 warning 提醒整理。

## Body

- Prefer ≤150 lines
- No secrets
- Migrated bodies may initially remain long; one-file-one-shard is a transition state, not proof of good decomposition

## Example

```markdown
---
title: Auth login flow
summary: Password login issues access+refresh tokens; 401 refresh path.
keywords: [auth, login, token, 鉴权, 登录]
domain: backend
code_paths: [src/auth/, src/api/session.py]
trust_level: 1
verified_at: 2026-07-01
---

# Auth login flow

...
```
