---
title: 密钥管理规范
summary: 密钥存放、轮换周期与泄露应急。
keywords: [security, secret, 密钥, 安全]
domain: security
code_paths: []
trust_level: 1
verified_at: "2026-07-02"
---

# 密钥管理规范

## 概述

密钥管理规范（无代码路径，全仓适用）。

## 存放

- 只允许进密钥管理服务；禁止进仓库、CI 日志、前端构建产物。
- 本地开发用 `.env.local`（gitignore 兜底），但禁止提交真实生产密钥。

## 轮换

- 生产密钥 90 天强制轮换。
- JWT 签名密钥支持双密钥过渡（旧签名校验保留 30 天）。

## 泄露应急

1. 立即吊销 → 2. 轮换 → 3. 排查访问日志 → 4. 按 incident-response 走 SEV2 流程。

## 检查

- CI 有密钥扫描；误报加白名单需安全组批准。

## 相关

- 事故流程见 `ops/incident-response.md`。
