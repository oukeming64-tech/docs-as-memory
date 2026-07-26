# Workflow walkthrough

下面四个例子展示 `doc-memory` 如何短路或完成 R→V→P→S。命令假设项目已接入
`doc_memory.py` 和 `docs/shards`。

## 1. 新会话只要文档地图

```bash
python3 doc_memory.py overview
```

读取 L0 后先停止。只有具体问题需要下钻时，才打开一两篇 shard。

## 2. 查询一个事实

```bash
python3 doc_memory.py search "限流 配额" --limit 2
```

打开命中最高的 shard，回答问题；若文档与当前实现疑似冲突，进入 Verify。没有漂移
也不需要写入时，P 和 S 可以合法跳过。

## 3. 代码改动后同步

```bash
python3 doc_memory.py affected src/auth/
```

1. 把命中 shard 与实际 diff 合并成候选范围；
2. 按 `references/VERIFY_CHECKLIST.md` 对照实现、配置和测试；
3. 只修改被证据确认已漂移的文档；
4. 运行 `reindex` 与 `validate`。

```bash
python3 doc_memory.py reindex
python3 doc_memory.py validate
```

只有 `validate` 为 0 error，且没有待用户裁决的契约冲突，才能说文档闭环完成。

## 4. 审计别人声称“已经做完”

1. 先把声称拆成可验证 claim；
2. 查看当前文件和 diff，运行相关测试；
3. 用 `overview/search` 定位当前文档；
4. 运行 `validate`；
5. 按 `references/HANDOFF_CHECKLIST.md` 填证据矩阵；
6. 输出 `PASS` 或 `BLOCKED`，并列出最小修复项。

作者摘要只能帮助导航，不能作为完成证据。
