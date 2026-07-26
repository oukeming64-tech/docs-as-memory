---
title: 移动客户端发版
summary: iOS/Android 发版节奏、热更新边界与灰度策略。
keywords: [mobile, release, 发版, 客户端]
domain: mobile
code_paths: [mobile/]
trust_level: 3
verified_at: "2026-07-01"
---

# 移动客户端发版

## 概述

客户端工程在 `mobile/`（React Native）。

## 节奏

- 双周发版，与 Web 发布解耦（Web 流程见 ops/deploy-runbook）。
- 商店审核预留 48 小时缓冲。

## 热更新

- 只允许 JS bundle 热更；原生模块变更必须整包发版。
- 热更包签名校验，失败回退内置 bundle。

## 灰度

- 热更 5% → 50% → 100%，每档观察 24 小时。
- 崩溃率超基线 1.5 倍自动停止推送。

## 边界

- 最低支持系统版本每年 Q1 评审上调。
- 商店截图与文案走 product 评审，不归发版流程。

## 相关

- 鉴权 token 在客户端的存放约定同 `backend/auth-login.md`（禁持久化 access token）。
