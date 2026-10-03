# Contract Freeze v0.2

## 1. Case Contract

```json
{
  "case_id": "ST-001",
  "device_type": "industrial_robot",
  "scenario": "flexible_handling",
  "difficulty": 1,
  "task": {"type": "pick_and_place"},
  "fault": {
    "type": "object_pose_offset",
    "parameters": {"axis": "x", "offset_mm": 70}
  },
  "initial_state": {},
  "initial_observation": [],
  "evidence": [
    {
      "id": "E01",
      "type": "gripper_state",
      "content": {},
      "information_value": 10,
      "related_faults": []
    }
  ],
  "ground_truth": {"diagnosis": "object_pose_mismatch"},
  "optimal_path": [],
  "safety_rules": [],
  "scoring_rules": {}
}
```

### 强约束
- `ground_truth` 不得通过 learner-facing API 返回
- hidden evidence 未披露前不得进入 Tutor Context
- Case 必须可在不依赖 LLM 的情况下完整执行

## 2. Session Contract

```json
{
  "session_id": "uuid",
  "case_id": "ST-001",
  "user_id": "user-001",
  "current_stage": "INVESTIGATE",
  "evidence_seen": [],
  "current_hypothesis": null,
  "hypothesis_history": [],
  "actions": [],
  "hint_count": 0,
  "wrong_branch_count": 0,
  "skill_scores": {
    "hypothesis": 0,
    "evidence": 0,
    "efficiency": 0,
    "updating": 0,
    "safety": 0
  }
}
```

### Session Trace 至少记录
- timestamp
- stage
- action_type
- evidence_id
- current_hypothesis
- tutor_hint
- result

## 3. Diagnostic State Contract

```text
START
↓
OBSERVE
↓
INVESTIGATE
↓
HYPOTHESIZE
↓
TEST
↓
UPDATE
↓
DIAGNOSE
↓
REFLECT
↓
FINISH
```

约束：
- 所有状态变化必须可审计
- Tutor 不得自行跳状态
- 前端不得直接改 Session State
- State transition 由 Core Domain 决定

## 4. Skill Contract

五维：
- Hypothesis
- Evidence
- Efficiency
- Updating
- Safety

V0 使用规则评分，必须可解释。

禁止：
- LLM 直接给最终分数
- 黑箱 ML 替代 V0 规则评分

## 5. Tutor Agent Contract

### 输入
- Training Module
- Case Public State
- Evidence Seen
- Learner Action History
- Current Hypothesis
- Current Skill Profile
- Allowed Tutor Actions

### 禁止输入
- Ground Truth
- 未披露 Hidden Evidence
- 完整 Optimal Path

### 输出
```json
{
  "intent": "question|hint|explain|reflect",
  "message": "string",
  "suggested_next_step": null
}
```

## 6. Simulation Adapter Contract

```python
class SimulationAdapter:
    def reset_scenario(self, case_id: str): ...
    def get_state(self) -> dict: ...
    def perform_action(self, action: dict) -> dict: ...
    def get_evidence(self, evidence_id: str) -> dict: ...
    def inject_fault(self, fault_config: dict) -> None: ...
    def get_result(self) -> dict: ...
```

V0: `MockSimulationAdapter`

V1: `IsaacSimulationAdapter` 或 `GazeboSimulationAdapter`

## 7. API Contract v0

```text
GET    /modules
GET    /modules/{id}
GET    /cases/{case_id}

POST   /sessions
GET    /sessions/{session_id}

POST   /sessions/{id}/evidence
POST   /sessions/{id}/hypothesis
POST   /sessions/{id}/action
POST   /sessions/{id}/diagnosis

GET    /sessions/{id}/report
```

所有 API 变更：
1. 先修改 Contract
2. Tech Lead Review
3. 再修改代码
