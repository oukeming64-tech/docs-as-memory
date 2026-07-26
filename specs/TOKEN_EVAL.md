# Token 验收规则（防自欺）

- 版本：v1.2（量尺公式不变；scripted_path 明确按任务卡 top_k 限制 search 输出）
- 状态：**修复前 Kimi/Grok 双跑复现 AC-1 回归；v0.1.1 Codex 工程回归通过，
  修复后的正式 Kimi/Grok 双端重跑仍是公开路线图项目**
- 适用：AC-1、AC-5 及一切「省 token」宣称
- 原则：涉及 token 的数字 **禁止单方口述**；必须 **同一套量尺 + 双人各跑 + 留原始输出**

---

## 1. 为什么单独立规

「感觉少读了很多」「模型说大约省了 70%」**一律不算数**。
token 相关结论最容易：

- 测的人知道答案，只读了碰巧很小的子集
- baseline 选得虚高（把从不该整读的垃圾也算进去）
- 用「字符÷4」和另一边「真实 tokenizer」混比
- 只跑一次、只一方跑、改完夹具不重跑

故：**Grok 与 Kimi 必须各自完整跑同一套 token 评测**；数字对不上先查流程，再谈产品。

---

## 2. 谁跑什么

| 角色 | 必须做 | 禁止 |
|------|--------|------|
| **Kimi** | 实现后跑 **Run-K**，把原始日志写入约定路径 | 只交「结论段落」无 raw |
| **Grok** | 在 Kimi 交付后 **独立再跑 Run-G**（不复制 Kimi 的结果表充数） | 用「我看了代码觉得没问题」代替实跑 |
| **Codex** | 终审时抽查：规则是否被遵守、两边报告是否齐全 | 不替双方重做全套，除非抽查失败 |
| **所有者** | 可指定任务句、可否改夹具 | — |

**通过条件（token 类 AC）：**
`Run-K` 与 `Run-G` **都**对同一 `fixture_id` + 同一 `task_id` 给出可复现数字，且 **相对误差 ≤10%**（见 §6）；两边都达标才算 AC 过。

一方未跑 = **该 AC 未完成**，不得在 STATUS 写「已通过」。

Codex 可用 `runner=codex` 生成工程回归报告，用于在提交前发现退化；它不进入
Kimi/Grok 双端一致性计算，也不能单独把 token AC 判为正式通过。

---

## 3. 统一量尺（禁止混用）

### 3.1 唯一估算公式（v1）

在未引入第三方 tokenizer 库的前提下（与「零依赖」一致），**全项目只允许一种**文档 token 估算：

```text
est_tokens = ceil(normalized_utf8_byte_length / 4)
```

- 对象：将要进入模型上下文的 **文档字节**（见 §4 计入范围）
- 编码：UTF-8
- 换行：计算前把 CRLF 和 CR 规范为 LF，避免 Windows/macOS 仅因 checkout
  换行不同而得到不同量尺
- 实现：评测脚本或 CLI 子命令必须打印 `normalized_utf8_bytes` 与
  `est_tokens`，禁止只打印百分比

> 说明：这不是 billable API token 的精确值，而是 **可复现的相对量尺**。
> 宣称「省额度」时必须写明：`method=normalized_utf8_bytes/4`。
> 若未来要改公式，升本文件版本，并 **作废** 旧报告。

### 3.2 禁止

- 心算、Chat 窗口里让模型估 token
- 中英混用不同公式
- baseline 用公式 A、atlas 路径用公式 B
- 只报百分比不报绝对 `est_tokens`

---

## 4. 计入范围（什么算「文档 token」）

### 4.1 Baseline（整读对照）

固定评测仓内，下列全部拼接并规范换行后算 `normalized_utf8_bytes`：

- `docs/shards/**/*.md` 的 **完整文件**（含 frontmatter）
- **不含** `docs/INDEX.md` / `docs/index.json`（baseline 假设「没有 Docs as Memory」时 agent 直接啃碎片全集；若夹具还有未拆大文档，则那些大文档全文也计入——夹具清单写死）

### 4.2 Atlas 路径（省读路径）

只计 agent **实际加载** 的文档字节之和：

1. L0：`docs/INDEX.md` 全文（若任务要求先 overview，则计入）
2. 若调用了 `search` / `affected`：计 **CLI 打印给 agent 的输出**（stdout 原文），**不计** 未被读的碎片正文
3. 再计 agent **打开/read 的每个 shard 全文**

**不计：**

- 源代码（除非任务明确要求读代码；token AC 默认只评 **文档子系统**）
- `index.json` 整文件（除非 agent 真的 read 了它；规范鼓励用 CLI，若 read 了则计入）
- SKILL.md / PRD 等本工具仓库说明（评测宿主是 `fixtures/demo_project`）

### 4.3 任务脚本化（防「我知道该读哪篇」）

每个 token 任务必须有 **冻结的 task 卡**（见 `fixtures/eval/tasks/`，实现阶段创建），至少包含：

| 字段 | 含义 |
|------|------|
| `task_id` | 如 `T-auth-locate` |
| `prompt` | 给 agent 的唯一用户句（双方一字不改） |
| `allowed_tools` | 允许：doc-memory CLI、read 文件；是否允许 grep 全仓要写死 |
| `success_criteria` | 如：最终引用的 shard path 集合 ⊆ 期望集合，且答对一个事实探针 |
| `baseline_mode` | `all_shards`（默认） |

