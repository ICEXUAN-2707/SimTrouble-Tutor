# SimTrouble Tutor Workspace

## 当前状态

- 当前阶段：**Phase 2 — Training Core**（Phase 1 Contract Freeze 已通过）
- 当前唯一上位基线：[`SimTrouble_FreezePack_v0.2/`](SimTrouble_FreezePack_v0.2/)
- Phase 1 任务规格：[`specs/phase1/`](specs/phase1/)
- Phase 1 契约：[`contracts/`](contracts/)
- 首个 Case：[`data/cases/ST-001.json`](data/cases/ST-001.json)
- Phase 1 交叉审计：[`docs/phase1-contract-audit.md`](docs/phase1-contract-audit.md)
- 当前实现规范：[`specs/phase2/`](specs/phase2/)

## 本地验证

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_*.py" -v
```

## 目录职责

```text
SimTrouble_FreezePack_v0.2/  冻结的治理、架构、路线图和开发规则
specs/phase1/                本阶段 goal/context/contract/acceptance/out_of_scope
contracts/                   Schema 与接口契约；不是产品实现
data/cases/                  已冻结 Case 数据
docs/                        Phase 0 尽调和产品原始资料
tests/contracts/             契约静态校验
```

## 规范优先级

1. `SimTrouble_FreezePack_v0.2/`
2. 当前 `specs/<phase>/`
3. `contracts/`
4. `docs/` 中的研究与原始产品材料

发生冲突时停止实现并提交 Contract Change Proposal，不通过代码或 Schema 擅自修改冻结需求。

## Phase 1 禁止项

本阶段不实现前后端、Core、状态机、Skill 算法、Tutor/LLM、RAG、Mock/真实仿真、Fault Injection 或 Episode Recorder。
