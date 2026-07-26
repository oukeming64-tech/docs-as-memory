# CALL_ENGINE — 如何调用 doc-memory 引擎（Retrieve / Seal 子系统）

Docs as Memory 是 doc-memory 的**自有子系统**（技能包 `scripts/doc_memory.py`；
本仓兼容入口 `doc_memory.py`），可以维护；
它**不是**上游只读技能。

## 位置

- 安装后 CLI：宿主项目根 `doc_memory.py`；未安装时可用技能包内置 CLI 配合 `--root`。
- 规范：`specs/shard-format.md`、`specs/index-schema.md`。
- Token 规则：`specs/TOKEN_EVAL.md`（唯一量尺
  `est_tokens = ceil(normalized_utf8_bytes/4)`）。

## 命令速查

```bash
python3 doc_memory.py overview                          # R：只打印新鲜 L0
python3 doc_memory.py search "鉴权 token" --limit 2     # R：热域检索
python3 doc_memory.py search "旧规格" --include-cold    # R：显式冷域回退
python3 doc_memory.py affected src/auth/                # R：代码路径反查碎片
python3 doc_memory.py reindex                           # S：改碎片后重建索引（原子写）
python3 doc_memory.py validate                          # S：体检；error≠0，仅 warn=0
python3 doc_memory.py migrate --source docs-old         # 接入：默认 dry-run
```

- `--root DIR` 指定宿主项目根（默认当前目录）。
- search 支持 `--json`、`--limit N`；search/affected 支持
  `--include-cold`、`--exclude-glob`。
- 读取损坏 shard 时默认 exit 1；只有诊断可显式 `--allow-partial`。
- overview 遇过期索引默认 exit 1；`--allow-stale` 仅用于诊断。
- 退出码：0 正常；1 数据/校验错误；2 用法/路径安全错误。

## 冷域约定（v1）

- `history|cold|archive` domain 或同名路径段默认排除，防 history 巨石污染 top-k。
- 点名历史或热域无答案时才加 `--include-cold`；额外路径规则仍可用
  `--exclude-glob`（可多次）。

## 纪律

- 索引只能由 `reindex` 生成，禁止手改 `docs/INDEX.md` / `docs/index.json`。
- 改了任何碎片必须 `reindex`；`validate` 用内容哈希检测过期。
- L0 自动选择 full/compact/domains/minimal，`validate` 硬检查 ≤1500 est_tokens。
- `migrate` 默认不写，`--apply` 也只写派生 shard；源文件不得改变。
- 演示与回归夹具：`fixtures/demo_project/`（27 碎片）。
