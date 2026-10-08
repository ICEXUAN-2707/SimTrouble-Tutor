# Documentation Index

本目录只保存研究、决策、审计和原始产品资料；冻结契约位于 `contracts/`，阶段执行规格位于 `specs/`，项目治理基线位于 `SimTrouble_FreezePack_v0.2/`。

## Canonical project documents

| File | Purpose | Status |
|---|---|---|
| `architecture-decisions.md` | Phase 0 架构决策与技术边界 | accepted; Freeze Pack 冲突时以上位基线为准 |
| `reuse-analysis.md` | 外部项目技术尽调与可复用范围 | completed |
| `license-check.md` | 外部依赖和参考项目许可检查 | completed |
| `phase1-contract-audit.md` | Phase 1 Contract 交叉审计 | passed after CCP-001/CCP-002 |
| `phase2-code-cross-audit.md` | Phase 2 到 Phase 3 的代码边界审计 | historical findings closed by Phase 3 |
| `architecture-current.md` | 当前已经实现的模块、依赖方向和限制 | current as of Phase 3 |
| `architecture-target.md` | 模块化单体目标与可替换 Adapter 方向 | approved direction; implementation remains phase-gated |

## Source material

`product/` 保存比赛详情和最初产品方案，作为需求来源与追溯材料，不是当前执行 Spec。文件保留原名，避免破坏来源语义；若与 Freeze Pack 或当前 Phase Spec 冲突，不直接据此修改实现。

## No-duplication rule

- 项目介绍只维护在根 `README.md`；
- 治理、架构和路线图只维护在 `SimTrouble_FreezePack_v0.2/`；
- 可执行需求只维护在对应 `specs/phaseX/`；
- 公共数据与接口形状只维护在 `contracts/`；
- 本目录不复制上述正文，只提供研究证据、审计记录和索引。
