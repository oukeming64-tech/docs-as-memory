---
title: 事故应急响应
summary: 事故分级、响应流程与复盘要求。
keywords: [ops, incident, 事故, 应急响应]
domain: ops
code_paths: []
trust_level: 2
verified_at: "2026-06-20"
---

# 事故应急响应

## 概述

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
