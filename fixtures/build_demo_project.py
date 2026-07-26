#!/usr/bin/env python3
"""重建 fixtures/demo_project（23 个碎片 + dummy 代码树）。

注意：重建会改变 fixture 内容哈希；按 specs/TOKEN_EVAL.md §6，
任何夹具变更后 Kimi 与 Grok 双方都必须整 task 重跑评测。
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(HERE, "demo_project")

# (relpath, title, summary, keywords, domain, code_paths, trust_level, verified_at, body)
SHARDS = [
    ("backend/auth-login.md", "Auth 登录流程",
     "密码登录签发 access+refresh 双 token 的入口、会话约定与错误码。",
     ["auth", "login", "token", "鉴权", "登录"], "backend",
     ["src/auth/", "src/api/session.py"], 1, "2026-07-20",
     """## 概述

登录是鉴权子系统的唯一入口，位于 `src/auth/login.py` 的 `handle_login`。

## 流程

1. 客户端提交 username + password 到 `POST /auth/login`。
2. 服务端校验密码（argon2id，参数见 `src/auth/password.py`）。
3. 成功后签发两个 token：
   - access token：JWT，有效期 15 分钟，含 `sub` 与 `scope`。
   - refresh token：不透明随机串，有效期 30 天，存 `auth_refresh` 表。
4. 会话记录在 `src/api/session.py` 建立，绑定 UA 指纹。

## 错误码

| HTTP | code | 含义 |
|------|------|------|
| 401 | BAD_CREDENTIALS | 用户名或密码错误（不区分哪种，防枚举） |
| 423 | ACCOUNT_LOCKED | 连续失败 5 次锁定 15 分钟 |
| 429 | LOGIN_RATE_LIMITED | 同 IP 每分钟超过 20 次尝试 |

## 约定

- access token 只放内存，禁止写 localStorage。
- refresh token 走 HttpOnly cookie，`SameSite=Strict`。
- 登录响应不返回用户全量资料，资料走 `GET /me`（见 user-profile 碎片）。

## 相关

- 刷新见 `auth-token-refresh.md`；权限见 `auth-permissions.md`。
"""),
    ("backend/auth-token-refresh.md", "Auth token 刷新",
     "access token 过期后的刷新端点、轮换策略与 REFRESH_TOKEN_EXPIRED 处理。",
     ["auth", "token", "refresh", "刷新", "鉴权"], "backend",
     ["src/auth/refresh.py"], 1, "2026-07-20",
     """## 概述

access token 有效期只有 15 分钟，客户端必须用 refresh token 静默续期。
实现位于 `src/auth/refresh.py`。

## 端点

`POST /auth/refresh`

- 请求：HttpOnly cookie 中的 refresh token，无需 body。
- 成功响应 200：新 access token（JSON body）+ 新 refresh token（Set-Cookie）。

## 轮换策略

- 每次刷新 **旧 refresh token 立即作废**（rotation）。
- 旧 token 被重放使用 → 判定泄露，整条 token 链全部吊销，用户须重新登录。
- 吊销记录保留 30 天用于审计。

## 错误码

| HTTP | code | 含义 |
|------|------|------|
| 401 | REFRESH_TOKEN_EXPIRED | refresh token 超 30 天或已被轮换作废 |
| 401 | REFRESH_TOKEN_REUSED | 旧 token 重放，token 链已吊销 |

客户端收到 `REFRESH_TOKEN_EXPIRED` 必须跳登录页，禁止无限重试刷新。

## 边界

- 并发刷新：同一 refresh token 同时到达两个请求，先到的成功，后到的
  收到 REFRESH_TOKEN_REUSED——客户端应做请求去抖。
- 时钟偏移：access token 校验容忍 60 秒 skew。

## 相关

- 登录入口见 `auth-login.md`。
"""),
    ("backend/auth-permissions.md", "权限模型 RBAC",
     "角色-权限两级模型、scope 命名规范与接口鉴权中间件用法。",
     ["auth", "rbac", "permission", "权限", "鉴权"], "backend",
     ["src/auth/rbac.py"], 2, "2026-07-01",
     """## 概述

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
"""),
    ("backend/billing-invoices.md", "账单与发票",
     "账单生成周期、发票 PDF 生成与欠费处理策略。",
     ["billing", "invoice", "账单", "发票"], "backend",
     ["src/billing/"], 2, "2026-06-15",
     """## 概述

