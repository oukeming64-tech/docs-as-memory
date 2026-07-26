---
title: API 限流
summary: 全局限流规则、配额档位与 429 响应约定。
keywords: [api, ratelimit, 限流, 配额]
domain: backend
code_paths: [src/api/ratelimit.py]
trust_level: 1
verified_at: "2026-07-10"
---

# API 限流

## 概述

限流中间件：`src/api/ratelimit.py`，基于滑动窗口（Redis）。

## 档位

| 套餐 | 默认配额 |
|------|----------|
| free | 60 req/min |
| pro | 600 req/min |
| enterprise | 6000 req/min |

## 响应约定

- 超限返回 429，带 `Retry-After`（秒）。
- 响应头始终携带 `X-RateLimit-Limit` / `X-RateLimit-Remaining`。

## 例外

- 登录接口单独限流（见 auth-login 的 LOGIN_RATE_LIMITED）。
- webhook 入口不限流但验签（见 billing-webhooks）。

## 边界

- 限流按 API key 维度；无 key 的匿名请求按 IP。
- Redis 故障时限流降级为放行（fail-open），同时告警——宁可放过不可误杀。

## 相关

- 错误码总表见 `api-error-codes.md`。
