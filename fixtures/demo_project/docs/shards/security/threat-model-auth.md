---
title: 鉴权威胁模型
summary: 鉴权子系统的威胁清单与对应缓解措施。
keywords: [security, threat, 威胁模型, 鉴权]
domain: security
code_paths: [src/auth/]
trust_level: 2
verified_at: "2026-06-27"
---

# 鉴权威胁模型

## 概述

鉴权子系统威胁模型，范围 `src/auth/`。

## 威胁清单

| 威胁 | 缓解 |
|------|------|
| 撞库 | 登录限流 + 账号锁定（见 auth-login） |
| refresh token 泄露重放 | 轮换 + 重放检测吊销全链（见 auth-token-refresh） |
| XSS 窃取 token | token 不落 localStorage，refresh 走 HttpOnly cookie |
| 越权 | scope 校验在中间件，业务代码不做可信假设 |
| 时序攻击枚举用户 | 登录失败统一 BAD_CREDENTIALS + 恒定时间比较 |

## 残余风险

- access token 15 分钟窗口内的 scope 滞后（角色变更），已接受，
  见 auth-permissions 的 revoke_user_tokens。

## 评审

- 威胁模型随鉴权相关 PR 更新；每半年全量复审一次。

## 相关

- `backend/auth-login.md`、`auth-token-refresh.md`、`auth-permissions.md`。