账单子系统位于 `src/billing/`，核心入口 `invoices.py`。

## 生成周期

- 每月 1 日 00:30（Asia/Shanghai）批处理生成上月账单。
- 生成失败自动重试 3 次，仍失败告警到 ops 频道（见 monitoring-alerts）。

## 发票

- PDF 由 `invoice_pdf.py` 渲染，模板在 `src/billing/templates/`。
- 发票号格式 `INV-YYYYMM-{8位序号}`，序号全局唯一、不回填。

## 欠费策略

| 逾期 | 动作 |
|------|------|
| 7 天 | 邮件提醒 |
| 15 天 | 降级为 viewer（见 auth-permissions） |
| 30 天 | 停服，数据保留 90 天 |

## 边界

- 中途升级套餐按天折算，精度到分，四舍五入。
- 退款不走账单系统，人工审批后由财务处理。

## 相关

- 支付回调见 `billing-webhooks.md`；定价展示见 `product/pricing-page.md`。
"""),
    ("backend/billing-webhooks.md", "支付 webhook 处理",
     "第三方支付回调的验签、幂等与对账约定。",
     ["billing", "webhook", "回调", "支付"], "backend",
     ["src/billing/webhooks.py"], 1, "2026-05-20",
     """## 概述

支付平台异步通知入口：`src/billing/webhooks.py`。

## 验签

- 使用平台公钥验签（Ed25519），验签失败直接 401，**不写库**。
- 时间戳偏差超过 5 分钟拒绝，防重放。

## 幂等

- 以 `event_id` 去重，唯一索引在 `billing_events` 表。
- 重复事件返回 200 + `{"dedup": true}`，让平台停止重试。

## 处理顺序

1. 验签 → 2. 落库（原始 payload 存档）→ 3. 业务处理（异步队列）→ 4. 回 200。
- 业务处理失败不影响 200 响应；由队列重试，超过 10 次进死信。

## 对账

- 每日 04:00 拉平台账单文件与本地核对，差异 >0 时告警。
- 对账脚本：`src/billing/reconcile.py`。

## 相关

- 账单生成见 `billing-invoices.md`。
"""),
    ("backend/user-profile.md", "用户资料",
     "用户资料的读写接口、字段约束与隐私分级。",
     ["user", "profile", "用户", "资料"], "backend",
     ["src/user/"], 2, "2026-06-30",
     """## 概述

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
"""),
    ("backend/api-rate-limit.md", "API 限流",
     "全局限流规则、配额档位与 429 响应约定。",
     ["api", "ratelimit", "限流", "配额"], "backend",
     ["src/api/ratelimit.py"], 1, "2026-07-10",
     """## 概述

限流中间件：`src/api/ratelimit.py`，基于滑动窗口（Redis）。

## 档位

| 套餐 | 默认配额 |
|------|----------|
| free | 60 req/min |
| pro | 600 req/min |
| enterprise | 6000 req/min |

## 响应约定

- 超限返回 429，带 `Retry-After`（秒）。
- 响应头始终携带 `X-RateLimit-Limit` / `X-RateLimit-Remaining`。

## 例外

- 登录接口单独限流（见 auth-login 的 LOGIN_RATE_LIMITED）。
- webhook 入口不限流但验签（见 billing-webhooks）。

## 边界

- 限流按 API key 维度；无 key 的匿名请求按 IP。
- Redis 故障时限流降级为放行（fail-open），同时告警——宁可放过不可误杀。

## 相关

- 错误码总表见 `api-error-codes.md`。
"""),
    ("backend/api-error-codes.md", "API 错误码总表",
     "统一错误响应格式与全域错误码清单。",
     ["api", "error", "错误码", "异常"], "backend",
     ["src/api/errors.py"], 2, "2026-07-05",
     """## 概述

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
"""),
    ("frontend/web-routing.md", "Web 路由",
     "前端路由结构、鉴权守卫与懒加载约定。",
     ["frontend", "router", "路由", "页面"], "frontend",
     ["web/src/router/"], 2, "2026-06-25",
     """## 概述

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
"""),
    ("frontend/web-state-store.md", "前端状态管理",
     "store 分层、服务端状态缓存策略与禁止事项。",
     ["frontend", "store", "状态管理"], "frontend",
     ["web/src/store/"], 2, "2026-06-18",
     """## 概述

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
"""),
    ("frontend/web-build-pipeline.md", "Web 构建管线",
     "构建工具链、环境变量注入与产物发布流程。",
     ["frontend", "build", "构建", "打包"], "frontend",
     ["web/build/"], 3, "2026-05-30",
     """## 概述

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
"""),
    ("frontend/web-ui-components.md", "UI 组件库约定",
     "组件分层、样式方案与新增组件 checklist。",
     ["frontend", "component", "组件"], "frontend",
     ["web/src/components/"], 3, "2026-04-15",
     """## 概述

