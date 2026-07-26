---
title: 邀请返利计划
summary: 邀请奖励规则、防刷策略与结算周期。
keywords: [growth, referral, 邀请, 增长]
domain: growth
code_paths: [src/growth/]
trust_level: 4
verified_at: "2026-06-12"
---

# 邀请返利计划

## 概述

邀请系统代码在 `src/growth/`，规则以本文为准。

## 规则

- 邀请人：被邀请者付费首月后，邀请人得 1 个月 pro 额度。
- 被邀请者：注册即得 14 天 pro 试用（与 pricing 试用不叠加）。

## 防刷

- 同设备/同支付账户判定为同一人，不发放奖励。
- 邀请链接带签名参数，篡改直接 400。
- 异常模式（短时批量注册）进人工审核队列。

## 结算

- 每月 5 日结算上月奖励，记录进 `referral_grants` 表。
- 奖励不可折现、不可转让。

## 边界

- 邀请转化率埋点见 data/analytics-events（`referral_signed_up`）。
- 企业客户不参与邀请计划。

## 相关

- 试用规则见 `product/pricing-page.md`；账单见 `backend/billing-invoices.md`。
