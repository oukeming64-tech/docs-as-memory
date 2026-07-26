# Changelog

All notable changes to this project will be documented here.

## [0.1.1] - 2026-07-26

### Changed

- Limit `search` to the two highest-scoring results by default; use
  `--limit 0` only when all matches are intentionally needed.
- Freeze scripted token evaluation to each task card's `top_k` instead of
  inheriting an unbounded CLI result set.
- Allow `codex` as an engineering-regression runner without treating it as a
  substitute for the required independent Kimi/Grok acceptance pair.

### Fixed

- Restore the `T-auth-locate` regression from `0.3266` to `0.2555` on the
  frozen fixture while preserving the answer probe.
- Run token evaluation against an isolated fixture copy so `reindex` does not
  dirty committed demo indexes.
- Fail token evaluation immediately when a CLI subprocess exits non-zero.
- Handle external report directories on a different Windows drive without
  failing while formatting the result path.
- Force UTF-8 token-evaluation output on narrow Windows console locales such
  as cp1252.

## [0.1.0] - 2026-07-26

First public alpha release.

### Added

- Self-contained `doc-memory` skill with Retrieve → Verify → Patch → Seal rules.
- Zero-dependency `doc_memory.py` engine for init, reindex, overview, search,
  affected-path lookup, migration and validation.
- Dry-run-first skill and project installers with backup and idempotency checks.
- Cold-domain opt-in, stale-index fail-closed behavior and atomic index writes.
- Demo project, reproducible token evaluation protocol and real-document benchmark.
- Cross-platform CI, MIT license and contribution/security policies.

### Known limitations

- UTF-8 Markdown only.
- Lexical search only; no embeddings or semantic database.
- `code_paths` mappings require human review.
- Public alpha API and file formats may still change.

### Fixed

- Force UTF-8 CLI and installer output on Windows locales that otherwise default
  to legacy encodings such as cp1252.
- Normalize Markdown line endings before hashing and sizing so a cross-platform
  Git checkout does not falsely invalidate a committed index. This hash semantic
  is recorded as `index.json` schema version 2.
