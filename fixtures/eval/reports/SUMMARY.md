# Evaluation evidence

公开版本把“省上下文”与“命令跑得更快”明确分开，不用单次体感代替证据。

## 当前公开证据

- [真实文档副本基准](real-docs-benchmark-2026-07-26.md)：四个真实目录、
  59 篇 Markdown；验证源哈希不变、14 个查询、冷域回退、`affected` 映射和封口时间。
- [Token 验收规则](../../../specs/TOKEN_EVAL.md)：固定
  `est_tokens = ceil(normalized_utf8_bytes / 4)`、加载范围、任务卡、内容哈希和
  双端一致性阈值。
- [v0.1.1 Codex 回归：L0](codex-20260726-T-l0-budget.md)、
  [search](codex-20260726-T-auth-locate.md)、
  [affected](codex-20260726-T-affected-auth.md)：评测在隔离夹具副本运行；
  AC-1 为 0.2555，探针通过。
- `../tasks/`：三个冻结的 demo 任务卡。

## 结论边界

- 当前可公开宣称：该次隔离副本实验中，中位上下文节省 74.6%，源文件 59/59 未变化。
- 当前可公开宣称：v0.1.1 的 Codex 工程回归在冻结夹具上通过 AC-1 数值门槛与
  事实探针，且没有改动源夹具索引。
- 不宣称：API 账单 token 精确节省 74.6%、本地搜索更快、所有项目都能达到同样收益。
- 不宣称：Codex 工程回归等于正式双端验收。修复后的 Kimi/Grok 独立重跑仍待完成。
