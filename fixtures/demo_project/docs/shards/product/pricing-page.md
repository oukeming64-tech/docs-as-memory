---
title: 定价页
summary: 套餐档位展示、试用规则与定价变更流程。
keywords: [product, pricing, 定价, 套餐]
domain: product
code_paths: [web/src/pricing/]
trust_level: 4
verified_at: "2026-07-08"
---

# 定价页

## 概述

定价页实现 `web/src/pricing/`，文案与规则以本文为准。

## 档位

| 套餐 | 价格 | 关键差异 |
|------|------|----------|
| free | ¥0 | 3 项目，60 req/min |
| pro | ¥99/月 | 不限项目，600 req/min |
| enterprise | 询价 | SSO、审计日志、6000 req/min |

## 试用

- pro 免费试用 14 天，到期自动降级 free（不扣费、不绑卡）。
- 试用期内 API 按 pro 配额（见 backend/api-rate-limit）。

## 定价变更

- 任何调价提前 30 天邮件通知存量用户。
- 老用户价格保护 12 个月。

## 边界

- 页面价格由配置文件驱动，禁止前端硬编码。
- 折扣码逻辑在服务端，前端只做展示。

## 相关

- 账单规则见 `backend/billing-invoices.md`。
