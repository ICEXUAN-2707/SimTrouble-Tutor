import { evidenceName, sourceText } from "./ui-copy";
import type {
  DiagnosisAssessment,
  DiagnosisType,
  SkillDimension,
  TrainingReport,
} from "./learning-types";

const assessmentLabels: Record<DiagnosisAssessment, string> = {
  correct: "正确",
  partially_correct: "部分正确",
  incorrect: "错误",
  insufficient: "证据不足",
};

const diagnosisLabels: Record<DiagnosisType, string> = {
  object_pose_mismatch: "物体位姿不匹配",
  grasp_failure: "抓取失败",
  obstacle_collision_risk: "障碍碰撞风险",
  placement_target_conflict: "放置目标冲突",
};

const dimensionLabels: Record<SkillDimension, string> = {
  hypothesis: "假设质量",
  evidence: "证据运用",
  efficiency: "诊断效率",
  updating: "假设修正",
  safety: "安全意识",
};

const dimensions: SkillDimension[] = [
  "hypothesis",
  "evidence",
  "efficiency",
  "updating",
  "safety",
];

function element<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className: string,
  text?: string,
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function metric(label: string, value: string, testId?: string): HTMLElement {
  const item = element("div", "report-metric");
  const caption = element("span", "", label);
  const result = element("strong", "", value);
  if (testId) result.dataset.testid = testId;
  item.append(caption, result);
  return item;
}

export function renderTrainingReport(container: HTMLElement, report: TrainingReport): void {
  const fragment = document.createDocumentFragment();

  const hero = element("div", "report-hero");
  hero.dataset.assessment = report.diagnosis.assessment;
  const heroCopy = element("div", "");
  heroCopy.append(
    element("small", "report-kicker", "诊断评价"),
    element("strong", "report-assessment", assessmentLabels[report.diagnosis.assessment]),
  );
  const score = report.overall.score === null ? "未评价" : String(report.overall.score);
  hero.append(heroCopy, metric("综合评分", score, "overall-score"));
  fragment.append(hero);

  const metrics = element("div", "report-metrics");
  metrics.append(
    metric("评价覆盖率", `${Math.round(report.overall.coverage * 100)}%`, "report-coverage"),
    metric("助教服务", report.tutor_mode === "llm" ? "智能引导" : "基础引导", "report-tutor-mode"),
  );
  fragment.append(metrics);

  const diagnosis = element("section", "report-section diagnosis-review");
  diagnosis.append(element("h3", "", "诊断复核"));
  const submitted = element("dl", "report-definition-list");
  submitted.append(
    element("dt", "", "提交诊断"),
    element("dd", "", diagnosisLabels[report.diagnosis.submitted.diagnosis_type]),
    element("dt", "", "诊断理由"),
    element("dd", "", report.diagnosis.submitted.reasoning),
    element("dt", "", "参考解释"),
    element("dd", "", sourceText(report.diagnosis.reference_explanation)),
  );
  diagnosis.append(submitted);
  const evidence = element("div", "report-evidence");
  evidence.append(element("span", "", "引用证据"));
  for (const evidenceId of report.evidence_used) {
    evidence.append(element("code", "", evidenceName(evidenceId)));
  }
  diagnosis.append(evidence);
  fragment.append(diagnosis);

  const dimensionSection = element("section", "report-section");
  dimensionSection.append(element("h3", "", "五维能力评估"));
  const dimensionGrid = element("div", "dimension-grid");
  for (const dimension of dimensions) {
    const result = report.dimension_results[dimension];
    const card = element("article", "dimension-card");
    card.dataset.dimension = dimension;
    card.dataset.status = result.status;
    const heading = element("div", "dimension-heading");
    heading.append(
      element("strong", "", dimensionLabels[dimension]),
      element(
        "span",
        "dimension-score",
        result.status === "not_assessed" || result.score === null ? "未评估" : `${result.score} / 100`,
      ),
    );
    card.append(heading, element("p", "", sourceText(result.rationale)));

    dimensionGrid.append(card);
  }
  dimensionSection.append(dimensionGrid);
  fragment.append(dimensionSection);

  const feedback = element("section", "report-section report-feedback");
  feedback.append(
    element("h3", "", "训练反馈"),
    element("p", "", sourceText(report.feedback_summary)),
    element("h4", "", "下一步建议"),
    element("p", "", sourceText(report.next_learning_step)),
  );
  fragment.append(feedback);

  container.replaceChildren(fragment);
}
