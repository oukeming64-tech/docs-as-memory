# Docs as Memory

[![CI](https://github.com/oukeming64-tech/docs-as-memory/actions/workflows/ci.yml/badge.svg)](https://github.com/oukeming64-tech/docs-as-memory/actions/workflows/ci.yml)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-%E2%89%A53.9-3776AB.svg)](https://www.python.org/)

**Turn a documentation-heavy repository into small, verifiable working memory for AI coding agents.**

一个本地、零第三方依赖的 agent 技能：让 AI 面对文档比代码还多的项目时，
先准确定位，再核对事实，只改相关文档，最后用可复现证据封口。

> 当前版本：`0.1.0` public alpha。适合真实项目试用，但尚未承诺稳定 API。

## 为什么做它

AI 开发项目常常只有少量正式代码，却堆积了核对文档、交接文档、审计记录、
历史方案和发布说明。新增一个需求或修一个错误时，agent 如果重新读取全部 Markdown，
既浪费上下文，也更容易引用旧版本或改错文件。

Docs as Memory 把文档工作固定成一个闭环：

```text
R Retrieve  →  V Verify  →  P Patch  →  S Seal
少读定位        对照实现      窄范围写入      重建索引并验收
```

- `doc-memory` 是安装后的技能名；
- `doc_memory.py` 是技能自带的确定性索引和校验引擎；
- 完整闭环已经包含检索、事实核对、窄改和交接证据规则，不依赖云服务、数据库或
  其他技能。

## 已验证的效果

2026-07-26，我们把四个真实目录的 59 篇 Markdown 复制到隔离临时目录后测试，
没有修改原文档：

| 指标 | 结果 |
|---|---:|
| 原文档 SHA-256 保持不变 | 59 / 59 |
| 默认热域查询命中 | 11 / 14 |
| 显式冷域回退后命中 | 14 / 14 |
| 中位上下文节省 | 74.6% |
| `affected` 人工维护映射 | 4 / 4 唯一命中 |
| L0 上限 | ≤ 1,500 est_tokens |

这里的 `est_tokens = ceil(normalized UTF-8 bytes / 4)` 会先把 CRLF/CR
换行规范成 LF，是可复现的上下文体量指标，
不是 API 账单 token。工具并没有让本地文本搜索更快；它减少的是 agent 需要加载的
文档量，并把“改哪篇、何时算同步完成”变成可验证流程。

完整报告见
[real-docs-benchmark-2026-07-26.md](fixtures/eval/reports/real-docs-benchmark-2026-07-26.md)。

## 安装技能

```bash
git clone https://github.com/oukeming64-tech/docs-as-memory.git
cd docs-as-memory

# 先预演：不会写入
python3 doc-memory/scripts/install_skill.py

# 确认后安装到 ~/.codex/skills/doc-memory
python3 doc-memory/scripts/install_skill.py --apply
```

若已有不同版本，安装器会先闭锁。确认升级时使用 `--apply --force`，旧目录会保留
带时间戳的备份。其他 agent 可通过 `--skills-root` 指定自己的技能目录。

## 接入一个项目

```bash
# 先预演，不改目标项目
python3 ~/.codex/skills/doc-memory/scripts/install_project.py \
  --root /path/to/project --with-agents-snippet

# 确认后安装单文件引擎、添加幂等 AGENTS 规则并初始化
python3 ~/.codex/skills/doc-memory/scripts/install_project.py \
  --root /path/to/project --apply --with-agents-snippet --init
```

两个安装器都默认 dry-run。不同的现有文件不会被静默覆盖；更新已有
`AGENTS.md` 前会创建备份。

## 日常使用

```bash
python3 doc_memory.py overview
python3 doc_memory.py search "鉴权 token" --limit 2
python3 doc_memory.py search "旧规格" --include-cold
python3 doc_memory.py affected src/auth/
python3 doc_memory.py reindex
python3 doc_memory.py validate
```

也可以直接告诉 agent：

> 用 doc-memory 查“鉴权刷新”，默认不要读历史域，只打开最相关的 1～2 篇。

> 走 doc-memory 全流程同步这次代码改动：affected → 核对实现 → 窄改 →
> reindex → validate。

> 用 doc-memory 审计这次交接，不要只看作者总结，给出证据矩阵和阻断项。

更完整的人类说明见 [HOW_TO_USE.md](doc-memory/HOW_TO_USE.md)，agent 入口见
[SKILL.md](doc-memory/SKILL.md)。

## 安全边界

- `migrate` 默认只列计划；`--apply` 只向 `docs/shards/imported` 写派生副本；
- 迁移不修改、不移动、不删除源文档，并记录源 SHA-256；
- `overview` 遇到旧索引默认失败闭锁；
- `search/affected` 遇到损坏 shard 默认失败闭锁；
- `--allow-stale` 和 `--allow-partial` 只允许诊断，不能作为完成证据；
- `reindex` 使用原子写；`validate` 必须 0 error 才能宣称文档闭环完成。

存量文档迁移细节见 [MIGRATION.md](MIGRATION.md)。

## 文档结构

| 层 | 文件 | 用途 |
|---|---|---|
| L0 | `docs/INDEX.md` | 小地图，动态控制在 1,500 est_tokens 内 |
| 机器索引 | `docs/index.json` | 关键词、代码路径、内容哈希与 L0 模式 |
| Shards | `docs/shards/**/*.md` | 一事一片，按任务只打开少量正文 |

## 适用范围与限制

适合 Markdown 较多、历史文档明显、多 agent 协作且重视交接证据的个人或小团队项目。

当前限制：

- 只处理本地 UTF-8 Markdown；
- 是确定性词法检索，不是 embedding 语义检索；
- `code_paths` 需要人工维护，`affected` 才能准确反查；
- 只有几篇短文档时，建立索引的收益有限；
- 当前真实文档报告由 Codex 独立运行，正式 Kimi/Grok 双端重跑仍在公开路线图中。

## 仓库结构

```text
doc-memory/                 可直接安装的完整技能包
doc_memory.py              开发与兼容入口，和包内引擎字节一致
tests/                     安全、迁移、安装与索引回归
fixtures/demo_project/     27 篇 shard 的可复现示例项目
fixtures/eval/             评测任务、规则与公开报告
specs/                     shard、索引和 token 量尺规格
```

## 参与贡献

欢迎提交最小、可复现的 issue 或 pull request。请先阅读
[CONTRIBUTING.md](CONTRIBUTING.md)；安全问题请按 [SECURITY.md](SECURITY.md)
私下报告。

## License

[MIT](LICENSE) © 2026 oukeming64-tech
