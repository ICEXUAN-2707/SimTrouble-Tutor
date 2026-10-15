import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { renderTrainingReport } from "./report-renderer";
import type {
  DiagnosisSubmission,
  DiagnosisType,
  ReleasedEvidence,
  SessionView,
  TrainingReport,
  TutorAction,
  TutorTurnResponse,
} from "./learning-types";
import "./styles.css";

type Vec3 = [number, number, number];
type StepStatus = "READY" | "EXECUTING" | "GRASP_ATTEMPT" | "FAILURE_OBSERVED";

interface AnimationStep {
  id: string;
  label: string;
  duration_ms: number;
  status: StepStatus;
  joint_angles: [number, number, number, number];
  gripper_opening: number;
  object_attached: boolean;
}

interface SceneConfig {
  case_id: string;
  version: string;
  title: string;
  task: string;
  camera: { position: Vec3; target: Vec3; zoom: number };
  workcell: { robot_origin: Vec3; workpiece_position: Vec3; target_position: Vec3 };
  timeline: AnimationStep[];
  public_observations: string[];
}

interface SimulationSnapshot {
  stepId: string;
  status: StepStatus;
  endEffectorPosition: Vec3;
  workpiecePosition: Vec3;
  endEffectorDistance: number;
  objectAttached: boolean;
}

declare global {
  interface Window {
    __SIMTROUBLE_INSPECT__?: () => SimulationSnapshot;
  }
}

const byId = <T extends HTMLElement>(id: string): T => {
  const element = document.getElementById(id);
  if (!element) throw new Error(`Missing element #${id}`);
  return element as T;
};

const viewport = byId<HTMLDivElement>("cad-viewport");
const loadingState = byId<HTMLDivElement>("loading-state");
const playButton = byId<HTMLButtonElement>("play-button");
const resetButton = byId<HTMLButtonElement>("reset-button");
const skipButton = byId<HTMLButtonElement>("skip-button");
const faultCallout = byId<HTMLDivElement>("fault-callout");
const timelineTrack = byId<HTMLDivElement>("timeline-track");
const tutorStatus = byId<HTMLElement>("tutor-status");
const tutorLog = byId<HTMLDivElement>("tutor-log");
const tutorForm = byId<HTMLFormElement>("tutor-form");
const tutorInput = byId<HTMLTextAreaElement>("tutor-input");
const tutorSubmit = byId<HTMLButtonElement>("tutor-submit");
const sessionStage = byId<HTMLElement>("session-stage");
const sessionCode = byId<HTMLElement>("session-code");
const learningProgress = byId<HTMLElement>("learning-progress");
const learningError = byId<HTMLDivElement>("learning-error");
const learningNotice = byId<HTMLDivElement>("learning-notice");
const evidenceOptions = byId<HTMLDivElement>("evidence-options");
const hypothesisForm = byId<HTMLFormElement>("hypothesis-form");
const hypothesisInput = byId<HTMLTextAreaElement>("hypothesis-input");
const hypothesisSubmit = byId<HTMLButtonElement>("hypothesis-submit");
const hypothesisHint = byId<HTMLElement>("hypothesis-hint");
const hypothesisHistory = byId<HTMLOListElement>("hypothesis-history");
const hypothesisCount = byId<HTMLElement>("hypothesis-count");
const diagnosisStatus = byId<HTMLElement>("diagnosis-status");
const diagnosisError = byId<HTMLDivElement>("diagnosis-error");
const diagnosisNotice = byId<HTMLDivElement>("diagnosis-notice");
const diagnosisForm = byId<HTMLFormElement>("diagnosis-form");
const diagnosisType = byId<HTMLSelectElement>("diagnosis-type");
const diagnosisReasoning = byId<HTMLTextAreaElement>("diagnosis-reasoning");
const diagnosisEvidence = byId<HTMLFieldSetElement>("diagnosis-evidence");
const diagnosisCitations = byId<HTMLDivElement>("diagnosis-citations");
const diagnosisHint = byId<HTMLElement>("diagnosis-hint");
const diagnosisSubmit = byId<HTMLButtonElement>("diagnosis-submit");
const reportRetry = byId<HTMLButtonElement>("report-retry");
const reportPanel = byId<HTMLElement>("report-panel");
const reportContent = byId<HTMLDivElement>("report-content");

let config: SceneConfig;
let scene: THREE.Scene;
let camera: THREE.OrthographicCamera;
let renderer: THREE.WebGLRenderer;
let controls: OrbitControls;
let grid: THREE.GridHelper;
let axes: THREE.AxesHelper;
let robotBase: THREE.Group;
let shoulder: THREE.Group;
let elbow: THREE.Group;
let wrist: THREE.Group;
let fingerLeft: THREE.Mesh;
let fingerRight: THREE.Mesh;
let workpiece: THREE.Group;
let currentStep = 0;
let stepElapsed = 0;
let totalElapsed = 0;
let playing = false;
let previousFrame = performance.now();
let frameCounter = 0;
let fpsWindowStart = performance.now();
let sessionId: string | null = null;
let sessionView: SessionView | null = null;
let tutorBusy = false;
let learningBusy = false;
let diagnosisBusy = false;
let reportLoaded: TrainingReport | null = null;

