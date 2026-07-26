# PIPELINE — R→V→P→S 状态机

```text
任务进入
   │
   ▼
R Retrieve ── overview / search / affected，默认只读 1～2 篇
   │
   ▼
V Verify ──── 对照 diff、实现、配置与测试，锁定事实和范围
   │
   ├── 纯问答且无漂移 ──► 结束
   ▼
P Patch ───── 只改已确认相关的碎片
   │
   ▼
S Seal ────── reindex + validate；交接时补证据矩阵
   │
   ▼
PASS / BLOCKED
```

## R — Retrieve

- 新会话或看全貌：`python3 doc_memory.py overview`
- 主题检索：`python3 doc_memory.py search "<关键词>" --limit 2`
- 代码改动：`python3 doc_memory.py affected <改动路径>`
- 只打开命中的 1～2 篇；冷域只在任务点名或热域无答案时显式回退。
- 纯读取时不得擅自 `init/reindex`；`--allow-partial` 与 `--allow-stale`
  只用于诊断。

输出：待读路径、命中理由和必要的上下文体量。

## V — Verify

遵循 [VERIFY_CHECKLIST.md](VERIFY_CHECKLIST.md)：

- 从实际 diff 与 `affected` 结果锁定文档范围；
- 以当前实现、配置、API 和测试核对文档事实；
- 把问题分成 confirmed / stale / unknown / decision-needed；
- 规范、安全、产品和架构冲突由用户裁决。

输出：漂移清单、最小 patch 范围与阻断项。

## P — Patch

- 只改 V 锁定的文件；
- 不把未来工作写成已经完成；
- 完成事实核对后才更新 `verified_at`；
- 说明改了什么、没改什么、仍待什么决定。

输出：窄范围文档 diff。

## S — Seal

1. 改过 shard 后运行 `python3 doc_memory.py reindex`。
2. 运行 `python3 doc_memory.py validate`；0 error 才能宣称文档封口。
3. 交接场景继续遵循
   [HANDOFF_CHECKLIST.md](HANDOFF_CHECKLIST.md)，给出证据矩阵和
   `PASS / BLOCKED`。

输出：新鲜索引、验证记录和明确结论。

## 合法短路

| 条件 | 路径 |
|---|---|
| 纯问答且 R 已足够、无疑似漂移 | R 后结束 |
| 只检查索引 | 仅 S.validate |
| 只审计交接 | R 定位当前文档 + S 证据审计 |
| 代码或配置发生变化 | R→V→P→S，不得跳步 |
