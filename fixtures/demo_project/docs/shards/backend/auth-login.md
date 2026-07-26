---
title: Auth 登录流程
summary: 密码登录签发 access+refresh 双 token 的入口、会话约定与错误码。
keywords: [auth, login, token, 鉴权, 登录]
domain: backend
code_paths: [src/auth/, src/api/session.py]
trust_level: 1
verified_at: "2026-07-20"
---

# Auth 登录流程

## 概述

登录是鉴权子系统的唯一入口，位于 `src/auth/login.py` 的 `handle_login`。

## 流程

1. 客户端提交 username + password 到 `POST /auth/login`。
2. 服务端校验密码（argon2id，参数见 `src/auth/password.py`）。
3. 成功后签发两个 token：
   - access token：JWT，有效期 15 分钟，含 `sub` 与 `scope`。
   - refresh token：不透明随机串，有效期 30 天，存 `auth_refresh` 表。
4. 会话记录在 `src/api/session.py` 建立，绑定 UA 指纹。

## 错误码

| HTTP | code | 含义 |
|------|------|------|
| 401 | BAD_CREDENTIALS | 用户名或密码错误（不区分哪种，防枚举） |
| 423 | ACCOUNT_LOCKED | 连续失败 5 次锁定 15 分钟 |
| 429 | LOGIN_RATE_LIMITED | 同 IP 每分钟超过 20 次尝试 |

## 约定

- access token 只放内存，禁止写 localStorage。
- refresh token 走 HttpOnly cookie，`SameSite=Strict`。
- 登录响应不返回用户全量资料，资料走 `GET /me`（见 user-profile 碎片）。

## 相关

- 刷新见 `auth-token-refresh.md`；权限见 `auth-permissions.md`。
