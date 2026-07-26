---
title: 前端状态管理
summary: store 分层、服务端状态缓存策略与禁止事项。
keywords: [frontend, store, 状态管理]
domain: frontend
code_paths: [web/src/store/]
trust_level: 2
verified_at: "2026-06-18"
---

# 前端状态管理

## 概述

状态分两层，代码在 `web/src/store/`。

## 分层

- **服务端状态**：React Query，缓存 5 分钟，错误自动重试 2 次。
- **客户端状态**：zustand，只放 UI 态（弹窗、草稿、主题）。

## 禁止事项

- 禁止把服务端数据镜像进 zustand（双份真相）。
- 禁止在 store 里写业务请求逻辑；请求封装在 `web/src/api/`。

## token 存放

- access token 只在内存（zustand auth slice），刷新页面前从 cookie 静默续期。
- 任何持久化（localStorage）存 token 的 PR 一律打回（见 backend/auth-login 约定）。

## 边界

- React Query 的 `staleTime` 按资源单独调，不要全局拉大。
- 登出时 `queryClient.clear()`，防账号串数据。

## 相关

- 路由守卫见 `web-routing.md`。
