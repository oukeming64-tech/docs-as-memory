---
title: 新手引导流程
summary: 注册后引导的步骤设计、完成判定与跳过策略。
keywords: [product, onboarding, 新手引导]
domain: product
code_paths: [web/src/onboarding/]
trust_level: 4
verified_at: "2026-06-01"
---

# 新手引导流程

## 概述

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
