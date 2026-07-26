---
title: Auth token 刷新
summary: access token 过期后的刷新端点、轮换策略与 REFRESH_TOKEN_EXPIRED 处理。
keywords: [auth, token, refresh, 刷新, 鉴权]
domain: backend
code_paths: [src/auth/refresh.py]
trust_level: 1
verified_at: "2026-07-20"
---

# Auth token 刷新

## 概述

access token 有效期只有 15 分钟，客户端必须用 refresh token 静默续期。
实现位于 `src/auth/refresh.py`。

## 端点

`POST /auth/refresh`

- 请求：HttpOnly cookie 中的 refresh token，无需 body。
- 成功响应 200：新 access token（JSON body）+ 新 refresh token（Set-Cookie）。

## 轮换策略

- 每次刷新 **旧 refresh token 立即作废**（rotation）。
- 旧 token 被重放使用 → 判定泄露，整条 token 链全部吊销，用户须重新登录。
- 吊销记录保留 30 天用于审计。

## 错误码

| HTTP | code | 含义 |
|------|------|------|
| 401 | REFRESH_TOKEN_EXPIRED | refresh token 超 30 天或已被轮换作废 |
| 401 | REFRESH_TOKEN_REUSED | 旧 token 重放，token 链已吊销 |

客户端收到 `REFRESH_TOKEN_EXPIRED` 必须跳登录页，禁止无限重试刷新。

## 边界

- 并发刷新：同一 refresh token 同时到达两个请求，先到的成功，后到的
  收到 REFRESH_TOKEN_REUSED——客户端应做请求去抖。
- 时钟偏移：access token 校验容忍 60 秒 skew。

## 相关

- 登录入口见 `auth-login.md`。
