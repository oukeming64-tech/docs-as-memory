---
title: 更新日志规范
summary: changelog 的撰写规范、分类标签与发布节奏。
keywords: [product, changelog, 更新日志]
domain: product
code_paths: []
trust_level: 4
verified_at: "2026-05-10"
---

# 更新日志规范

## 概述

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
