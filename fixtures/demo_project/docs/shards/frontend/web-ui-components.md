---
title: UI 组件库约定
summary: 组件分层、样式方案与新增组件 checklist。
keywords: [frontend, component, 组件]
domain: frontend
code_paths: [web/src/components/]
trust_level: 3
verified_at: "2026-04-15"
---

# UI 组件库约定

## 概述

组件目录 `web/src/components/` 分三层：

- `base/`：无业务含义（Button、Modal）。
- `biz/`：业务组件（InvoiceCard）。
- `page/`：页面级组装，不进组件库文档。

## 样式

- Tailwind utility-first；禁止新增全局 CSS 文件。
- 设计 token 在 `web/src/styles/tokens.ts`，颜色禁止字面值。

## 新增组件 checklist

1. 放对层级（base/biz/page）。
2. props 全部显式类型，不用 `any`。
3. 交互组件配 keyboard 可达性。
4. base 组件必须有 story。

## 边界

- 超过 300 行的组件必须拆分。
- 第三方组件库只许引入头部制定的白名单。

## 相关

- 状态管理见 `web-state-store.md`。
