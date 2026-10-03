# 开发阶段地图 v0.2

## Phase 0 — 外部项目尽调
当前正在进行。

输出：
- reuse-analysis.md
- license-check.md
- architecture-decisions.md

## Phase 1 — Contract Freeze

冻结：
- Device Schema
- Training Module Schema
- Case Schema
- Session Schema
- Skill Schema
- Tutor Contract
- Simulation Adapter Contract
- API Contract

并完成：
- ST-001.json

## Phase 2 — Training Core
实现：
- TrainingModuleLoader
- CaseLoader
- CaseSession
- EvidenceManager
- ProgressManager

禁止：
- LLM
- 真仿真
- 复杂 UI

## Phase 3 — Diagnostic State Machine + Trace
实现：
```text
OBSERVE
→ INVESTIGATE
→ HYPOTHESIZE
→ TEST
→ UPDATE
→ DIAGNOSE
→ REFLECT
```

## Phase 4 — Skill Engine
规则评分。

Gate：
合理路径用户 > 乱点但猜对用户。

## Phase 5 — Tutor Agent
实现：
- 追问
- Hint
- 解释
- Reflection

禁止：
- 读取 Ground Truth
- 自行打分
- 自行改状态

## Phase 6 — Frontend Integration
页面：
- Dashboard
- Learning
- Scenario Brief
- Diagnostic Workspace
- Report

## Phase 7 — Case Library
先 8 个，再扩到 12。

## Phase 8 — Mock Simulation
完成稳定演示。

### 到此形成可参赛 V0

## Integration Gate v0.1
创建：
`integration/v0.1`

## Release v0.1
功能冻结，只修 bug / UI / 文案 / Demo。

完成后：
`main + tag v0.1.0`

# 冲奖增强线

## Phase 9 — Simulation Adapter
Isaac / Gazebo

## Phase 10 — Fault Injection

## Phase 11 — Episode Recorder

## Phase 12 — Auto Case Generation

最终形成：
```text
Simulation
→ Fault
→ Episode
→ Case
→ Tutor
→ Skill
```
