---
title: 数据同步管道
summary: 业务库到分析库的 ETL 节奏、幂等与失败处理。
keywords: [data, etl, 数据管道, 同步]
domain: data
code_paths: [etl/]
trust_level: 2
verified_at: "2026-06-08"
---

# 数据同步管道

## 概述

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
