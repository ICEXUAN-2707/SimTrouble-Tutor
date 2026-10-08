# Phase 3 Goal — Diagnostic State Machine + Trace

> Status: APPROVED FOR IMPLEMENTATION — DG-01 through DG-04 were resolved on 2026-10-05 by the restrictive frozen-baseline rule recorded in `decision-record.md`.

## Goal

在 Phase 2 Training Core 之上建立唯一权威、确定性、可审计的诊断状态控制与 Session Trace，使所有状态变化由 Core Domain 判定，并使用冻结的 Learner Session Contract 记录全过程。

## Frozen stage map

```text
START
→ OBSERVE
→ INVESTIGATE
→ HYPOTHESIZE
→ TEST
→ UPDATE
→ DIAGNOSE
→ REFLECT
→ FINISH
```

该图冻结状态集合与主向流程。V0 Phase 3 只实现图中明确画出的单向相邻边；未明确授权的回退、回环、跳转和业务前置条件均不加入。

## Required outcomes

- Diagnostic State Machine 是 Session 状态变化的唯一写入口；
- 每次成功状态变化均可通过冻结的 Trace 字段审计；
- 非法请求不改变 Session 领域状态，只按 DG-03 追加拒绝审计事件；
- Trace 保持追加式，不通过更新既有事件改写历史；
- 现有 Phase 1 Contract 与 Phase 2 行为保持兼容；
- 无 Tutor、LLM、Skill 评分、API、UI 或仿真实现。