const deg = THREE.MathUtils.degToRad;
const steel = new THREE.MeshStandardMaterial({ color: 0x76817d, roughness: 0.54, metalness: 0.68 });
const darkSteel = new THREE.MeshStandardMaterial({ color: 0x27302d, roughness: 0.48, metalness: 0.72 });
const accent = new THREE.MeshStandardMaterial({ color: 0x36b77f, roughness: 0.45, metalness: 0.5 });
const warning = new THREE.MeshStandardMaterial({ color: 0xdca74a, roughness: 0.55, metalness: 0.4 });

function part(geometry: THREE.BufferGeometry, material: THREE.Material, parent: THREE.Object3D): THREE.Mesh {
  const mesh = new THREE.Mesh(geometry, material);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  parent.add(mesh);
  const edge = new THREE.LineSegments(new THREE.EdgesGeometry(geometry), new THREE.LineBasicMaterial({ color: 0x9eaaa5, transparent: true, opacity: 0.28 }));
  mesh.add(edge);
  return mesh;
}

function buildScene(data: SceneConfig): void {
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x101514);
  scene.fog = new THREE.Fog(0x101514, 14, 28);

  const aspect = Math.max(viewport.clientWidth, 1) / Math.max(viewport.clientHeight, 1);
  camera = new THREE.OrthographicCamera(-5.6 * aspect, 5.6 * aspect, 5.6, -5.6, 0.1, 80);
  camera.position.fromArray(data.camera.position);
  camera.zoom = data.camera.zoom / 76;
  camera.lookAt(new THREE.Vector3().fromArray(data.camera.target));
  camera.updateProjectionMatrix();

  renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(viewport.clientWidth, viewport.clientHeight);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  viewport.prepend(renderer.domElement);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.target.fromArray(data.camera.target);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.minZoom = 0.55;
  controls.maxZoom = 2.8;

  scene.add(new THREE.HemisphereLight(0xc9ded6, 0x19201e, 1.45));
  const key = new THREE.DirectionalLight(0xe8f6ef, 2.4);
  key.position.set(5, 10, 7);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  scene.add(key);

  const floor = part(new THREE.BoxGeometry(12, 0.18, 8), new THREE.MeshStandardMaterial({ color: 0x1a211f, roughness: 0.9, metalness: 0.1 }), scene);
  floor.position.y = -0.12;
  grid = new THREE.GridHelper(12, 24, 0x416657, 0x28332f);
  grid.position.y = -0.015;
  scene.add(grid);
  axes = new THREE.AxesHelper(1.2);
  axes.position.set(-5.3, 0.02, 3.3);
  scene.add(axes);

  const station = new THREE.Group();
  scene.add(station);
  const table = part(new THREE.BoxGeometry(2.0, 0.18, 1.65), darkSteel, station);
  table.position.fromArray(data.workcell.workpiece_position);
  table.position.y = 0.25;
  for (const x of [-0.78, 0.78]) for (const z of [-0.6, 0.6]) {
    const leg = part(new THREE.BoxGeometry(0.12, 0.55, 0.12), steel, station);
    leg.position.set(table.position.x + x, -0.02, table.position.z + z);
  }

  workpiece = new THREE.Group();
  workpiece.position.fromArray(data.workcell.workpiece_position);
  scene.add(workpiece);
  const body = part(new THREE.CylinderGeometry(0.32, 0.32, 0.32, 32), warning, workpiece);
  body.rotation.x = Math.PI / 2;
  const bore = part(new THREE.CylinderGeometry(0.1, 0.1, 0.38, 24), darkSteel, workpiece);
  bore.rotation.x = Math.PI / 2;

  const target = new THREE.Group();
  target.position.fromArray(data.workcell.target_position);
  scene.add(target);
  const targetRing = part(new THREE.TorusGeometry(0.48, 0.035, 12, 48), accent, target);
  targetRing.rotation.x = Math.PI / 2;
  const targetCross = part(new THREE.BoxGeometry(1.1, 0.018, 0.028), accent, target);
  targetCross.position.y = 0.01;
  const targetCrossB = part(new THREE.BoxGeometry(0.028, 0.018, 1.1), accent, target);
  targetCrossB.position.y = 0.01;

  buildRobot(data.workcell.robot_origin);
}

