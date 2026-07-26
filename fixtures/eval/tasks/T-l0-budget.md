# Task card: T-l0-budget

```task
task_id: T-l0-budget
prompt: 测量 docs/INDEX.md（L0）的 est_tokens 是否在 1500 预算内。
allowed_tools: [doc-memory CLI, read 文件]
baseline_mode: none
mode: scripted_path
success_criteria: est_tokens(INDEX.md) ≤ 1500
probe_question: L0 是否处于 token 预算内？
probe_expected: BUDGET_OK
```

- 对应 AC-5。
- 不经过模型；直接对 INDEX.md 跑量尺。Kimi 与 Grok 必须各自执行并交报告（specs/TOKEN_EVAL.md §5）。
- `probe_expected: BUDGET_OK` 表示量尺结果 ≤1500 时探针判通过。