**禁止** 评测者在跑的时候口头补充「你去看 auth 那篇」。

---

## 5. 标准任务（v1 最少集）

实现夹具后必须具备（名称可同，定义不可漂）：

| task_id | 目的 | 对应 AC |
|---------|------|---------|
| `T-l0-budget` | 只测量 L0 `INDEX.md` 的 `est_tokens` | AC-5 |
| `T-auth-locate` | 从「需要鉴权/登录相关文档」类 prompt 定位并读最少碎片，回答探针 | AC-1 |
| `T-affected-auth` | 给定 `src/auth/`，用 `affected` 再读碎片 | AC-6 + 辅助 AC-1 |

`T-l0-budget` **不经过模型**也可：直接对 `INDEX.md` 跑量尺脚本 → 仍须 Kimi、Grok **各自执行脚本** 并交日志（防一方改夹具未重跑）。

`T-auth-locate` 若用 agent 实机：双方用 **同一 prompt、同一 fixture 提交哈希**；
若暂不用 agent、用「规范路径模拟」（只允许 INDEX +
`search --limit <top_k>` 输出 + 打开 top-k 正文），须在报告写明
`mode=scripted_path`，且双方 mode 必须相同。

---

## 6. 通过线与双端一致性

| 检查 | 阈值 |
|------|------|
| AC-5 L0 | `est_tokens(INDEX.md) ≤ 1500` |
| AC-1 节省 | `atlas_est / baseline_est ≤ 0.30`（文档 token） |
| 双端一致 | 对同一 task：`|K - G| / max(K,G,1) ≤ 0.10` |
| 探针正确 | `success_criteria` 满足（省 token 但答错 = **失败**） |

任一项失败：AC 失败，STATUS 记原因；允许修夹具/实现后 **整 task 重跑双方**，不得只重跑失败的一方凑数。

---

## 7. 报告格式（强制）

每次 Run 在主区写入：

```text
fixtures/eval/reports/<runner>-<YYYYMMDD>-<task_id>.md
```

正式双端报告的 `runner` ∈ `kimi` | `grok`。工程回归可用 `codex`，但必须在
结论中明确“不计入正式双端验收”。

报告模板：

```markdown
# Token eval report

- runner: kimi | grok
- date: ISO-8601
- fixture_id: demo_project@<git_or_content_hash>
- task_id: T-...
- method: normalized_utf8_bytes/4
- mode: agent | scripted_path

## Absolute numbers
- baseline_normalized_utf8_bytes:
- baseline_est_tokens:
- atlas_normalized_utf8_bytes:
- atlas_est_tokens:
- ratio: atlas_est / baseline_est

## Loaded paths (ordered)
1. ...
2. ...

## CLI raw (paste or path to .log)
...

## Probe
- question:
- answer:
- pass: true|false

## Notes
...
```

汇总表（可后写）：

```text
fixtures/eval/reports/SUMMARY.md
```

由 **后跑完的一方** 或 Grok 中检时合并：并排 K/G 数字与是否双过。

---

## 8. 内容哈希（防偷换夹具）

报告必须含 `fixture_id`：

- 对 `fixtures/demo_project/docs/shards` 下所有文件做稳定排序后的内容哈希
- 推荐：标准库 `hashlib.sha256` 串联
  `path + b'\\n' + normalized_file_bytes`，其中换行先规范为 LF
- K 与 G 的 hash **必须相同** 才允许比数字；不同则先对齐夹具再跑

---

## 9. 自欺清单（出现即作废）

- [ ] 没有 raw CLI / 没有 loaded paths
- [ ] 只有百分比
- [ ] 只有一方报告
- [ ] baseline 含了 atlas 不该比的巨型无关二进制/PDF
- [ ] 评测前「优化」了 INDEX 专为压 AC-5、却让 search 不可用
- [ ] 改完 shard 只重跑 Grok 或只重跑 Kimi
- [ ] 用模型口头估 token

---

## 10. 与 PRD 的挂钩

| AC | 本文件章节 |
|----|------------|
| AC-1 | §4–§7，`T-auth-locate` |
| AC-5 | §3、§5 `T-l0-budget` |
| AC-6 | `T-affected-auth`（正确性 + 可附带 token 附录） |

实现阶段应提供 **可复现命令**（示例，非现在已有）：

```bash
python3 tools/token_measure.py --runner kimi --task T-l0-budget
python3 tools/token_measure.py --runner kimi --task T-auth-locate
```

具体入口以实现为准，但 **method 与报告字段不得违反本文**。

---

## 11. 当前状态

- [x] 规则写入文档
- [x] 夹具与 task 卡
- [x] measure 脚本
- [x] 历史 Kimi Run-K
- [x] 历史 Grok Run-G
- [x] 历史 SUMMARY 双过
- [x] Codex 独立真实副本回归（59 篇，见
  `fixtures/eval/reports/real-docs-benchmark-2026-07-26.md`）
- [x] 修复前 public alpha 的 Kimi/Grok 双跑（同夹具、数字一致，AC-1
  `0.3266` 失败）
- [x] v0.1.1 Codex 工程回归（AC-1 `0.2555`，探针通过）
- [ ] v0.1.1 修复后的 Kimi/Grok 正式双端重跑

历史与修复前报告证明的是当时的 CLI/fixture 提交，不能覆盖当前行为。Codex
工程回归用于工程硬化和产品判断，不冒充本文件要求的双人 token 验收。