function buildRobot(origin: Vec3): void {
  robotBase = new THREE.Group();
  robotBase.position.fromArray(origin);
  scene.add(robotBase);

  const plinth = part(new THREE.CylinderGeometry(0.68, 0.82, 0.48, 32), darkSteel, robotBase);
  plinth.position.y = 0.24;
  const turntable = part(new THREE.CylinderGeometry(0.51, 0.57, 0.22, 32), accent, robotBase);
  turntable.position.y = 0.56;

  shoulder = new THREE.Group();
  shoulder.position.y = 0.65;
  robotBase.add(shoulder);
  const jointA = part(new THREE.CylinderGeometry(0.35, 0.35, 0.58, 28), darkSteel, shoulder);
  jointA.rotation.x = Math.PI / 2;
  const upper = part(new THREE.BoxGeometry(0.44, 1.82, 0.42), steel, shoulder);
  upper.position.y = 0.91;

  elbow = new THREE.Group();
  elbow.position.y = 1.82;
  shoulder.add(elbow);
  const jointB = part(new THREE.CylinderGeometry(0.3, 0.3, 0.54, 28), accent, elbow);
  jointB.rotation.x = Math.PI / 2;
  const forearm = part(new THREE.BoxGeometry(0.38, 1.52, 0.36), steel, elbow);
  forearm.position.y = 0.76;

  wrist = new THREE.Group();
  wrist.position.y = 1.52;
  elbow.add(wrist);
  const jointC = part(new THREE.CylinderGeometry(0.25, 0.25, 0.46, 24), darkSteel, wrist);
  jointC.rotation.x = Math.PI / 2;
  const endLink = part(new THREE.BoxGeometry(0.3, 0.78, 0.3), steel, wrist);
  endLink.position.y = 0.39;
  const tool = part(new THREE.CylinderGeometry(0.2, 0.16, 0.34, 24), darkSteel, wrist);
  tool.position.y = 0.94;

  fingerLeft = part(new THREE.BoxGeometry(0.1, 0.5, 0.11), accent, wrist);
  fingerRight = part(new THREE.BoxGeometry(0.1, 0.5, 0.11), accent, wrist);
  fingerLeft.position.y = 1.3;
  fingerRight.position.y = 1.3;
}

function setRobotPose(angles: number[], opening: number): void {
  robotBase.rotation.y = deg(angles[0]);
  shoulder.rotation.z = deg(angles[1]);
  elbow.rotation.z = deg(angles[2]);
  wrist.rotation.z = deg(angles[3]);
  const spread = 0.08 + opening * 0.22;
  fingerLeft.position.x = -spread;
  fingerRight.position.x = spread;
}

function interpolatePose(stepIndex: number, progress: number): void {
  const target = config.timeline[stepIndex];
  const source = config.timeline[Math.max(0, stepIndex - 1)];
  const smooth = THREE.MathUtils.smoothstep(progress, 0, 1);
  const angles = target.joint_angles.map((value, index) => THREE.MathUtils.lerp(source.joint_angles[index], value, smooth));
  const opening = THREE.MathUtils.lerp(source.gripper_opening, target.gripper_opening, smooth);
  setRobotPose(angles, opening);
}

function inspectSimulation(): SimulationSnapshot {
  const endEffectorPosition = wrist.localToWorld(new THREE.Vector3(0, 1.3, 0));
  const workpiecePosition = workpiece.getWorldPosition(new THREE.Vector3());
  return {
    stepId: config.timeline[currentStep].id,
    status: config.timeline[currentStep].status,
    endEffectorPosition: endEffectorPosition.toArray(),
    workpiecePosition: workpiecePosition.toArray(),
    endEffectorDistance: endEffectorPosition.distanceTo(workpiecePosition),
    objectAttached: config.timeline[currentStep].object_attached,
  };
}

function renderTimeline(): void {
  timelineTrack.replaceChildren(...config.timeline.map((step, index) => {
    const node = document.createElement("div");
    node.className = "timeline-node";
    if (index < currentStep) node.classList.add("done");
    if (index === currentStep) node.classList.add(step.status === "FAILURE_OBSERVED" ? "failed" : "active");
    node.textContent = `${String(index + 1).padStart(2, "0")} ${step.id.toUpperCase()}`;
    return node;
  }));
}

function updateInterface(): void {
  const step = config.timeline[currentStep];
  byId("step-index").textContent = `${String(currentStep + 1).padStart(2, "0")} / ${String(config.timeline.length).padStart(2, "0")}`;
  byId("step-label").textContent = step.label;
  byId("case-state").textContent = step.status;
  byId("learner-phase").textContent = step.status === "FAILURE_OBSERVED" ? "OBSERVE" : playing ? "PLAYBACK" : "READY";
  byId("elapsed-label").textContent = formatTime(totalElapsed);
  playButton.textContent = playing ? "PAUSE" : currentStep === config.timeline.length - 1 ? "REPLAY" : "PLAY";
  faultCallout.hidden = step.status !== "FAILURE_OBSERVED";

  const observations = byId<HTMLUListElement>("observations");
  const messages = step.status === "FAILURE_OBSERVED" ? config.public_observations : ["Animation in progress. Observe the robot, gripper, and workpiece."];
  observations.replaceChildren(...messages.map((message) => {
    const item = document.createElement("li");
    item.textContent = message;
    return item;
  }));
  renderTimeline();
}