组件目录 `web/src/components/` 分三层：

- `base/`：无业务含义（Button、Modal）。
- `biz/`：业务组件（InvoiceCard）。
- `page/`：页面级组装，不进组件库文档。

## 样式

- Tailwind utility-first；禁止新增全局 CSS 文件。
- 设计 token 在 `web/src/styles/tokens.ts`，颜色禁止字面值。

## 新增组件 checklist

1. 放对层级（base/biz/page）。
2. props 全部显式类型，不用 `any`。
3. 交互组件配 keyboard 可达性。
4. base 组件必须有 story。

## 边界

- 超过 300 行的组件必须拆分。
- 第三方组件库只许引入头部制定的白名单。

## 相关

- 状态管理见 `web-state-store.md`。
"""),
    ("product/onboarding-flow.md", "新手引导流程",
     "注册后引导的步骤设计、完成判定与跳过策略。",
     ["product", "onboarding",  "新手引导"], "product",
     ["web/src/onboarding/"], 4, "2026-06-01",
     """## 概述

新手引导实现于 `web/src/onboarding/`，产品逻辑本文为准。

## 步骤

1. 欢迎页（可跳过）→ 2. 创建首个项目（不可跳过）→
3. 邀请成员（可跳过）→ 4. 完成页。

## 完成判定

- 完成 = 创建首个项目；其余步骤不影响判定。
- 完成状态写服务端 `onboarding_done`，前端不存。

## 跳过策略

- 跳过入口永远可见；禁止「看完才能跳过」的强制设计。
- 7 天内未完成引导 → 引导浮层永久关闭，改在设置页留入口。

## 指标

- 引导完成率按周统计（埋点见 data/analytics-events）。
- 目标基线：完成率 ≥ 55%。

## 相关

- 埋点事件见 `data/analytics-events.md`。
"""),
    ("product/pricing-page.md", "定价页",
     "套餐档位展示、试用规则与定价变更流程。",
     ["product", "pricing", "定价", "套餐"], "product",
     ["web/src/pricing/"], 4, "2026-07-08",
     """## 概述

定价页实现 `web/src/pricing/`，文案与规则以本文为准。

## 档位

| 套餐 | 价格 | 关键差异 |
|------|------|----------|
| free | ¥0 | 3 项目，60 req/min |
| pro | ¥99/月 | 不限项目，600 req/min |
| enterprise | 询价 | SSO、审计日志、6000 req/min |

## 试用

- pro 免费试用 14 天，到期自动降级 free（不扣费、不绑卡）。
- 试用期内 API 按 pro 配额（见 backend/api-rate-limit）。

## 定价变更

- 任何调价提前 30 天邮件通知存量用户。
- 老用户价格保护 12 个月。

## 边界

- 页面价格由配置文件驱动，禁止前端硬编码。
- 折扣码逻辑在服务端，前端只做展示。

## 相关

- 账单规则见 `backend/billing-invoices.md`。
"""),
    ("product/changelog-policy.md", "更新日志规范",
     "changelog 的撰写规范、分类标签与发布节奏。",
     ["product", "changelog", "更新日志"], "product",
     [], 4, "2026-05-10",
     """## 概述

对外更新日志每周五发布；本文是撰写规范（无对应代码路径）。

## 分类标签

- `Added` 新功能 / `Changed` 行为变更 / `Fixed` 修复 / `Security` 安全。

## 规范

- 面向用户价值描述，禁止贴 commit message。
- Breaking change 必须置顶并附迁移步骤。
- Security 条目在修复全量发布后 7 天才公开细节。

## 节奏

- 周五 17:00 前合并 changelog PR，随当周发布一起出。

## 边界

- 内部重构不进 changelog。
- hotfix 单独发即时条目，不等周五。

## 相关

