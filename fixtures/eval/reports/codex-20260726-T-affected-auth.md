# Token eval report

- runner: codex
- date: 2026-07-26T22:14:32+08:00
- fixture_id: demo_project@fe358df8e1ac4c20
- task_id: T-affected-auth
- method: normalized_utf8_bytes/4
- mode: scripted_path

## Absolute numbers
- baseline_normalized_utf8_bytes: 28056
- baseline_est_tokens: 7014
- atlas_normalized_utf8_bytes: 5820
- atlas_est_tokens: 1455
- ratio: 0.2074

## Loaded paths (ordered)
1. (affected stdout) — normalized_utf8_bytes=740, est_tokens=185
2. docs/shards/backend/auth-login.md — normalized_utf8_bytes=1401, est_tokens=351
3. docs/shards/backend/auth-permissions.md — normalized_utf8_bytes=1155, est_tokens=289
4. docs/shards/backend/auth-token-refresh.md — normalized_utf8_bytes=1434, est_tokens=359
5. docs/shards/security/threat-model-auth.md — normalized_utf8_bytes=1090, est_tokens=273

## CLI raw
```
$ /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 doc_memory.py --root fixtures/demo_project reindex
reindex 完成：27 碎片，10 个 domain
  docs/INDEX.md  est_tokens=997 (normalized_utf8_bytes=3988, mode=full, 预算≤1500)
  docs/index.json shards_hash=fe358df8e1ac…
[stderr] warn: docs/shards/frontend/web-ui-components.md: verified_at=2026-04-15 已超 90 天，请复核
[exit=0]
$ /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 doc_memory.py --root fixtures/demo_project affected src/auth/
docs/shards/backend/auth-login.md | Auth 登录流程 | 密码登录签发 access+refresh 双 token 的入口、会话约定与错误码。 | est_tokens=351 code_paths=src/auth,src/api/session.py
docs/shards/backend/auth-permissions.md | 权限模型 RBAC | 角色-权限两级模型、scope 命名规范与接口鉴权中间件用法。 | est_tokens=289 code_paths=src/auth/rbac.py
docs/shards/backend/auth-token-refresh.md | Auth token 刷新 | access token 过期后的刷新端点、轮换策略与 REFRESH_TOKEN_EXPIRED 处理。 | est_tokens=359 code_paths=src/auth/refresh.py
docs/shards/security/threat-model-auth.md | 鉴权威胁模型 | 鉴权子系统的威胁清单与对应缓解措施。 | est_tokens=273 code_paths=src/auth
[exit=0]
```

## Probe
- question: 受影响碎片中是否包含鉴权威胁模型？
- answer: affected 命中 docs/shards/security/threat-model-auth.md
- pass: true

## Verdicts (本端量尺结果；AC 是否通过须等双端对比)
- 探针：PASS

## Notes
- 本报告由 tools/token_measure.py 生成；raw 输出见上。
- 双端一致性检查（|K-G|/max ≤ 0.10）见 SUMMARY.md，由后跑完的一方合并。