function formatTime(milliseconds: number): string {
  const seconds = milliseconds / 1000;
  const mins = Math.floor(seconds / 60).toString().padStart(2, "0");
  const secs = Math.floor(seconds % 60).toString().padStart(2, "0");
  const tenths = Math.floor((seconds % 1) * 10);
  return `${mins}:${secs}.${tenths}`;
}

function advanceStep(): void {
  if (currentStep < config.timeline.length - 1) {
    currentStep += 1;
    stepElapsed = 0;
    updateInterface();
  } else {
    playing = false;
    updateInterface();
  }
}

function resetPlayback(): void {
  currentStep = 0;
  stepElapsed = 0;
  totalElapsed = 0;
  playing = false;
  workpiece.position.fromArray(config.workcell.workpiece_position);
  setRobotPose(config.timeline[0].joint_angles, config.timeline[0].gripper_opening);
  updateInterface();
}

function bindControls(): void {
  playButton.addEventListener("click", () => {
    if (currentStep === config.timeline.length - 1 && !playing) resetPlayback();
    playing = !playing;
    updateInterface();
  });
  resetButton.addEventListener("click", resetPlayback);
  skipButton.addEventListener("click", () => {
    if (currentStep === config.timeline.length - 1) return;
    currentStep += 1;
    stepElapsed = config.timeline[currentStep].duration_ms;
    interpolatePose(currentStep, 1);
    updateInterface();
  });

  document.querySelectorAll<HTMLButtonElement>("[data-tool]").forEach((button) => button.addEventListener("click", () => {
    const tool = button.dataset.tool;
    if (tool === "grid") grid.visible = !grid.visible;
    if (tool === "axes") axes.visible = !axes.visible;
    if (tool === "fit") fitView();
    if (tool === "orbit" || tool === "pan") {
      document.querySelectorAll("[data-tool='orbit'], [data-tool='pan']").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      controls.mouseButtons.LEFT = tool === "pan" ? THREE.MOUSE.PAN : THREE.MOUSE.ROTATE;
    } else button.classList.toggle("active");
  }));
}

class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(detail);
  }
}

async function requestJson<T>(url: string, init: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: { Accept: "application/json", "Content-Type": "application/json" },
  });
  if (!response.ok) {
    let detail = "request_failed";
    try {
      const payload = await response.json() as { detail?: unknown };
      if (typeof payload.detail === "string") detail = payload.detail;
    } catch {
      // Keep the stable fallback when an upstream response is not JSON.
    }
    throw new ApiError(response.status, detail);
  }
  return await response.json() as T;
}

function learningErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return "操作失败，请检查服务连接后重试。当前学习进度已保留。";
  const messages: Record<string, string> = {
    invalid_session_stage: "当前学习阶段不允许此操作，请按可用步骤继续。",
    evidence_not_found: "该证据不存在或已不可用，请选择列表中的证据。",
    session_not_found: "学习会话已失效，请刷新页面创建新会话。",
  };
  return messages[error.detail] ?? `操作失败（HTTP ${error.status}），当前学习进度已保留。`;
}

function hasAction(action: TutorAction): boolean {
  return sessionView?.allowed_actions.includes(action) ?? false;
}

function formatEvidenceValue(value: unknown): string {
  if (typeof value === "boolean") return value ? "YES" : "NO";
  if (value === null) return "NULL";
  if (Array.isArray(value)) return value.map(formatEvidenceValue).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function setLearningNotice(message: string): void {
  learningNotice.textContent = message;
  learningNotice.hidden = false;
}

function clearLearningError(): void {
  learningError.hidden = true;
  learningError.textContent = "";
}

function showLearningError(error: unknown): void {
  learningError.textContent = learningErrorMessage(error);
  learningError.hidden = false;
}

const diagnosisTypes = new Set<string>([
  "object_pose_mismatch",
  "grasp_failure",
  "obstacle_collision_risk",
  "placement_target_conflict",
]);

function isDiagnosisType(value: string): value is DiagnosisType {
  return diagnosisTypes.has(value);
}

function diagnosisErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return "诊断操作失败，请检查服务连接后重试。当前学习进度已保留。";
  const messages: Record<string, string> = {
    diagnosis_already_submitted: "本会话已提交过诊断，不能重复提交。",
    invalid_session_stage: "当前学习阶段不允许提交诊断，请先完成证据调查和假设修正。",
    invalid_evidence_reference: "诊断引用包含未释放的 Evidence，请重新选择。",
    report_not_ready: "训练报告尚未就绪，请稍后重试读取报告。",
    session_not_found: "学习会话已失效，请刷新页面创建新会话。",
  };
  return messages[error.detail] ?? `诊断操作失败（HTTP ${error.status}），当前学习进度已保留。`;
}

