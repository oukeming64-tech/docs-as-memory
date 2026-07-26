---
title: API 错误码总表
summary: 统一错误响应格式与全域错误码清单。
keywords: [api, error, 错误码, 异常]
domain: backend
code_paths: [src/api/errors.py]
trust_level: 2
verified_at: "2026-07-05"
---

# API 错误码总表

## 概述

所有 API 错误响应统一格式，定义在 `src/api/errors.py`。

## 格式

```json
{"error": {"code": "SOME_CODE", "message": "人类可读", "trace_id": "..."}}
```

- `code` 为机器可读常量，大写蛇形。
- `message` 面向开发者，不做 i18n；前端自行映射文案。

## 全域错误码

| HTTP | code | 场景 |
|------|------|------|
| 400 | INVALID_ARGUMENT | 参数校验失败 |
| 401 | UNAUTHENTICATED | 缺 token 或 token 无效 |
| 403 | FORBIDDEN | scope 不足 |
| 404 | NOT_FOUND | 资源不存在或无权感知 |
| 409 | CONFLICT | 唯一性冲突 |
| 429 | RATE_LIMITED | 限流 |
| 500 | INTERNAL | 未捕获异常（只报 trace_id） |

## 约定

- 业务子系统的专用码（如 REFRESH_TOKEN_EXPIRED）在各自碎片登记，本表不重复。
- 新增错误码必须同步本表与 `errors.py`，二者由 CI 对拍。

## 相关

- 鉴权类错误见 `backend/auth-login.md` 与 `auth-token-refresh.md`。
