---
title: users 表结构
summary: users 及相关鉴权表的字段、索引与迁移约定。
keywords: [data, schema, 数据库, 用户表]
domain: data
code_paths: [db/migrations/]
trust_level: 1
verified_at: "2026-07-18"
---

# users 表结构

## 概述

表结构以 `db/migrations/` 迁移文件为准，本文是导读。

## users

| 字段 | 类型 | 说明 |
|------|------|------|
| id | uuid PK | |
| email | citext unique | 登录标识 |
| password_hash | text | argon2id |
| timezone | text | IANA 名 |
| deleted_at | timestamptz | 软删 |

## auth_refresh

- `token_hash`（不存明文）、`user_id`、`expires_at`、`rotated_from`。
- 索引：`(user_id, expires_at)`。

## 迁移约定

- 只增不改：历史迁移文件禁止编辑，修正走新迁移。
- DDL 必须向后兼容一个版本（见 ops/deploy-runbook）。
- 大表加索引用 CONCURRENTLY，进发布说明。

## 相关

- 字段的业务语义见 `backend/user-profile.md`。
