---
title: Web 路由
summary: 前端路由结构、鉴权守卫与懒加载约定。
keywords: [frontend, router, 路由, 页面]
domain: frontend
code_paths: [web/src/router/]
trust_level: 2
verified_at: "2026-06-25"
---

# Web 路由

## 概述

路由定义在 `web/src/router/`（React Router v6）。

## 结构

- `/login`、`/auth/callback`：匿名区。
- `/app/*`：登录区，外层 `RequireAuth` 守卫。
- `/app/settings/*`：需 `member` 以上角色。

## 守卫

- `RequireAuth`：无 access token → 先尝试静默刷新（见 backend/auth-token-refresh），
  失败跳 `/login?next=<原路径>`。
- 角色守卫读 token 的 scope，不做前端硬编码角色表。

## 懒加载

- 每个一级路由一个 chunk，`React.lazy` + `Suspense`。
- chunk 命名与路由一致，方便排查加载失败。

## 边界

- 404 页只对 `/app/*` 内生效；匿名区错误路径重定向到 `/login`。
- 路由切换不打点，埋点走页面级组件（见 data/analytics-events）。

## 相关

- 状态管理见 `web-state-store.md`。
