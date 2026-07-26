# Changelog

All notable changes to this project will be documented here.

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
