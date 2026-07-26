---
title: 账单与发票
summary: 账单生成周期、发票 PDF 生成与欠费处理策略。
keywords: [billing, invoice, 账单, 发票]
domain: backend
code_paths: [src/billing/]
trust_level: 2
verified_at: "2026-06-15"
---

# 账单与发票

## 概述

账单子系统位于 `src/billing/`，核心入口 `invoices.py`。

## 生成周期

- 每月 1 日 00:30（Asia/Shanghai）批处理生成上月账单。
- 生成失败自动重试 3 次，仍失败告警到 ops 频道（见 monitoring-alerts）。

## 发票

- PDF 由 `invoice_pdf.py` 渲染，模板在 `src/billing/templates/`。
- 发票号格式 `INV-YYYYMM-{8位序号}`，序号全局唯一、不回填。

## 欠费策略

| 逾期 | 动作 |
|------|------|
| 7 天 | 邮件提醒 |
| 15 天 | 降级为 viewer（见 auth-permissions） |
| 30 天 | 停服，数据保留 90 天 |

## 边界

- 中途升级套餐按天折算，精度到分，四舍五入。
- 退款不走账单系统，人工审批后由财务处理。

## 相关

- 支付回调见 `billing-webhooks.md`；定价展示见 `product/pricing-page.md`。