function setDiagnosisNotice(message: string): void {
  diagnosisNotice.textContent = message;
  diagnosisNotice.hidden = false;
}

function clearDiagnosisError(): void {
  diagnosisError.textContent = "";
  diagnosisError.hidden = true;
}

function showDiagnosisError(error: unknown): void {
  diagnosisError.textContent = diagnosisErrorMessage(error);
  diagnosisError.hidden = false;
}

function selectedEvidenceIds(): string[] {
  const releasedIds = new Set(sessionView?.released_evidence.map((evidence) => evidence.id) ?? []);
  return Array.from(
    diagnosisCitations.querySelectorAll<HTMLInputElement>("input[type='checkbox']:checked"),
    (input) => input.value,
  ).filter((evidenceId) => releasedIds.has(evidenceId));
}

function renderDiagnosisCitations(): void {
  const selected = new Set(selectedEvidenceIds());
  const released = sessionView?.released_evidence ?? [];
  if (released.length === 0) {
    const empty = document.createElement("p");
    empty.textContent = "尚无已释放 Evidence";
    diagnosisCitations.replaceChildren(empty);
    return;
  }
  diagnosisCitations.replaceChildren(...released.map((evidence) => {
    const label = document.createElement("label");
    label.className = "diagnosis-citation";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = evidence.id;
    checkbox.checked = selected.has(evidence.id);
    const copy = document.createElement("span");
    const id = document.createElement("strong");
    const type = document.createElement("small");
    id.textContent = evidence.id;
    type.textContent = evidence.type.replaceAll("_", " ").toUpperCase();
    copy.append(id, type);
    label.append(checkbox, copy);
    return label;
  }));
}

function updateDiagnosisControls(): void {
  const canSubmit = hasAction("submit_diagnosis");
  const submitted = sessionView?.public_stage === "SUBMITTED"
    || sessionView?.public_stage === "REVIEWED"
    || reportLoaded !== null;
  const interactionBusy = learningBusy || tutorBusy || diagnosisBusy;
  const unlocked = canSubmit && !submitted && !interactionBusy;
  diagnosisType.disabled = !unlocked;
  diagnosisReasoning.disabled = !unlocked;
  diagnosisEvidence.disabled = !unlocked;
  diagnosisCitations.querySelectorAll<HTMLInputElement>("input[type='checkbox']")
    .forEach((input) => { input.disabled = !unlocked; });

  const complete = isDiagnosisType(diagnosisType.value)
    && diagnosisReasoning.value.trim().length > 0
    && selectedEvidenceIds().length > 0;
  diagnosisSubmit.disabled = !unlocked || !complete;
  diagnosisSubmit.textContent = diagnosisBusy ? "SUBMITTING…" : "SUBMIT DIAGNOSIS";
  reportRetry.disabled = diagnosisBusy;

  diagnosisStatus.textContent = reportLoaded !== null
    ? "REVIEWED"
    : submitted
      ? "SUBMITTED"
      : canSubmit
        ? "READY"
        : "LOCKED";
  diagnosisStatus.classList.toggle("ready", canSubmit && !submitted);

  diagnosisHint.textContent = reportLoaded !== null
    ? "报告已生成，诊断不可再次提交"
    : submitted
      ? "诊断已提交，等待报告"
      : canSubmit
        ? complete
          ? "提交后不可修改"
          : "需要诊断类型、理由和至少一条 Evidence"
        : "完成一次假设修正后解锁";
}

function setDiagnosisBusy(busy: boolean): void {
  diagnosisBusy = busy;
  renderEvidence();
  updateHypothesisControls();
  setTutorBusy(tutorBusy);
  updateDiagnosisControls();
}

async function fetchTrainingReport(): Promise<boolean> {
  if (sessionId === null) return false;
  reportRetry.hidden = true;
  setDiagnosisNotice("正在读取确定性训练报告…");
  try {
    const report = await requestJson<TrainingReport>(
      `/api/v0.4/sessions/${encodeURIComponent(sessionId)}/report`,
      { method: "GET" },
    );
    if (report.session_id !== sessionId) {
      throw new Error("Report session mismatch");
    }
    reportLoaded = report;
    renderTrainingReport(reportContent, report);
    reportPanel.hidden = false;
    clearDiagnosisError();
    setDiagnosisNotice("诊断已完成。以下内容由后端评估与评分管线生成。");
    updateDiagnosisControls();

    try {
      const reviewed = await requestJson<SessionView>(
        `/api/v0.4/sessions/${encodeURIComponent(sessionId)}`,
        { method: "GET" },
      );
      renderSession(reviewed);
    } catch {
      setDiagnosisNotice("报告已生成；公开 Session 阶段刷新失败，不影响报告结果。");
    }
    reportPanel.scrollIntoView({ block: "start" });
    return true;
  } catch (error) {
    showDiagnosisError(error);
    if (error instanceof ApiError && error.detail === "report_not_ready") {
      reportRetry.hidden = false;
      setDiagnosisNotice("报告尚未就绪。当前 Session 已保留，可手动重试读取。");
    } else {
      setDiagnosisNotice("报告读取失败。诊断提交状态和当前 Session 已保留。");
    }
    return false;
  }
}