- 发布流程见 `ops/deploy-runbook.md`。
"""),
    ("ops/deploy-runbook.md", "部署手册",
     "标准发布流程、回滚步骤与发布窗口。",
     ["ops", "deploy", "部署", "发布"], "ops",
     ["deploy/"], 1, "2026-07-22",
     """## 概述

部署脚本与清单在 `deploy/`。

## 标准流程

1. CI 绿 → 2. 打 tag（`vYYYY.MM.DD-N`）→ 3. 灰度 5%（30 分钟观察）→
4. 全量 → 5. changelog 发布（见 product/changelog-policy）。

## 回滚

- 一键回滚：`deploy/rollback.sh <tag>`，3 分钟内完成。
- 数据库变更必须向后兼容一个版本，禁止「代码+破坏性 DDL」同批发布。

## 发布窗口

- 工作日 10:00–17:00（Asia/Shanghai），周五 15:00 后冻结。
- 冻结期 hotfix 需值班 TL 批准。

## 边界

- 灰度期错误率超基线 2 倍自动暂停（见 monitoring-alerts）。
- 每次发布后在 #ops 频道留一行记录：tag、操作人、结果。

## 相关

- 监控告警见 `monitoring-alerts.md`；事故处理见 `incident-response.md`。
"""),
    ("ops/monitoring-alerts.md", "监控与告警",
     "核心指标、告警分级与值班响应时限。",
     ["ops", "monitoring", "alert", "监控", "告警"], "ops",
     ["deploy/monitoring/"], 2, "2026-07-15",
     """## 概述

告警规则在 `deploy/monitoring/alerts.yaml`。

## 核心指标

- API：p99 延迟、5xx 率、限流拒绝率。
- 鉴权：登录成功率、刷新失败率（异常飙升 = 攻击或 bug）。
- 账单：生成任务成功率、对账差异。

## 分级

| 级别 | 含义 | 响应时限 |
|------|------|----------|
| P1 | 服务不可用/数据风险 | 15 分钟 |
| P2 | 核心功能受损 | 1 小时 |
| P3 | 趋势异常 | 下个工作日 |

## 值班

- 单周轮换；P1 电话，P2 短信，P3 仅频道消息。
- 告警 30 分钟未确认自动升级一级。

## 边界

- 新告警规则先「仅记录」观察一周再开通知，防告警风暴。
- 误报率 >20% 的规则必须调阈值或删除。

## 相关

- 事故流程见 `incident-response.md`。
"""),
    ("ops/incident-response.md", "事故应急响应",
     "事故分级、响应流程与复盘要求。",
     ["ops", "incident", "事故", "应急响应"], "ops",
     [], 2, "2026-06-20",
     """## 概述

事故处理流程（无专属代码路径，配合监控告警执行）。

## 分级

- SEV1：全站不可用或数据丢失风险。
- SEV2：核心功能受损有绕行方案。
- SEV3：影响有限。

## 流程

1. 确认（值班，15 分钟内）→ 2. 建作战频道 → 3. 指定 incident commander →
4. 先恢复后定位 → 5. 公告（SEV1 每 30 分钟更新）。

## 角色

- IC 拥有现场最高决策权，包括回滚与降级。
- 沟通官负责对外公告，IC 不直接对外。

## 复盘

- SEV1/2 必须 48 小时内出复盘报告：时间线、根因、action items。
- 复盘不追责个人，只追流程缺陷。

## 相关

- 回滚操作见 `deploy-runbook.md`；告警分级见 `monitoring-alerts.md`。
"""),
    ("data/db-schema-users.md", "users 表结构",
     "users 及相关鉴权表的字段、索引与迁移约定。",
     ["data", "schema", "数据库", "用户表"], "data",
     ["db/migrations/"], 1, "2026-07-18",
     """## 概述

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
"""),
    ("data/etl-pipeline.md", "数据同步管道",
     "业务库到分析库的 ETL 节奏、幂等与失败处理。",
     ["data", "etl", "数据管道", "同步"], "data",
     ["etl/"], 2, "2026-06-08",
     """## 概述

ETL 代码在 `etl/`，业务库 → 分析库（列存）。

## 节奏

- 增量：每 15 分钟（基于 `updated_at` 游标）。
- 全量校验：每日 03:00，行数 + checksum 对拍。

## 幂等

