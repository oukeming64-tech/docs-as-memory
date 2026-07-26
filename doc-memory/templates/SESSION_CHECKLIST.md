# SESSION_CHECKLIST — doc-memory 会话勾选单

按任务类型选用对应段落；每行完成后打勾（含证据路径/命令输出）。

## 通用前置

- [ ] `validate` / `overview` 确认索引新鲜；纯读取任务未擅自 init/reindex
- [ ] 未整仓读 md；未打开 `docs/history/**`（除非用户点名）
- [ ] 所有完成判断都来自当前文件与实际命令，不只来自作者摘要

## S1 新会话要文档地图（R）

- [ ] `python3 doc_memory.py overview`（或读 `docs/INDEX.md`）→ 记录 est_tokens
- [ ] 只按需要下钻了 ≤2 篇碎片

## S2 只读检索（R，必要时 V）

- [ ] `python3 doc_memory.py search "<关键词>" --limit 2`
- [ ] 只打开了命中的 1～2 篇碎片
- [ ] 若用了 `--include-cold`，任务确实点名历史或热域无答案，并已说明回退
- [ ] 未把 `--allow-partial` 输出当作“确实没有”
- [ ] 若内容与代码疑似冲突 → 已进入 V 并向用户报告（未静默采信文档）

## S3 代码改动后同步文档（R→V→P→S，顺序固定）

- [ ] 1. `python3 doc_memory.py affected <改动路径>` → 记录受影响碎片列表
- [ ] 2. 按 `VERIFY_CHECKLIST.md` 对照当前实现、配置和测试
- [ ] 3. 对照实现/测试得出漂移清单与 patch 范围（范围 = affected ∪ diff 推导，无无关文件）
- [ ] 4. 契约/规范类冲突已提问用户（如本范围）
- [ ] 5. 窄改锁定文件；更新 `verified_at`；说明改了/没改/defer 什么
- [ ] 6. `python3 doc_memory.py reindex`
- [ ] 7. `python3 doc_memory.py validate` → 0 error

## S4 交接审计（S 主，R 辅助）

- [ ] 1. 先立 claim：对方声称完成了什么（逐条列出）
- [ ] 2. 按 `HANDOFF_CHECKLIST.md` 独立取证
- [ ] 3. 文档面用 `overview`/`search` 定位当前 docs（未整读 history）
- [ ] 4. `python3 doc_memory.py validate` → 记录输出
- [ ] 5. 搜 `todo/pending/next/blocked/known issue` 与完成声称的矛盾
- [ ] 6. 填证据矩阵（Scope/Implementation/Verification/Documentation/Data/Release/Human acceptance）
- [ ] 7. Documentation 行引用了实际读过的路径或 CLI 输出（非作者摘要）
- [ ] 8. 结论：通过 / 阻断（阻断附最小修复项）

## S6 索引体检（S 子集）

- [ ] `python3 doc_memory.py validate` → 记录 error/warn 数
