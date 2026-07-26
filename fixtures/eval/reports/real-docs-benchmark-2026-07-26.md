# Docs as Memory 真实文档副本基准

- 日期：2026-07-26
- 执行者：Codex
- 环境：隔离临时副本
- 方法：`est_tokens = ceil(normalized_utf8_bytes/4)`；本次样本为 LF，数字不变
- 边界：这是 public alpha 检索核心的 Codex 独立回归，不冒充
  TOKEN_EVAL 要求的 Kimi/Grok 正式双端重跑

## 1. 样本与原件保护

从四个真实目录按旧实验冻结清单复制 59 篇 Markdown 到临时目录：

| 来源 | 文档数 | UTF-8 bytes | est_tokens |
|---|---:|---:|---:|
| 自动化项目 | 8 | 24,910 | 6,228 |
| 图形工具项目 | 38 | 532,397 | 133,100 |
| 游戏项目 | 9 | 33,719 | 8,430 |
| 汇报材料目录 | 4 | 21,852 | 5,463 |
| **合计** | **59** | **612,878** | **153,220** |

- 迁移前：原件与临时副本 59/59 SHA-256 一致。
- 迁移、检索、临时写入和封口后：原件与临时副本仍 59/59 一致。
- 测试写入只发生在 Docs as Memory 生成的派生 shard。
- PDF/XLSX/PPTX 未纳入：当前产品只支持 UTF-8 Markdown。

## 2. 安装与迁移

1. `migrate` 默认 dry-run，确认 `docs/` 不存在，写入数为 0。
2. 四组 `--apply` 共生成 59 个派生 shard，并记录源 SHA-256。
3. `validate`：0 error，1 条聚合 warning（59 个 `needs-review`），没有 59 行噪声。
4. 单文件 CLI 在没有外部 `templates/` 时，`init` 仍会生成 `_TEMPLATE.md`。
5. 技能包包含 bundled CLI、安装器和 `agents/openai.yaml`。

## 3. L0 预算

| 项目 | 本次版本 L0 est_tokens | 模式 |
|---|---:|---|
| 自动化项目 | 454 | full |
| 图形工具项目 | 831 | full（21 篇 history 折叠） |
| 游戏项目 | 506 | full |
| 汇报材料目录 | 366 | full |
| 四组合并实验 | 1,044 | compact |

图形工具项目的旧实验 L0 为 1,996；本次版本降到 831，减少 58.4%，并由
`validate` 硬检查不超过 1,500。

## 4. 14 个真实查询

固定 top-2；history/cold 默认关闭，未命中目标时显式 `--include-cold`：

| 项目 | 任务数 | 默认命中 | 回退后 | 平均加载全文 | 平均节省 |
|---|---:|---:|---:|---:|---:|
| 自动化项目 | 3 | 3 | 3 | 51.7% | 48.3% |
| 游戏项目 | 4 | 4 | 4 | 24.9% | 75.1% |
| 汇报材料目录 | 2 | 2 | 2 | 74.0% | 26.0% |
| 图形工具项目 | 5 | 2 | 5 | 8.1% | 91.9% |

- 合计：默认 11/14；冷域回退后 14/14。
- 中位加载：25.4%；中位节省：74.6%。
- 平均加载：31.7%；平均节省：68.3%。
- 中位查询墙钟：31.3 ms（含 Python 启动）；旧实验约 26.2 ms。

结论：本次版本没有提高本地搜索速度，甚至因 body 检索和安全检查略慢；它提高的是
安装/迁移可靠性、L0 可控性和写入范围确定性。只有 4 篇长文档的目录收益仍有限。

## 5. 写入闭环

机械迁移不会自动猜 `code_paths`。在临时副本人工维护 4 组真实映射后：

| 映射 | affected 结果 | 中位墙钟 |
|---|---|---:|
| 自动化参数 → 对应渲染脚本 | 唯一命中 | 31.0 ms |
| 角色认知文档 → 对应实现 | 唯一命中 | 31.3 ms |
| 合约测试文档 → 对应 guard | 唯一命中 | 29.8 ms |
| 渲染规范 → 对应数据实现 | 唯一命中 | 33.4 ms |

在图形工具项目的 38 篇派生 shard 上做一次临时窄写：

- stale `overview`：exit 1，37.7 ms；
- stale `validate`：exit 1，36.2 ms；
- `reindex`：36.5 ms；
- final `validate`：35.9 ms；
- 封口合计：72.4 ms；
- 被抽样的原始规范文件与临时源副本哈希仍一致。

旧实验封口约 58.4 ms，因此“写入效率提高”不能解释成命令更快。可验证的提升是：
先由 `affected` 唯一定位目标，再由 stale 闸门防止旧索引被误当成功，最后 72 ms 左右完成封口。

## 6. 安全回归

本报告生成时的 14 项回归全部通过；开源整理后扩展为 19 项，本地 19/19 通过，
跨平台结果以 CI 为准。覆盖：

- scalar title 不再导致 search traceback；
- `..\` 和符号链接路径逃逸被拒绝；
- 损坏 shard 默认闭锁，`--allow-partial` 明示降级；
- stale overview 默认闭锁；
- 冷域显式 opt-in；
- 超大 L0 动态折叠到预算；
- migrate dry-run、源哈希不变、冲突保护；
- 重复字段、symlink shard、managed docs symlink 闭锁；
- bundled CLI 与根开发入口字节一致；
- 技能/项目安装器 dry-run、备份、幂等 AGENTS 标记、自包含 init。

## 7. GitHub 对照定位

| 项目 | 可借鉴强项 | 与 doc-memory 的边界 |
|---|---|---|
| Aider repo map | 动态 token 预算、代码结构排序 | 面向代码地图，不负责文档写回与交接 |
| Grounded Docs MCP | 文档摄取、搜索、访问根边界 | 服务化和检索更强，部署更重 |
| Context7 | 外部库的版本化文档、低摩擦 CLI/MCP 安装 | 不管理私有项目文档写回 |
| Repomix | 仓库打包、压缩、token 统计 | 适合一次性喂上下文，不做 R→V→P→S |

本次版本 吸收了动态预算、allowed-root/fail-closed 和幂等安装三个模式；没有引入
embedding、数据库、云服务或 MCP，以保持本地、零依赖和可审计。

参考：

- https://aider.chat/docs/repomap.html
- https://github.com/arabold/docs-mcp-server
- https://github.com/upstash/context7
- https://github.com/yamadashy/repomix

## 8. 判定

适合：个人/小团队本地 public alpha、Markdown 较多、历史域明显、
多 agent 交接严格的项目。

已经具备 MIT 许可证、Git 仓和跨平台 CI，仍不应称为稳定版：

1. 当前检索核心的 Kimi/Grok 正式双端重跑未做；
2. 非 Markdown 格式和语义检索不支持；
3. `code_paths` 仍需要人工维护；
4. public alpha 的 CLI 与索引格式尚未承诺长期兼容。
