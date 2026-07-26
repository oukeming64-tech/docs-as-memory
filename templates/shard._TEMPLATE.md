---
title:                    # 必填，短标题
summary:                  # 必填，≤80 中文字，供 L0 索引展示
keywords: []              # 必填，中英都写；检索主依赖
domain:                   # 必填，slug，如 backend / frontend / product / ops
code_paths: []            # 建议，仓内相对路径，禁止绝对路径、.. 与符号链接逃逸
trust_level: 4            # 建议，1=实现真相 2=API契约 3=测试 4=叙述文档
verified_at: "YYYY-MM-DD" # 可选，超 90 天 validate 会 warn（注意加引号）
---

# 标题

一事一碎片，正文建议 ≤150 行。改完必须 `python3 doc_memory.py reindex`。
