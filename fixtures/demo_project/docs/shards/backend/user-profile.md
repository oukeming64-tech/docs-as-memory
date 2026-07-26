---
title: 用户资料
summary: 用户资料的读写接口、字段约束与隐私分级。
keywords: [user, profile, 用户, 资料]
domain: backend
code_paths: [src/user/]
trust_level: 2
verified_at: "2026-06-30"
---

# 用户资料

## 概述

用户资料服务位于 `src/user/`。

## 接口

- `GET /me`：当前用户资料（登录后调用，见 auth-login）。
- `PATCH /me`：更新资料，字段级校验。

## 字段约束

| 字段 | 约束 |
|------|------|
| display_name | 1～32 字符，允许 emoji |
| avatar_url | 必须是本仓 CDN 域名 |
| timezone | IANA 时区名 |

## 隐私分级

- L1 公开：display_name、avatar_url。
- L2 登录可见：timezone、注册时间。
- L3 仅本人：邮箱、手机号（响应中掩码）。

## 边界

- display_name 不做唯一性；@提及用 user id。
- 注销用户资料 30 天后物理删除（软删标记 `deleted_at`）。

## 相关

- 鉴权见 `backend/auth-login.md`；表结构见 `data/db-schema-users.md`。