function updateHypothesisControls(): void {
  const canSubmit = hasAction("submit_hypothesis");
  const canRevise = hasAction("revise_hypothesis");
  const actionAvailable = canSubmit || canRevise;
  hypothesisInput.disabled = !actionAvailable || learningBusy || tutorBusy || diagnosisBusy;
  hypothesisSubmit.disabled = hypothesisInput.disabled || hypothesisInput.value.trim().length === 0;
  hypothesisSubmit.textContent = canRevise ? "REVISE HYPOTHESIS" : "SUBMIT HYPOTHESIS";
  hypothesisHint.textContent = canRevise
    ? "可依据新证据修正"
    : canSubmit
      ? "提交初始假设"
      : "等待 Evidence 解锁";
}

function renderEvidence(): void {
  if (sessionView === null) {
    evidenceOptions.replaceChildren();
    return;
  }
  const released = new Map(sessionView.released_evidence.map((item) => [item.id, item]));
  const canInspect = hasAction("inspect_evidence") && !learningBusy && !tutorBusy && !diagnosisBusy;
  evidenceOptions.replaceChildren(...sessionView.case_public_state.evidence_options.map((option) => {
    const card = document.createElement("article");
    card.className = "evidence-card";
    const evidence = released.get(option.id);
    if (evidence) card.classList.add("released");

    const heading = document.createElement("div");
    heading.className = "evidence-heading";
    const title = document.createElement("strong");
    title.textContent = option.id;
    const type = document.createElement("span");
    type.textContent = option.type.replaceAll("_", " ").toUpperCase();
    heading.append(title, type);
    card.append(heading);

    if (evidence) {
      const values = document.createElement("dl");
      values.className = "evidence-values";
      for (const [key, value] of Object.entries(evidence.content)) {
        const term = document.createElement("dt");
        const detail = document.createElement("dd");
        term.textContent = key.replaceAll("_", " ").toUpperCase();
        detail.textContent = formatEvidenceValue(value);
        values.append(term, detail);
      }
      card.append(values);
    } else {
      const locked = document.createElement("p");
      locked.className = "evidence-locked";
      locked.textContent = "测量值未释放";
      card.append(locked);
    }

    const button = document.createElement("button");
    button.type = "button";
    button.dataset.evidenceId = option.id;
    button.disabled = evidence !== undefined || !canInspect;
    button.textContent = evidence ? "RELEASED" : learningBusy ? "REQUESTING…" : "REQUEST";
    card.append(button);
    return card;
  }));
}

function renderSession(view: SessionView): void {
  sessionView = view;
  sessionId = view.session_id;
  sessionStage.textContent = view.public_stage;
  sessionStage.classList.remove("pending");
  sessionCode.textContent = view.session_id.slice(0, 8).toUpperCase();
  sessionCode.title = view.session_id;
  learningProgress.textContent = `${view.released_evidence.length} / ${view.case_public_state.evidence_options.length} EVIDENCE`;
  hypothesisCount.textContent = `${view.hypotheses.length} ${view.hypotheses.length === 1 ? "ENTRY" : "ENTRIES"}`;
  hypothesisHistory.replaceChildren(...(
    view.hypotheses.length > 0
      ? view.hypotheses.map((hypothesis, index) => {
        const item = document.createElement("li");
        item.textContent = hypothesis;
        if (index === view.hypotheses.length - 1) item.classList.add("current");
        return item;
      })
      : [Object.assign(document.createElement("li"), { className: "empty", textContent: "尚未提交假设" })]
  ));
  if (document.activeElement !== hypothesisInput) {
    hypothesisInput.value = view.current_hypothesis ?? "";
  }
  renderEvidence();
  updateHypothesisControls();
  renderDiagnosisCitations();
  updateDiagnosisControls();
}

function setLearningBusy(busy: boolean): void {
  learningBusy = busy;
  if (sessionView) renderSession(sessionView);
  setTutorBusy(tutorBusy);
}

function appendTutorMessage(
  role: "learner" | "tutor" | "system",
  message: string,
  mode?: "llm" | "rule_fallback",
  suggestedAction?: string | null,
): HTMLElement {
  const item = document.createElement("article");
  item.className = `tutor-message ${role}`;
  if (mode) item.dataset.mode = mode;
  const label = document.createElement("span");
  label.textContent = role === "learner"
    ? "LEARNER"
    : role === "system"
      ? "SYSTEM"
      : mode === "llm" ? "TUTOR / LLM" : "TUTOR / RULE FALLBACK";
  const copy = document.createElement("p");
  copy.textContent = message;
  item.append(label, copy);
  if (suggestedAction) {
    const action = document.createElement("small");
    action.textContent = `NEXT ACTION / ${suggestedAction.toUpperCase()}`;
    item.append(action);
  }
  tutorLog.append(item);
  tutorLog.scrollTop = tutorLog.scrollHeight;
  return item;
}

