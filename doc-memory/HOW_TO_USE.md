# doc-memory 使用说明

## 它解决什么

doc-memory 把项目文档工作分成四步：

1. **R / Retrieve**：用小索引定位 1～2 篇；
2. **V / Verify**：对照实现、配置和测试；
3. **P / Patch**：只改已确认相关的文档；
4. **S / Seal**：重建索引、校验，并在交接时审计证据。

它节省的是模型上下文和错误写入，不追求比本地文本搜索更快。

## 三种常用说法

给 agent：

> 用 doc-memory 查“多灯”，默认不要读历史域，只打开最相关的 1～2 篇。

> 走 doc-memory 全流程同步这次代码改动：affected → 核对实现 → 窄改 → reindex → validate。

> 用 doc-memory 审计这次交接；不要只看作者总结，给出文档证据和阻断项。

## 只读检索

```bash
python3 doc_memory.py overview
python3 doc_memory.py search "多灯 multi light"
```

`search` 默认只返回 top-2；明确需要完整命中清单时才使用 `--limit 0`。
默认搜不到历史规格时，先判断任务是否真的需要历史；需要才：

```bash
python3 doc_memory.py search "多灯 multi light" --limit 2 --include-cold
```

如果 `overview` 报索引过期，纯读取任务不要擅自写入。可直接使用 live `search`，
或请项目所有者授权 `reindex`。`--allow-stale` 只用于诊断旧索引，不能当事实依据。

## 代码后同步

```bash
python3 doc_memory.py affected path/to/changed/code
```

然后按内置 `VERIFY_CHECKLIST.md` 对照当前实现，只改命中的文档与 diff
明确推导出的补充范围。
完成后：

```bash
python3 doc_memory.py reindex
python3 doc_memory.py validate
```

`validate` 为 0 error 只是技术封口；产品文案、架构决策和视觉验收仍需相应的人类判断。

## 存量迁移

```bash
python3 doc_memory.py migrate --source /path/to/docs       # dry-run
python3 doc_memory.py migrate --source /path/to/docs --apply
```

迁移只创建派生副本。自动生成的 `keywords` 和 `code_paths` 不是最终质量：

- 重要文档补中英文关键词；
- 把代码路径映射到真实仓内文件/目录；
- 对照实现后将 `migration_status` 从 `needs-review` 改为 `reviewed`。

## 失败模式

| 表现 | 含义 | 处理 |
|---|---|---|
| overview 非 0 | 索引缺失、损坏或过期 | 授权写入后 reindex |
| search/affected 非 0 | 至少一个 shard 无法可靠读取 | 修复；诊断才用 `--allow-partial` |
| 无命中但命令为 0 | 完整热域中没有字面命中 | 换同义词，再按需 include-cold |
| validate 只有 needs-review warn | 迁移副本可用但尚未人工整理 | 逐篇复核元数据 |
| affected 无命中 | `code_paths` 尚未维护或路径不覆盖 | 补映射，不要猜写入范围 |

## 适用与不适用

适合：

- 20 篇以上、常有历史文档的项目；
- 多 agent 协作；
- 需要证明“文档确实同步”的交接。

收益较小：

- 只有几篇短文档的小项目；
- 内容主要是 PDF/Office 文件；
- 需要向量语义检索、多人文档服务或 Web UI 的场景。
