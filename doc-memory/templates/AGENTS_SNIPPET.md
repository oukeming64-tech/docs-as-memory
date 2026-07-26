## 文档记忆（doc-memory 闭环）

- 文档任务走 doc-memory 闭环：**R 定位 → V 核对 → P 窄改 → S 封口**。
- 找文档只走 Docs as Memory：`overview / search --limit 2 / affected`；**禁止默认整仓读 md**。history/cold/archive 已默认排除，需要时显式 `--include-cold`。
- 改代码后同步文档的顺序固定：`affected → 按当前实现/测试核对 → 窄改 → reindex`，不许跳步。
- 宣称「文档已同步/可交接」前：`python3 doc_memory.py validate` 必须 0 error，并按内置交接清单填证据矩阵；**禁止只凭作者摘要验收**。
- `--allow-stale` / `--allow-partial` 仅供诊断，不得用于完成声称；存量迁移必须先 dry-run，且不得改源文件。
- 指针：Docs as Memory CLI 在仓库根 `doc_memory.py`；编排细则见 doc-memory 技能的 `references/PIPELINE.md`。
