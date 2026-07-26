# Token eval report

- runner: codex
- date: 2026-07-26T22:23:42+08:00
- fixture_id: demo_project@fe358df8e1ac4c20
- task_id: T-auth-locate
- method: normalized_utf8_bytes/4
- mode: scripted_path

## Absolute numbers
- baseline_normalized_utf8_bytes: 28056
- baseline_est_tokens: 7014
- atlas_normalized_utf8_bytes: 7167
- atlas_est_tokens: 1792
- ratio: 0.2555

## Loaded paths (ordered)
1. docs/INDEX.md — normalized_utf8_bytes=3988, est_tokens=997
2. (search stdout) — normalized_utf8_bytes=344, est_tokens=86
3. docs/shards/backend/auth-login.md — normalized_utf8_bytes=1401, est_tokens=351
4. docs/shards/backend/auth-token-refresh.md — normalized_utf8_bytes=1434, est_tokens=359

## CLI raw
```
$ /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 doc_memory.py --root fixtures/demo_project reindex
reindex 完成：27 碎片，10 个 domain
  docs/INDEX.md  est_tokens=997 (normalized_utf8_bytes=3988, mode=full, 预算≤1500)
  docs/index.json shards_hash=fe358df8e1ac…
[stderr] warn: docs/shards/frontend/web-ui-components.md: verified_at=2026-04-15 已超 90 天，请复核
[exit=0]
$ /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 doc_memory.py --root fixtures/demo_project search auth token refresh 鉴权 登录 --limit 2
docs/shards/backend/auth-login.md | Auth 登录流程 | 密码登录签发 access+refresh 双 token 的入口、会话约定与错误码。 | est_tokens=351 score=25
docs/shards/backend/auth-token-refresh.md | Auth token 刷新 | access token 过期后的刷新端点、轮换策略与 REFRESH_TOKEN_EXPIRED 处理。 | est_tokens=359 score=25
[exit=0]
```

## Probe
- question: refresh token 失效（超期或被轮换）时，POST /auth/refresh 返回什么错误码？
- answer: 在已加载碎片中找到 REFRESH_TOKEN_EXPIRED
- pass: true

## Verdicts (本端量尺结果；AC 是否通过须等双端对比)
- AC-1 量尺：ratio=0.2555 ≤ 0.3 → PASS
- 探针：PASS

## Notes
- 本报告由 tools/token_measure.py 生成；raw 输出见上。
- 双端一致性检查（|K-G|/max ≤ 0.10）见 SUMMARY.md，由后跑完的一方合并。
