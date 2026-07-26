# doc-memory 技能包

`SKILL.md` 是 agent 入口，`HOW_TO_USE.md` 是人类操作说明。

本包自包含：

- `scripts/doc_memory.py`：零依赖检索/校验引擎；
- `scripts/install_skill.py`：dry-run 优先、升级前备份的技能安装器；
- `scripts/install_project.py`：dry-run 优先的项目安装器；
- `agents/openai.yaml`：Codex/ChatGPT 展示元数据；
- `references/`：R→V→P→S 调用约定；
- `templates/`：AGENTS 规则与会话检查单。

检索、事实核对、窄改和交接证据规则都已包含在本包中，无需再安装其他技能。
环境里已有的文档同步或交接工具可以作为额外复核，但不构成运行依赖。

## 安装技能

```bash
python3 doc-memory/scripts/install_skill.py
python3 doc-memory/scripts/install_skill.py --apply
```

若目标已存在且内容不同，安装器会闭锁。核对 SHA-256 后用
`--apply --force` 升级，旧目录会保留为带时间戳的 backup。

确认入口：

```bash
test -f ~/.codex/skills/doc-memory/SKILL.md
```

## 接入一个项目

```bash
# 默认 dry-run
python3 ~/.codex/skills/doc-memory/scripts/install_project.py \
  --root /path/to/project --with-agents-snippet

# 确认后执行
python3 ~/.codex/skills/doc-memory/scripts/install_project.py \
  --root /path/to/project --apply --with-agents-snippet --init
```

安全语义：

- 不同的现有 `doc_memory.py` 默认闭锁；有意替换才加 `--force`；
- AGENTS 规则通过唯一标记区块幂等维护；
- 改写已有 AGENTS 前先备份；
- CLI 单文件也能生成 shard 模板，不依赖仓库根 `templates/`。

## 不安装项目 CLI 也能只读调用

```bash
python3 ~/.codex/skills/doc-memory/scripts/doc_memory.py \
  --root /path/to/project search "关键词"
```

`search` 默认只返回 top-2；只有明确需要全部命中时才传 `--limit 0`。
若项目还没有 `docs/shards`，请先征得用户同意再安装/迁移，不要在只读问答中擅自写入。

## 升级

先比较项目 CLI 与新包内 CLI。安装器会显示 SHA-256；不同版本不会静默覆盖。
确认目标项目没有本地定制后再：

```bash
python3 ~/.codex/skills/doc-memory/scripts/install_project.py \
  --root /path/to/project --apply --force
```

升级后运行 `python3 doc_memory.py reindex && python3 doc_memory.py validate`。
