---
title: 权限模型 RBAC
summary: 角色-权限两级模型、scope 命名规范与接口鉴权中间件用法。
keywords: [auth, rbac, permission, 权限, 鉴权]
domain: backend
code_paths: [src/auth/rbac.py]
trust_level: 2
verified_at: "2026-07-01"
---

# 权限模型 RBAC

## 概述

权限采用 RBAC：user → role → permission。实现在 `src/auth/rbac.py`。

## 内置角色

| role | 说明 |
|------|------|
| admin | 全部权限 |
| member | 业务读写 |
| viewer | 只读 |

## scope 命名

`{资源}:{动作}`，如 `invoice:read`、`invoice:write`、`user:ban`。

## 接口鉴权

```python
from auth.rbac import require

@app.get("/invoices")
@require("invoice:read")
def list_invoices(): ...
```

- `@require` 从 access token 的 `scope` claim 读取权限，**不查库**。
- scope 不足返回 403 `FORBIDDEN`（不是 401）。

## 注意

- 角色变更后，已签发的 access token 在剩余 15 分钟生命周期内仍持旧 scope，
  这是有意取舍；强制即时生效请调用 `revoke_user_tokens(uid)`。

## 相关

- token 签发见 `auth-login.md`；威胁模型见 `security/threat-model-auth.md`。
