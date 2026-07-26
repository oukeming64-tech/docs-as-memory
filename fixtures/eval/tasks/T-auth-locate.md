# Task card: T-auth-locate

```task
task_id: T-auth-locate
prompt: 我需要了解鉴权/登录相关的文档：access token 过期后客户端应该怎么续期，续期失败会拿到什么错误码？
allowed_tools: [doc-memory CLI, read 文件]
baseline_mode: all_shards
mode: scripted_path
query: auth token refresh 鉴权 登录
top_k: 2
success_criteria: 加载的 shard 集合 ⊆ {docs/shards/backend/auth-login.md, docs/shards/backend/auth-token-refresh.md, docs/shards/backend/auth-permissions.md, docs/shards/security/threat-model-auth.md} 且探针答对；atlas_est/baseline_est ≤ 0.30
probe_question: refresh token 失效（超期或被轮换）时，POST /auth/refresh 返回什么错误码？
probe_expected: REFRESH_TOKEN_EXPIRED
```

- 对应 AC-1。
- scripted_path 流程固定为：读 INDEX.md →
  `doc-memory search "<query>" --limit <top_k>` → 打开 top_k 碎片。
- 探针判定：probe_expected 字符串出现在已加载碎片正文中（脚本化判定；agent 实机模式由评审人判定）。
- 双方必须使用同一 query、同一 top_k、同一 fixture 哈希，禁止口头提示。
