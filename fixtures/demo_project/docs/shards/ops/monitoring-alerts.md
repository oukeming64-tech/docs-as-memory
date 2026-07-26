---
title: 监控与告警
summary: 核心指标、告警分级与值班响应时限。
keywords: [ops, monitoring, alert, 监控, 告警]
domain: ops
code_paths: [deploy/monitoring/]
trust_level: 2
verified_at: "2026-07-15"
---

# 监控与告警

## 概述

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
