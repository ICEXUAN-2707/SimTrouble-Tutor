export type TutorAction =
  | "observe_scene"
  | "inspect_evidence"
  | "submit_hypothesis"
  | "revise_hypothesis"
  | "submit_diagnosis"
  | "reflect";

export interface EvidenceOption {
  id: string;
  type: string;
}

export interface ReleasedEvidence extends EvidenceOption {
  content: Record<string, unknown>;
}

export interface SessionView {
  contract_version: string;
  session_id: string;
  case_public_state: {
    evidence_options: EvidenceOption[];
  };
  public_stage: string;
  released_evidence: ReleasedEvidence[];
  current_hypothesis: string | null;
  hypotheses: string[];
  allowed_actions: TutorAction[];
}

export interface TutorTurnResponse {
  tutor: {
    message: string;
    suggested_action: string | null;
  };
  session: SessionView;
  tutor_mode: "llm" | "rule_fallback";
}

export type DiagnosisType =
  | "object_pose_mismatch"
  | "grasp_failure"
  | "obstacle_collision_risk"
  | "placement_target_conflict";

export type DiagnosisAssessment =
  | "correct"
  | "partially_correct"
  | "incorrect"
  | "insufficient";

export type SkillDimension =
  | "hypothesis"
  | "evidence"
  | "efficiency"
  | "updating"
  | "safety";

export interface DiagnosisSubmission {
  contract_version: string;
  diagnosis_type: DiagnosisType;
  reasoning: string;
  cited_evidence_ids: string[];
}

export interface SkillDimensionResult {
  status: "scored" | "not_assessed";
  score: number | null;
  weight: number;
  rationale: string;
  rule_ids: string[];
  trace_indices: number[];
}

export interface TrainingReport {
  contract_version: string;
  rubric_version: string;
  session_id: string;
  case_id: string;
  diagnosis: {
    submitted: DiagnosisSubmission;
    assessment: DiagnosisAssessment;
    reference_explanation: string;
  };
  evidence_used: string[];
  dimension_results: Record<SkillDimension, SkillDimensionResult>;
  overall: {
    score: number | null;
    coverage: number;
    included_dimensions: SkillDimension[];
  };
  feedback_summary: string;
  next_learning_step: string;
  tutor_mode: "llm" | "rule_fallback";
}