- 所有写入按主键 upsert；重复跑不产生重复行。
- 游标存 `etl_state` 表，失败从最后成功点续跑。

## 失败处理

- 单表失败不阻塞其他表；连续 3 次失败告警（P3）。
- 数据不一致时以业务库为准，分析库重刷。

## 边界

- 删数据靠软删标记同步，物理删除不进分析库。
- PII 字段（email、手机号）进分析库前哈希。

## 相关

- 埋点事件另走实时流，见 `analytics-events.md`。
"""),
    ("data/analytics-events.md", "埋点事件规范",
     "事件命名、属性规范与新事件上线流程。",
     ["data", "analytics", "埋点", "事件"], "data",
     ["src/analytics/"], 2, "2026-07-12",
     """## 概述

埋点 SDK 在 `src/analytics/`，前后端共用事件规范。

## 命名

- `{对象}_{动作}`，蛇形小写：`project_created`、`onboarding_step_skipped`。
- 禁止动态拼接事件名。

## 属性规范

- 必带：`user_id`、`ts`、`source`（web/api）。
- 禁止携带 PII；金额类用「分」为单位的整数。

## 新事件上线流程

1. 本文档登记 → 2. 评审 → 3. 实现 → 4. 灰度环境验证数据 → 5. 上线。

## 边界

- 事件 schema 变更只允许加属性，不允许改含义；语义变了就起新事件名。
- 路由切换不打点（见 frontend/web-routing）。

## 相关

- 引导漏斗依赖本文事件，见 `product/onboarding-flow.md`。
"""),
    ("security/secrets-policy.md", "密钥管理规范",
     "密钥存放、轮换周期与泄露应急。",
     ["security", "secret", "密钥", "安全"], "security",
     [], 1, "2026-07-02",
     """## 概述

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
"""),
    ("security/threat-model-auth.md", "鉴权威胁模型",
     "鉴权子系统的威胁清单与对应缓解措施。",
     ["security", "threat", "威胁模型", "鉴权"], "security",
     ["src/auth/"], 2, "2026-06-27",
     """## 概述

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
"""),
    ("qa/test-strategy.md", "测试策略",
     "测试金字塔分层、覆盖率门槛与 CI 集成方式。",
     ["qa", "test", "测试", "策略"], "qa",
     ["tests/"], 3, "2026-07-06",
     """## 概述

测试代码在 `tests/`，按金字塔分层。

## 分层

- 单测（70%）：纯函数与领域逻辑，禁止起服务、禁网。
- 集成（25%）：API 层，用测试库，鉴权走真实中间件。
- E2E（5%）：只覆盖登录、下单两条黄金路径。

## 门槛

- 全仓行覆盖率 ≥ 80%；`src/auth/` 单独要求 ≥ 90%。
- 新增代码覆盖率低于门槛 CI 直接红。

## CI 集成

- PR：单测 + 集成（约 6 分钟）；E2E 只在主干跑。
- flaky 测试挂起隔离，两周内不修复就删除，不允许「重试到绿」。

## 边界

- 快照测试只用于组件库 base 层。
- 测试数据用 factory，禁止从生产导数据。

## 相关

- 鉴权中间件行为见 `backend/auth-permissions.md`。
"""),
    ("design/design-tokens.md", "设计 token",
     "颜色、间距、字阶的 token 定义与同步流程。",
     ["design", "tokens", "设计"], "design",
     ["web/src/styles/"], 3, "2026-05-25",
     """## 概述

设计 token 源文件在 `web/src/styles/tokens.ts`，设计稿工具单一事实源。

## 分层

- 基础 token：色板、间距刻度、字阶（原始值）。
- 语义 token：`text-primary`、`surface-raised` 等，引用基础 token。

## 同步流程

1. 设计在 Figma 改 → 2. 导出 JSON → 3. 脚本生成 tokens.ts → 4. PR 评审。
- 禁止手改 tokens.ts；diff 必须由导出脚本产生。

## 暗色模式

- 语义 token 双值（light/dark），运行时切换，不另出一份组件。

## 边界

- 组件内禁止出现字面值颜色（见 frontend/web-ui-components）。
- 新增语义 token 需要设计 + 前端双人会签。

## 相关

- 组件规范见 `frontend/web-ui-components.md`。
"""),
    ("growth/referral-program.md", "邀请返利计划",
     "邀请奖励规则、防刷策略与结算周期。",
     ["growth", "referral", "邀请", "增长"], "growth",
     ["src/growth/"], 4, "2026-06-12",
     """## 概述

