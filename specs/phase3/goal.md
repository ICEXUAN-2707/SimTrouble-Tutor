# Phase 3 Goal — Diagnostic State Machine + Trace

> Status: PLANNED — implementation is blocked until the open Decision Gates in `contract.md` are approved.

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

该图冻结状态集合与主向流程，但不自动授权任何回退、回环、跳转或业务前置条件；合法 transition table 必须先通过 Phase 3 Decision Gate。

## Required outcomes

- Diagnostic State Machine 是 Session 状态变化的唯一写入口；
- 每次成功状态变化均可通过冻结的 Trace 字段审计；
- 非法请求不会修改 Session；
- Trace 保持追加式，不通过更新既有事件改写历史；
- 现有 Phase 1 Contract 与 Phase 2 行为保持兼容；
- 无 Tutor、LLM、Skill 评分、API、UI 或仿真实现。
