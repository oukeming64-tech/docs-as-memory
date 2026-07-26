# Token eval report

- runner: codex
- date: 2026-07-26T22:20:56+08:00
- fixture_id: demo_project@fe358df8e1ac4c20
- task_id: T-l0-budget
- method: normalized_utf8_bytes/4
- mode: scripted_path

## Absolute numbers
- baseline_normalized_utf8_bytes: 0
- baseline_est_tokens: n/a
- atlas_normalized_utf8_bytes: 3988
- atlas_est_tokens: 997
- ratio: n/a (T-l0-budget 无 baseline)

## Loaded paths (ordered)
1. docs/INDEX.md — normalized_utf8_bytes=3988, est_tokens=997

## CLI raw
```
$ /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 doc_memory.py --root fixtures/demo_project reindex
reindex 完成：27 碎片，10 个 domain
  docs/INDEX.md  est_tokens=997 (normalized_utf8_bytes=3988, mode=full, 预算≤1500)
  docs/index.json shards_hash=fe358df8e1ac…
[stderr] warn: docs/shards/frontend/web-ui-components.md: verified_at=2026-04-15 已超 90 天，请复核
[exit=0]
```

## Probe
- question: L0 是否处于 token 预算内？
- answer: BUDGET_OK
- pass: true

## Verdicts (本端量尺结果；AC 是否通过须等双端对比)
- AC-5 量尺：est_tokens=997 ≤ 1500 → PASS
- 探针：PASS

## Notes
- 本报告由 tools/token_measure.py 生成；raw 输出见上。
- 双端一致性检查（|K-G|/max ≤ 0.10）见 SUMMARY.md，由后跑完的一方合并。