邀请系统代码在 `src/growth/`，规则以本文为准。

## 规则

- 邀请人：被邀请者付费首月后，邀请人得 1 个月 pro 额度。
- 被邀请者：注册即得 14 天 pro 试用（与 pricing 试用不叠加）。

## 防刷

- 同设备/同支付账户判定为同一人，不发放奖励。
- 邀请链接带签名参数，篡改直接 400。
- 异常模式（短时批量注册）进人工审核队列。

## 结算

- 每月 5 日结算上月奖励，记录进 `referral_grants` 表。
- 奖励不可折现、不可转让。

## 边界

- 邀请转化率埋点见 data/analytics-events（`referral_signed_up`）。
- 企业客户不参与邀请计划。

## 相关

- 试用规则见 `product/pricing-page.md`；账单见 `backend/billing-invoices.md`。
"""),
    ("mobile/app-release.md", "移动客户端发版",
     "iOS/Android 发版节奏、热更新边界与灰度策略。",
     ["mobile", "release", "发版", "客户端"], "mobile",
     ["mobile/"], 3, "2026-07-01",
     """## 概述

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
"""),
]

DUMMY_FILES = {
    "src/auth/__init__.py": "\"\"\"auth package\"\"\"\n",
    "src/auth/login.py": "# 登录入口 handle_login\n",
    "src/auth/refresh.py": "# token 刷新与轮换\n",
    "src/auth/rbac.py": "# require() 权限装饰器\n",
    "src/auth/password.py": "# argon2id 参数\n",
    "src/api/session.py": "# 会话建立与 UA 指纹\n",
    "src/api/ratelimit.py": "# 滑动窗口限流\n",
    "src/api/errors.py": "# 统一错误格式\n",
    "src/billing/__init__.py": "",
    "src/billing/invoices.py": "# 账单批处理\n",
    "src/billing/webhooks.py": "# 支付回调验签与幂等\n",
    "src/billing/reconcile.py": "# 每日对账\n",
    "src/user/profile.py": "# 资料读写\n",
    "src/analytics/events.py": "# 埋点 SDK\n",
    "web/src/router/index.tsx": "// 路由与 RequireAuth\n",
    "web/src/store/index.ts": "// zustand store\n",
    "web/build/build.mjs": "// vite 构建配置\n",
    "web/src/components/Button.tsx": "// base 组件示例\n",
    "web/src/onboarding/wizard.tsx": "// 新手引导\n",
    "web/src/pricing/plans.tsx": "// 定价页\n",
    "deploy/deploy.sh": "#!/bin/sh\n# 标准发布\n",
    "deploy/rollback.sh": "#!/bin/sh\n# 一键回滚\n",
    "deploy/monitoring/alerts.yaml": "# 告警规则\n",
    "db/migrations/0001_users.sql": "-- users & auth_refresh\n",
    "etl/pipeline.py": "# 增量 ETL\n",
    "tests/test_auth.py": "# 鉴权集成测试\n",
    "web/src/styles/tokens.ts": "// 设计 token（脚本生成，勿手改）\n",
    "src/growth/referral.py": "# 邀请返利\n",
    "mobile/App.tsx": "// RN 入口\n",
}


def main():
    if os.path.isdir(DEMO):
        shutil.rmtree(DEMO)
    for rel, content in DUMMY_FILES.items():
        p = os.path.join(DEMO, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
    for rel, title, summary, kws, domain, cps, tl, va, body in SHARDS:
        kw = "[" + ", ".join(kws) + "]"
        cp = "[" + ", ".join(cps) + "]"
        fm = (
            "---\n"
            f"title: {title}\n"
            f"summary: {summary}\n"
            f"keywords: {kw}\n"
            f"domain: {domain}\n"
            f"code_paths: {cp}\n"
            f"trust_level: {tl}\n"
            f"verified_at: \"{va}\"\n"
            "---\n\n"
        )
        p = os.path.join(DEMO, "docs", "shards", rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(fm + f"# {title}\n\n" + body)
    print(f"demo_project 重建完成：{len(SHARDS)} 碎片，{len(DUMMY_FILES)} 代码占位文件")


if __name__ == "__main__":
    sys.exit(main())