function setTutorBusy(busy: boolean): void {
  tutorBusy = busy;
  tutorInput.disabled = busy || learningBusy || diagnosisBusy || sessionId === null;
  tutorSubmit.disabled = busy || learningBusy || diagnosisBusy || sessionId === null;
  tutorSubmit.textContent = busy ? "PROCESSING…" : "REQUEST HINT";
  if (sessionView) {
    renderEvidence();
    updateHypothesisControls();
    updateDiagnosisControls();
  }
}

async function initialiseLearningSession(): Promise<void> {
  try {
    const session = await requestJson<SessionView>("/api/v0.4/sessions", {
      method: "POST",
      body: JSON.stringify({ case_id: config.case_id }),
    });
    renderSession(session);
    tutorStatus.textContent = "READY";
    tutorStatus.classList.remove("pending");
    tutorLog.replaceChildren();
    appendTutorMessage("system", "会话已建立。请先描述观察，再请求诊断提示。");
    setLearningNotice("会话已建立。请请求一条 Evidence 开始调查。");
    clearLearningError();
    setTutorBusy(false);
  } catch (error) {
    sessionStage.textContent = "OFFLINE";
    tutorStatus.textContent = "OFFLINE";
    showLearningError(error);
    setLearningNotice("未创建新会话。修复连接后刷新页面重试。");
    appendTutorMessage("system", error instanceof Error ? error.message : "Tutor session unavailable");
  }
}

function bindLearning(): void {
  evidenceOptions.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLButtonElement)) return;
    const evidenceId = target.dataset.evidenceId;
    if (!evidenceId || !sessionId || !hasAction("inspect_evidence") || learningBusy || tutorBusy || diagnosisBusy) return;
    clearLearningError();
    setLearningBusy(true);
    setLearningNotice(`正在请求 ${evidenceId}…`);
    try {
      const response = await requestJson<{ evidence: ReleasedEvidence; session: SessionView }>(
        `/api/v0.4/sessions/${encodeURIComponent(sessionId)}/evidence`,
        { method: "POST", body: JSON.stringify({ evidence_id: evidenceId }) },
      );
      renderSession(response.session);
      setLearningNotice(`${response.evidence.id} 已释放。测量值现已加入本会话。`);
    } catch (error) {
      showLearningError(error);
      setLearningNotice("请求未完成；已释放证据和假设均保持不变。");
    } finally {
      setLearningBusy(false);
    }
  });

  hypothesisInput.addEventListener("input", updateHypothesisControls);
  hypothesisForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const hypothesis = hypothesisInput.value.trim();
    const actionAvailable = hasAction("submit_hypothesis") || hasAction("revise_hypothesis");
    if (!hypothesis || !sessionId || !actionAvailable || learningBusy || tutorBusy || diagnosisBusy) return;
    clearLearningError();
    setLearningBusy(true);
    setLearningNotice("正在提交假设…");
    try {
      const response = await requestJson<SessionView>(
        `/api/v0.4/sessions/${encodeURIComponent(sessionId)}/hypotheses`,
        { method: "POST", body: JSON.stringify({ hypothesis }) },
      );
      renderSession(response);
      setLearningNotice(response.hypotheses.length > 1 ? "假设已修正，诊断提交现已解锁。" : "初始假设已记录。请继续请求证据并修正假设。");
    } catch (error) {
      showLearningError(error);
      setLearningNotice("提交未完成；输入内容和现有学习进度均已保留。");
    } finally {
      setLearningBusy(false);
    }
  });
}

function bindDiagnosis(): void {
  diagnosisType.addEventListener("change", updateDiagnosisControls);
  diagnosisReasoning.addEventListener("input", updateDiagnosisControls);
  diagnosisCitations.addEventListener("change", updateDiagnosisControls);

  diagnosisForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const diagnosisValue = diagnosisType.value;
    const reasoning = diagnosisReasoning.value.trim();
    const citedEvidenceIds = selectedEvidenceIds();
    if (
      sessionId === null
      || !isDiagnosisType(diagnosisValue)
      || !reasoning
      || citedEvidenceIds.length === 0
      || !hasAction("submit_diagnosis")
      || diagnosisBusy
      || learningBusy
      || tutorBusy
    ) return;

    const submission: DiagnosisSubmission = {
      contract_version: "0.4.0",
      diagnosis_type: diagnosisValue,
      reasoning,
      cited_evidence_ids: citedEvidenceIds,
    };
    clearDiagnosisError();
    setDiagnosisNotice("正在提交一次性诊断…");
    setDiagnosisBusy(true);
    try {
      const submitted = await requestJson<SessionView>(
        `/api/v0.4/sessions/${encodeURIComponent(sessionId)}/diagnosis`,
        { method: "POST", body: JSON.stringify(submission) },
      );
      renderSession(submitted);
      setDiagnosisNotice("诊断已提交，正在读取训练报告…");
    } catch (error) {
      showDiagnosisError(error);
      setDiagnosisNotice("诊断未提交；表单内容、Evidence 和学习进度均已保留。");
      setDiagnosisBusy(false);
      return;
    }

    await fetchTrainingReport();
    setDiagnosisBusy(false);
  });

  reportRetry.addEventListener("click", async () => {
    if (sessionId === null || diagnosisBusy) return;
    clearDiagnosisError();
    setDiagnosisBusy(true);
    await fetchTrainingReport();
    setDiagnosisBusy(false);
  });
}

