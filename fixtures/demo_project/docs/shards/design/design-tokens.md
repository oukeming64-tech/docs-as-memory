---
title: 设计 token
summary: 颜色、间距、字阶的 token 定义与同步流程。
keywords: [design, tokens, 设计]
domain: design
code_paths: [web/src/styles/]
trust_level: 3
verified_at: "2026-05-25"
---

# 设计 token

## 概述

设计 token 源文件在 `web/src/styles/tokens.ts`，设计稿工具单一事实源。

## 分层

- 基础 token：色板、间距刻度、字阶（原始值）。
- 语义 token：`text-primary`、`surface-raised` 等，引用基础 token。

## 同步流程

1. 设计在 Figma 改 → 2. 导出 JSON → 3. 脚本生成 tokens.ts → 4. PR 评审。
- 禁止手改 tokens.ts；diff 必须由导出脚本产生。

## 暗色模式

- 语义 token 双值（light/dark），运行时切换，不另出一份组件。

## 边界

- 组件内禁止出现字面值颜色（见 frontend/web-ui-components）。
- 新增语义 token 需要设计 + 前端双人会签。

## 相关

- 组件规范见 `frontend/web-ui-components.md`。
