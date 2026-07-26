# Task card: T-affected-auth

```task
task_id: T-affected-auth
prompt: 我刚改完 src/auth/ 下的代码，哪些文档碎片可能受影响需要核对更新？
allowed_tools: [doc-memory CLI, read 文件]
baseline_mode: all_shards
mode: scripted_path
affected_path: src/auth/
top_k: 0
success_criteria: affected 命中集合 ⊇ {docs/shards/backend/auth-login.md, docs/shards/backend/auth-token-refresh.md, docs/shards/backend/auth-permissions.md, docs/shards/security/threat-model-auth.md} 且探针答对
probe_question: 受影响碎片中是否包含鉴权威胁模型？
probe_expected: docs/shards/security/threat-model-auth.md
```

- 对应 AC-6（正确性为主），token 数字作为 AC-1 的辅助附录。
- scripted_path 流程固定为：`doc-memory affected src/auth/` → 打开全部命中碎片（top_k=0 表示不截断）。
- 探针判定：probe_expected 路径出现在 affected 输出中。