function bindTutor(): void {
  tutorForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = tutorInput.value.trim();
    if (!message || sessionId === null || tutorBusy || learningBusy || diagnosisBusy) return;
    appendTutorMessage("learner", message);
    tutorInput.value = "";
    setTutorBusy(true);
    tutorStatus.textContent = "THINKING";
    try {
      const response = await requestJson<TutorTurnResponse>(
        `/api/v0.4/sessions/${encodeURIComponent(sessionId)}/tutor`,
        { method: "POST", body: JSON.stringify({ message }) },
      );
      appendTutorMessage(
        "tutor",
        response.tutor.message,
        response.tutor_mode,
        response.tutor.suggested_action,
      );
      renderSession(response.session);
      tutorStatus.textContent = response.tutor_mode === "llm" ? "LLM" : "SAFE FALLBACK";
    } catch (error) {
      appendTutorMessage("system", "Tutor 请求失败，请稍后重试。学习会话仍然保留。");
      tutorStatus.textContent = "RETRY";
      console.error(error);
    } finally {
      setTutorBusy(false);
      tutorInput.focus();
    }
  });
}

function fitView(): void {
  camera.position.fromArray(config.camera.position);
  camera.zoom = config.camera.zoom / 76;
  controls.target.fromArray(config.camera.target);
  camera.lookAt(controls.target);
  camera.updateProjectionMatrix();
  controls.update();
}

function resizeViewport(): void {
  const width = Math.max(viewport.clientWidth, 1);
  const height = Math.max(viewport.clientHeight, 1);
  const halfHeight = 5.6;
  const halfWidth = halfHeight * (width / height);
  camera.left = -halfWidth;
  camera.right = halfWidth;
  camera.top = halfHeight;
  camera.bottom = -halfHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height, false);
}

function animate(now: number): void {
  requestAnimationFrame(animate);
  const delta = Math.min(now - previousFrame, 80);
  previousFrame = now;

  if (playing) {
    stepElapsed += delta;
    totalElapsed += delta;
    const step = config.timeline[currentStep];
    interpolatePose(currentStep, Math.min(stepElapsed / step.duration_ms, 1));
    byId("elapsed-label").textContent = formatTime(totalElapsed);
    if (stepElapsed >= step.duration_ms) advanceStep();
  }

  controls.update();
  renderer.render(scene, camera);
  frameCounter += 1;
  if (now - fpsWindowStart >= 750) {
    const fps = Math.round((frameCounter * 1000) / (now - fpsWindowStart));
    byId("fps-label").textContent = `${fps} FPS`;
    frameCounter = 0;
    fpsWindowStart = now;
  }
  const position = camera.position.toArray().map((value) => value.toFixed(1));
  byId("camera-readout").textContent = `X ${position[0]} / Y ${position[1]} / Z ${position[2]}`;
}

async function initialise(): Promise<void> {
  try {
    const response = await fetch("/api/v0.4/cases/ST-001/scene", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`Scene API returned ${response.status}`);
    config = await response.json() as SceneConfig;
    byId("case-code").textContent = config.case_id;
    byId("case-title").textContent = config.title;
    byId("task-title").textContent = config.title;
    byId("task-copy").textContent = config.task;
    buildScene(config);
    setRobotPose(config.timeline[0].joint_angles, config.timeline[0].gripper_opening);
    Object.defineProperty(window, "__SIMTROUBLE_INSPECT__", {
      configurable: true,
      value: inspectSimulation,
    });
    bindControls();
    bindLearning();
    bindDiagnosis();
    bindTutor();
    updateInterface();
    loadingState.hidden = true;
    new ResizeObserver(resizeViewport).observe(viewport);
    requestAnimationFrame(animate);
    await initialiseLearningSession();
  } catch (error) {
    loadingState.replaceChildren();
    const heading = document.createElement("strong");
    const detail = document.createElement("small");
    heading.textContent = "SCENE UNAVAILABLE";
    detail.textContent = error instanceof Error ? error.message : "Unknown initialisation error";
    loadingState.append(heading, detail);
    console.error(error);
  }
}

void initialise();
