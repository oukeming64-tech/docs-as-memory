---
title: Web 构建管线
summary: 构建工具链、环境变量注入与产物发布流程。
keywords: [frontend, build, 构建, 打包]
domain: frontend
code_paths: [web/build/]
trust_level: 3
verified_at: "2026-05-30"
---

# Web 构建管线

## 概述

构建配置在 `web/build/`，Vite + esbuild。

## 环境变量

- 仅 `VITE_` 前缀变量注入客户端。
- 密钥一律不进前端构建（见 security/secrets-policy）。

## 产物

- `web/dist/`，带内容哈希的文件名，CDN 缓存 1 年。
- `index.html` 不缓存（`Cache-Control: no-cache`）。

## 发布流程

1. CI 构建 → 2. 上传 CDN → 3. 切流量（见 ops/deploy-runbook）。

## 边界

- sourcemap 上传到监控平台后从产物中删除，不公网暴露。
- 构建时间超过 8 分钟告警（基线约 4 分钟）。

## 相关

- 部署见 `ops/deploy-runbook.md`。
