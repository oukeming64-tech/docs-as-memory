---
title: 埋点事件规范
summary: 事件命名、属性规范与新事件上线流程。
keywords: [data, analytics, 埋点, 事件]
domain: data
code_paths: [src/analytics/]
trust_level: 2
verified_at: "2026-07-12"
---

# 埋点事件规范

## 概述

埋点 SDK 在 `src/analytics/`，前后端共用事件规范。

## 命名

- `{对象}_{动作}`，蛇形小写：`project_created`、`onboarding_step_skipped`。
- 禁止动态拼接事件名。

## 属性规范

- 必带：`user_id`、`ts`、`source`（web/api）。
- 禁止携带 PII；金额类用「分」为单位的整数。

## 新事件上线流程

1. 本文档登记 → 2. 评审 → 3. 实现 → 4. 灰度环境验证数据 → 5. 上线。

## 边界

- 事件 schema 变更只允许加属性，不允许改含义；语义变了就起新事件名。
- 路由切换不打点（见 frontend/web-routing）。

## 相关

- 引导漏斗依赖本文事件，见 `product/onboarding-flow.md`。
