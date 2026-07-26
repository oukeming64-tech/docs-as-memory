---
title: 支付 webhook 处理
summary: 第三方支付回调的验签、幂等与对账约定。
keywords: [billing, webhook, 回调, 支付]
domain: backend
code_paths: [src/billing/webhooks.py]
trust_level: 1
verified_at: "2026-05-20"
---

# 支付 webhook 处理

## 概述

支付平台异步通知入口：`src/billing/webhooks.py`。

## 验签

- 使用平台公钥验签（Ed25519），验签失败直接 401，**不写库**。
- 时间戳偏差超过 5 分钟拒绝，防重放。

## 幂等

- 以 `event_id` 去重，唯一索引在 `billing_events` 表。
- 重复事件返回 200 + `{"dedup": true}`，让平台停止重试。

## 处理顺序

1. 验签 → 2. 落库（原始 payload 存档）→ 3. 业务处理（异步队列）→ 4. 回 200。
- 业务处理失败不影响 200 响应；由队列重试，超过 10 次进死信。

## 对账

- 每日 04:00 拉平台账单文件与本地核对，差异 >0 时告警。
- 对账脚本：`src/billing/reconcile.py`。

## 相关

- 账单生成见 `billing-invoices.md`。
