# Contributing

感谢你帮助改进 Docs as Memory。

## 开始前

1. 先搜索已有 issue，说明真实场景、预期结果和实际结果。
2. 修复尽量保持小而可复现，不要顺手重写无关文档。
3. 不要提交真实项目私密文档、访问令牌、绝对个人路径或未获授权的数据。

## 本地验证

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q doc_memory.py doc-memory tests tools
python3 doc_memory.py --root fixtures/demo_project validate
```

如果修改了根 `doc_memory.py`，必须同步修改
`doc-memory/scripts/doc_memory.py`；测试会要求两者字节一致。

涉及检索效果或 token 宣称的变更，请遵循 [TOKEN_EVAL.md](specs/TOKEN_EVAL.md)
并提交原始命令、加载路径和绝对数字。

## Pull request

- 说明解决的问题和范围；
- 列出实际运行的验证；
- 明确没有验证的系统或场景；
- 文档、实现和示例必须保持一致；
- 所有贡献按本仓库 MIT License 发布。
