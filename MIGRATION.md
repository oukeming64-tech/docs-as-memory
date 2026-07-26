# MIGRATION — 存量 Markdown 安全迁移

v1.1 提供**机械迁移**，不承诺自动把长文智能拆成完美碎片。默认原则：

1. 先 dry-run；
2. 只写派生副本；
3. 源文件不改、不移、不删；
4. 自动元数据明确标记为待复核。

## 1. 先预演

```bash
python3 doc_memory.py --root /path/to/project migrate \
  --source /path/to/existing/docs
```

`--source` 可以是单个 `.md` 或目录，也可以位于项目外。默认只列清单，不创建
`docs/`。工具不跟随目录符号链接，并默认排除 `.git`、`node_modules`、构建目录、
虚拟环境和已有 `docs/shards`。

可选项：

```bash
--domain product                  # 生成的 domain，默认 imported
--exclude-glob "history/**"       # 可重复
--max-files 200                   # 安全上限；默认 500，0=不限
--json                            # 机器可读清单
```

## 2. 确认后写派生副本

```bash
python3 doc_memory.py --root /path/to/project migrate \
  --source /path/to/existing/docs \
  --domain product \
  --apply
```

写入位置固定为：

```text
docs/shards/imported/<source-name>/**/*.md
```

同名目标存在时整批闭锁，不会半覆盖。只有确认要替换**派生副本**时才可加
`--force`。每个生成文件包含：

- 自动提取的 `title` / `summary` / `keywords`；
- `source_path`；
- 原文件 `source_sha256`；
- `migration_status: needs-review`；
- 原文正文的完整副本。

完成后会自动 `reindex`。`validate` 只汇总一条 needs-review 警告，避免几十行噪声。

## 3. 人工整理是必需步骤

机械迁移后逐篇处理高价值文档：

1. 校正 `title`、`summary`；
2. 给 `keywords` 补中英文同义词；
3. 填真实仓内 `code_paths`，使 `affected` 能定位写入范围；
4. 对照实现确认内容；
5. 把 `migration_status` 改为 `reviewed`；
6. 若确实完成核对，再写当天 `verified_at`。

不要把自动复制日期当成内容已验证日期。

## 4. 冷域

历史、归档类文档放在 `domain: history|cold|archive`，或路径中使用同名目录。它们：

- 在 L0 中只显示汇总；
- 默认不进入 `search` / `affected`；
- 用户点名时通过 `--include-cold` 显式读取。

当前规格若只存在于 history，必须保留一篇 hot 摘要或在任务中明确回退冷域。

## 5. 封口

```bash
python3 doc_memory.py reindex
python3 doc_memory.py validate
python3 doc_memory.py overview
python3 doc_memory.py search "<常见查询>" --limit 2
python3 doc_memory.py affected <一条真实代码路径>
```

完成标准：

- `validate` 为 0 error；
- L0 不超过 1500 est_tokens；
- 3～5 个常用查询命中正确；
- 抽样 `affected` 命中应同步的碎片；
- 所有源文件哈希保持不变。

## 6. 什么时候手工拆分

机械的一文件一片只适合作为过渡。出现以下情况应继续拆：

- 一篇同时回答多个无关问题；
- top-1 命中了正确文件，但读取它仍占项目文档的大部分；
- summary 无法在约 80 字内解释清楚；
- 正文长期超过约 150 行且常被局部引用。

拆分后保留一个短导读片，不要删除原文，除非用户另行决定归档策略。
