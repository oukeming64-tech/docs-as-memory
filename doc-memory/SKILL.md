---
name: doc-memory
description: >
  项目文档记忆闭环。在「查文档 / 改代码后同步文档 / 验收交接是否真做完」时使用。
  四步：Retrieve 用本地索引少读 → Verify 对照实现与测试 →
  Patch 只改相关碎片 → Seal 用 reindex/validate 与证据矩阵封口。
  关键词: docs, 文档, sync, 索引, handoff, 交接, shard, Docs as Memory.
---

# doc-memory 怎么用

你不是来「读完整个仓库的 md」的。
你是来按 **R → V → P → S** 四步，**少读、读对、改窄、能验收**。

详细状态机见 [references/PIPELINE.md](references/PIPELINE.md)。
命令见 [references/CALL_ENGINE.md](references/CALL_ENGINE.md)。
真相对照见 [references/VERIFY_CHECKLIST.md](references/VERIFY_CHECKLIST.md)。
交接验收见 [references/HANDOFF_CHECKLIST.md](references/HANDOFF_CHECKLIST.md)。

---

## 0. 开始前 10 秒检查

在项目根：

```bash
# 已安装到项目时
python3 doc_memory.py validate

# 未安装到项目时，也可直接用本技能内置引擎
python3 <doc-memory目录>/scripts/doc_memory.py --root . validate
```

纯读取任务中，索引缺失/过期时**不要擅自 init/reindex**；`search` 会直接扫描当前
shards，或向用户报告需要安装。用户授权接入时才运行
`scripts/install_project.py`（见 [README.md](README.md)）。
完整 R→V→P→S 规则已经收在本技能包内，不依赖另装其他技能。

---

## 1. 你要干什么？选一条路

| 用户意图 | 你走的路径 | 禁止 |
|----------|------------|------|
| 「项目文档结构是什么」 | **只做 R**：`overview` 或读 `docs/INDEX.md` | 不要打开十几篇全文 |
| 「某某功能文档在哪 / 怎么设计的」 | **R**：`search` → **最多读 1～2 篇**碎片 | 不要 `find` 全部 md 读入 |
| 「我刚改了代码，文档跟上」 | **R→V→P→S 全走** | 不要跳过 `affected` 直接改 README |
| 「对面说做完了，文档也齐」 | **S 为主**（auditor）+ R 定位当前 docs | 不要只信作者摘要 |
| 「索引还健康吗」 | **只 S.validate** | — |

会话勾选清单：[templates/SESSION_CHECKLIST.md](templates/SESSION_CHECKLIST.md)。

---

## 2. 四步怎么做（可照抄）

### R — 定位（省 token）

```bash
python3 doc_memory.py overview
python3 doc_memory.py search "你的关键词" --limit 2
python3 doc_memory.py affected path/to/changed/code
```

- 只打开 **命中的 1～2 个** `docs/shards/**/*.md`。
- `history/cold/archive` 冷域默认不检索；用户点名或 hot 域无答案时才加
  `--include-cold`，并说明这是回退。
- 搜不到：换中英文关键词；再不行，在 INDEX 里按 domain 人工点一篇，仍不要整域灌入。
- 命令遇到损坏碎片会失败闭锁。只有诊断才可加 `--allow-partial`；不完整结果不能作为
  “确实没有”或验收通过的证据。

### V — 核对（求真）

1. 遵循 `VERIFY_CHECKLIST.md`，先读实际 diff 与最小实现/测试集合。
2. Trust order：**当前实现与可执行结果 > API/配置/schema > 测试/夹具 > 文档 > 作者摘要**。
3. 文档范围 = `affected` 结果 ∪ diff 推导，**禁止顺手改无关大文档**。
4. 规范/安全/产品契约冲突 → **问用户**，不静默改。

### P — 窄改

- 只改 V 锁定的文件。
- 有 frontmatter 则更新 `verified_at`（今天日期）。
- 写清：**改了什么 / 没改什么 / 仍 defer 什么**。

### S — 封口

```bash
python3 doc_memory.py reindex
python3 doc_memory.py validate   # 必须 0 error 才能说「文档同步完成」
```

若是**交接验收**：按 `HANDOFF_CHECKLIST.md` 填证据矩阵；Documentation
一行必须写**你实际读过的路径或 CLI 输出**。

---

## 3. 硬禁令（违反 = 本次文档任务失败）

1. 禁止默认整仓读 markdown。
2. 禁止默认读 history 冷域。
3. 禁止只凭作者摘要宣布交接通过。
4. 改代码后同步文档顺序固定：`affected → verify → patch → reindex`。
5. 禁止把 `--allow-stale` / `--allow-partial` 的降级输出当当前事实或完成证据。

---

## 4. 一个技能里的三个能力

| 名字 | 关系 |
|------|------|
| **Retrieve** | `doc_memory.py` 提供索引、检索与代码路径反查 |
| **Verify / Patch** | `VERIFY_CHECKLIST.md` 管文档是否对得上当前实现 |
| **Seal / Handoff** | `HANDOFF_CHECKLIST.md` 管完成声称是否有独立证据 |

安装一个 `doc-memory` 包即可运行完整闭环。其他文档同步或交接技能仍可作为
额外检查，但不是运行依赖。

---

## 5. 多 agent

- 业务代码：主开发 agent（如 Codex）为主。
- 文档闭环：执行 doc-memory 的 agent 负责 R/V/P/S。
- 两人同时改碎片：后写的人 `validate` 若报索引过期 → 先 `reindex` 再继续。

---

## 6. 宿主项目建议

使用 `scripts/install_project.py --root <项目> --with-agents-snippet` 先 dry-run；
用户确认后加 `--apply --init`。安装器会用标记区块幂等更新
`AGENTS.md`，并在改写已有文件前备份。

已有 Markdown 只在用户授权接入时走 `doc_memory.py migrate`：默认 dry-run，
`--apply` 只写 `docs/shards/imported` 派生副本，源文件必须保持不变。
