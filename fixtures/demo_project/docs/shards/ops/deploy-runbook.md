---
title: 部署手册
summary: 标准发布流程、回滚步骤与发布窗口。
keywords: [ops, deploy, 部署, 发布]
domain: ops
code_paths: [deploy/]
trust_level: 1
verified_at: "2026-07-22"
---

# 部署手册

## 概述

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
