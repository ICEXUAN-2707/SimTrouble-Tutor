import { initialiseWorkspace, syncWorkspace, showReport } from "./workspace-controller";
import { label as uiLabel, evidenceName, formatValue, sourceText, fieldLabel } from "./ui-copy";
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
import "./fonts.css";
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

interface AuthUser {
  user_id: string;
  username: string;
  display_name: string;
}

interface AuthSession {
  user: AuthUser;
  expires_at: number;
  csrf_token: string;
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
const reportContent = byId<HTMLDivElement>("report-content");
const appRoot = byId<HTMLDivElement>("app");
const authShell = byId<HTMLElement>("auth-shell");
const authForm = byId<HTMLFormElement>("auth-form");
const authTitle = byId<HTMLElement>("auth-title");
const authSubtitle = byId<HTMLElement>("auth-subtitle");
const authError = byId<HTMLDivElement>("auth-error");
const authUsername = byId<HTMLInputElement>("auth-username");
const authPassword = byId<HTMLInputElement>("auth-password");
const authDisplayName = byId<HTMLInputElement>("auth-display-name");
const displayNameField = byId<HTMLElement>("display-name-field");
const authSubmit = byId<HTMLButtonElement>("auth-submit");
const loginTab = byId<HTMLButtonElement>("login-tab");
const registerTab = byId<HTMLButtonElement>("register-tab");
const signedUser = byId<HTMLElement>("signed-user");
const logoutButton = byId<HTMLButtonElement>("logout-button");

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
let hypothesisDirty = false;
const expandedEvidence = new Map<string, boolean>();

let sessionId: string | null = null;
let sessionView: SessionView | null = null;
let tutorBusy = false;
let learningBusy = false;
let diagnosisBusy = false;
let reportLoaded: TrainingReport | null = null;
let csrfToken: string | null = null;
let authMode: "login" | "register" = "login";
let applicationStarted = false;
const CSRF_COOKIE_NAME = "simtrouble_csrf";

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
  renderer.setSize(viewport.clientWidth, viewport.clientHeight, false);
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
    node.textContent = String(index + 1);
    node.title = sourceText(step.label);
    return node;
  }));
}

function updateInterface(): void {
  const step = config.timeline[currentStep];
  byId("step-index").textContent = `${String(currentStep + 1).padStart(2, "0")} / ${String(config.timeline.length).padStart(2, "0")}`;
  byId("step-label").textContent = sourceText(step.label);
  byId("case-state").textContent = uiLabel(step.status);
  byId("learner-phase").textContent = step.status === "FAILURE_OBSERVED" ? "观察异常" : playing ? "播放中" : "准备就绪";
  byId("elapsed-label").textContent = formatTime(totalElapsed);
  playButton.textContent = playing ? "暂停" : currentStep === config.timeline.length - 1 ? "重播" : "播放";
  faultCallout.hidden = step.status !== "FAILURE_OBSERVED";

  const observations = byId<HTMLUListElement>("observations");
  const messages = step.status === "FAILURE_OBSERVED" ? config.public_observations : ["播放动画，观察机械臂、夹爪与工件。"];
  observations.replaceChildren(...messages.map((message) => {
    const item = document.createElement("li");
    item.textContent = sourceText(message);
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

function clearExpiredAuthentication(): void {
  csrfToken = null;
  sessionId = null;
  sessionView = null;
  reportLoaded = null;
  tutorBusy = false;
  learningBusy = false;
  diagnosisBusy = false;
  hypothesisDirty = false;
  expandedEvidence.clear();

  document.cookie = `${CSRF_COOKIE_NAME}=; Max-Age=0; Path=/; SameSite=Lax`;
  signedUser.textContent = "";
  sessionCode.textContent = "尚未创建";
  sessionCode.removeAttribute("title");
  learningProgress.textContent = "尚未获取证据";
  evidenceOptions.replaceChildren();
  hypothesisInput.value = "";
  hypothesisHistory.replaceChildren();
  hypothesisCount.textContent = "0 条记录";
  byId("hypothesis-evidence-summary").replaceChildren();
  diagnosisType.value = "";
  diagnosisReasoning.value = "";
  diagnosisCitations.replaceChildren();
  reportContent.replaceChildren();
  tutorInput.value = "";
  tutorLog.replaceChildren();
  authPassword.value = "";

  appRoot.hidden = true;
  authShell.hidden = false;
  setAuthMode("login");
  authError.textContent = "登录已失效，请重新登录。";
  authError.hidden = false;
  window.location.reload();
}

async function requestJson<T>(url: string, init: RequestInit): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  headers.set("Content-Type", "application/json");
  const method = (init.method ?? "GET").toUpperCase();
  if (csrfToken && method !== "GET" && method !== "HEAD") {
    headers.set("X-CSRF-Token", csrfToken);
  }
  const response = await fetch(url, {
    ...init,
    credentials: "include",
    headers,
  });
  if (!response.ok) {
    let detail = "request_failed";
    try {
      const payload = await response.json() as { detail?: unknown };
      if (typeof payload.detail === "string") detail = payload.detail;
    } catch {
      // Keep the stable fallback when an upstream response is not JSON.
    }
    const error = new ApiError(response.status, detail);
    if (
      response.status === 401
      && detail === "authentication_required"
      && csrfToken !== null
    ) {
      clearExpiredAuthentication();
    }
    throw error;
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
  return messages[error.detail] ?? `操作失败（状态码 ${error.status}），当前学习进度已保留。`;
}

function hasAction(action: TutorAction): boolean {
  return sessionView?.allowed_actions.includes(action) ?? false;
}

function formatEvidenceValue(value: unknown): string { return formatValue(value); }

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
    invalid_evidence_reference: "诊断引用包含未释放的证据，请重新选择。",
    report_not_ready: "训练报告尚未就绪，请稍后重试读取报告。",
    session_not_found: "学习会话已失效，请刷新页面创建新会话。",
  };
  return messages[error.detail] ?? `诊断操作失败（状态码 ${error.status}），当前学习进度已保留。`;
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
    empty.textContent = "尚无已释放证据";
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
    id.textContent = evidenceName(evidence.id, evidence.type);
    type.textContent = "已获取";
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
  diagnosisSubmit.textContent = diagnosisBusy ? "正在提交…" : "提交诊断";
  reportRetry.disabled = diagnosisBusy;

  diagnosisStatus.textContent = reportLoaded !== null
    ? "已评估"
    : submitted
      ? "已提交"
      : canSubmit
        ? "可提交"
        : "未解锁";
  diagnosisStatus.classList.toggle("ready", canSubmit && !submitted);

  diagnosisHint.textContent = reportLoaded !== null
    ? "报告已生成，诊断不可再次提交"
    : submitted
      ? "诊断已提交，等待报告"
      : canSubmit
        ? complete
          ? "提交后不可修改"
          : "需要诊断类型、理由和至少一条证据"
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
      `/api/v0.5/sessions/${encodeURIComponent(sessionId)}/report`,
      { method: "GET" },
    );
    if (report.session_id !== sessionId) {
      throw new Error("Report session mismatch");
    }
    reportLoaded = report;
    renderTrainingReport(reportContent, report);
    clearDiagnosisError();
    setDiagnosisNotice("诊断已完成。以下内容由后端评估与评分管线生成。");
    updateDiagnosisControls();

    try {
      const reviewed = await requestJson<SessionView>(
        `/api/v0.5/sessions/${encodeURIComponent(sessionId)}`,
        { method: "GET" },
      );
      renderSession(reviewed);
    } catch {
      setDiagnosisNotice("报告已生成；公开会话阶段刷新失败，不影响报告结果。");
    }
    showReport();
    return true;
  } catch (error) {
    showDiagnosisError(error);
    reportRetry.hidden = false;
    if (error instanceof ApiError && error.detail === "report_not_ready") {
      reportRetry.hidden = false;
      setDiagnosisNotice("报告尚未就绪。当前会话已保留，可手动重试读取。");
    } else {
      setDiagnosisNotice("报告读取失败。诊断提交状态和当前会话已保留。");
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
  hypothesisSubmit.textContent = canRevise ? "修正假设" : "提交假设";
  hypothesisHint.textContent = canRevise
    ? "可依据新证据修正"
    : canSubmit
      ? "提交初始假设"
      : "等待证据解锁";
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
    title.textContent = evidenceName(option.id, option.type);
    const type = document.createElement("span");
    type.textContent = evidence ? "已获取" : "待获取";
    heading.append(title, type);
    card.append(heading);

    if (evidence) {
      const values = document.createElement("dl");
      values.className = "evidence-values";
      for (const [key, value] of Object.entries(evidence.content)) {
        const term = document.createElement("dt");
        const detail = document.createElement("dd");
        term.textContent = fieldLabel(key);
        detail.textContent = formatEvidenceValue(value);
        values.append(term, detail);
      }
      values.hidden = expandedEvidence.get(option.id) === false;
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
    button.disabled = evidence ? false : !canInspect;
    button.textContent = evidence ? (expandedEvidence.get(option.id) === false ? "展开证据" : "收起证据") : learningBusy ? "正在获取…" : "查看证据";
    if (evidence) button.setAttribute("aria-expanded", String(expandedEvidence.get(option.id) !== false));
    card.append(button);
    return card;
  }));
}

function renderSession(view: SessionView): void {
  sessionView = view;
  sessionId = view.session_id;
  sessionStage.textContent = uiLabel(view.public_stage);
  sessionStage.classList.remove("pending");
  sessionCode.textContent = "当前会话";
  sessionCode.title = view.session_id;
  learningProgress.textContent = `${view.released_evidence.length} / ${view.case_public_state.evidence_options.length} 条证据`;
  hypothesisCount.textContent = `${view.hypotheses.length} 条记录`;
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
  if (!hypothesisDirty) {
    hypothesisInput.value = view.current_hypothesis ?? "";
  }
  syncWorkspace(view, tutorBusy);
  const summary = byId("hypothesis-evidence-summary");
  summary.replaceChildren(...view.released_evidence.map(e => {
    const node = document.createElement("p");
    node.textContent = `${evidenceName(e.id, e.type)}：${formatValue(e.content)}`;
    return node;
  }));
  if (!view.released_evidence.length) summary.textContent = "尚未获取证据";
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
    ? "你"
    : role === "system"
      ? "系统"
      : "智能助教";
  const copy = document.createElement("p");
  copy.textContent = sourceText(message);
  item.append(label, copy);
  if (suggestedAction) {
    const action = document.createElement("small");
    action.textContent = `建议：${uiLabel(suggestedAction, "继续调查")}`;
    item.append(action);
  }
  tutorLog.append(item);
  tutorLog.scrollTop = tutorLog.scrollHeight;
  return item;
}

function setTutorBusy(busy: boolean): void {
  tutorBusy = busy;
  syncWorkspace(sessionView, busy);
  tutorInput.disabled = busy || learningBusy || diagnosisBusy || sessionId === null;
  tutorSubmit.disabled = busy || learningBusy || diagnosisBusy || sessionId === null;
  tutorSubmit.textContent = busy ? "正在思考…" : "发送";
  if (sessionView) {
    renderEvidence();
    updateHypothesisControls();
    updateDiagnosisControls();
  }
}

async function initialiseLearningSession(): Promise<void> {
  try {
    const session = await requestJson<SessionView>("/api/v0.5/sessions", {
      method: "POST",
      body: JSON.stringify({ case_id: config.case_id }),
    });
    renderSession(session);
    tutorStatus.textContent = "可用";
    tutorStatus.classList.remove("pending");
    tutorLog.replaceChildren();
    appendTutorMessage("system", "会话已建立。请先描述观察，再请求诊断提示。");
    setLearningNotice("会话已建立。请请求一条证据开始调查。");
    clearLearningError();
    setTutorBusy(false);
  } catch (error) {
    sessionStage.textContent = "连接失败";
    tutorStatus.textContent = "连接失败";
    showLearningError(error);
    setLearningNotice("未创建新会话。修复连接后刷新页面重试。");
    appendTutorMessage("system", "学习会话连接失败，请检查服务后刷新重试。");
    byId("training-status").textContent = "连接失败";
  }
}

function bindLearning(): void {
  evidenceOptions.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLButtonElement)) return;
    const evidenceId = target.dataset.evidenceId;
    if (evidenceId && sessionView?.released_evidence.some(e => e.id === evidenceId)) {
      expandedEvidence.set(evidenceId, expandedEvidence.get(evidenceId) === false);
      renderEvidence();
      return;
    }
    if (!evidenceId || !sessionId || !hasAction("inspect_evidence") || learningBusy || tutorBusy || diagnosisBusy) return;
    clearLearningError();
    setLearningBusy(true);
    setLearningNotice("正在获取证据…");
    try {
      const response = await requestJson<{ evidence: ReleasedEvidence; session: SessionView }>(
        `/api/v0.5/sessions/${encodeURIComponent(sessionId)}/evidence`,
        { method: "POST", body: JSON.stringify({ evidence_id: evidenceId }) },
      );
      renderSession(response.session);
      setLearningNotice("证据已获取，测量结果已更新。");
    } catch (error) {
      showLearningError(error);
      setLearningNotice("请求未完成；已释放证据和假设均保持不变。");
    } finally {
      setLearningBusy(false);
    }
  });

  hypothesisInput.addEventListener("input", () => { hypothesisDirty = true; updateHypothesisControls(); });
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
        `/api/v0.5/sessions/${encodeURIComponent(sessionId)}/hypotheses`,
        { method: "POST", body: JSON.stringify({ hypothesis }) },
      );
      hypothesisDirty = false;
      renderSession(response);
      setLearningNotice(hasAction("submit_diagnosis") ? "假设已修正，可以进入诊断。" : "初始假设已记录。你可以继续取证，或根据已有证据修正假设。");
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
        `/api/v0.5/sessions/${encodeURIComponent(sessionId)}/diagnosis`,
        { method: "POST", body: JSON.stringify(submission) },
      );
      renderSession(submitted);
      setDiagnosisNotice("诊断已提交，正在读取训练报告…");
    } catch (error) {
      showDiagnosisError(error);
      setDiagnosisNotice("诊断未提交；表单内容、证据和学习进度均已保留。");
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
    tutorStatus.textContent = "正在思考";
    try {
      const response = await requestJson<TutorTurnResponse>(
        `/api/v0.5/sessions/${encodeURIComponent(sessionId)}/tutor`,
        { method: "POST", body: JSON.stringify({ message }) },
      );
      appendTutorMessage(
        "tutor",
        response.tutor.message,
        response.tutor_mode,
        response.tutor.suggested_action,
      );
      renderSession(response.session);
      tutorStatus.textContent = response.tutor_mode === "llm" ? "可用" : "基础引导";
    } catch (error) {
      tutorInput.value = message;
      appendTutorMessage("system", "发送失败，问题已保留，请重新发送。学习进度不变。");
      tutorStatus.textContent = "请重试";
      console.error(error);
    } finally {
      setTutorBusy(false);
      if (byId<HTMLDialogElement>("assistant-dialog").open) tutorInput.focus();
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
  const width = viewport.clientWidth;
  const height = viewport.clientHeight;
  if (!width || !height) return;
  const halfHeight = Math.max(5.6, 7.56 / (width / height));
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

}

async function initialise(): Promise<void> {
  try {
    const response = await fetch("/api/v0.4/cases/ST-001/scene", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`Scene API returned ${response.status}`);
    config = await response.json() as SceneConfig;
    byId("case-code").textContent = config.case_id;
    byId("case-title").textContent = sourceText(config.title);
    byId("task-title").textContent = sourceText(config.title);
    byId("task-copy").textContent = sourceText(config.task);
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
    heading.textContent = "场景加载失败";
    detail.textContent = "请检查服务连接后刷新重试。";
    byId("training-status").textContent = "连接失败";
    loadingState.append(heading, detail);
    console.error(error);
  }
}

function setAuthMode(mode: "login" | "register"): void {
  authMode = mode;
  const registering = mode === "register";
  loginTab.setAttribute("aria-selected", String(!registering));
  registerTab.setAttribute("aria-selected", String(registering));
  displayNameField.hidden = !registering;
  authTitle.textContent = registering ? "创建本地账号" : "欢迎回来";
  authSubtitle.textContent = registering
    ? "注册成功后将自动进入实训"
    : "登录后继续诊断实训";
  authSubmit.textContent = registering ? "注册并登录" : "登录";
  authPassword.autocomplete = registering ? "new-password" : "current-password";
  authPassword.minLength = registering ? 15 : 1;
  authError.hidden = true;
}

function authErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return "身份服务暂时不可用，请稍后重试。";
  const messages: Record<string, string> = {
    invalid_registration: "请使用有效的 3–32 位账号和至少 15 位密码。",
    username_unavailable: "该账号已被注册，请更换账号或直接登录。",
    invalid_credentials: "账号或密码不正确。",
    authentication_required: "登录已失效，请重新登录。",
  };
  return messages[error.detail] ?? "身份验证失败，请重试。";
}

async function enterApplication(auth: AuthSession): Promise<void> {
  csrfToken = auth.csrf_token;
  signedUser.textContent = auth.user.display_name;
  authShell.hidden = true;
  appRoot.hidden = false;
  if (!applicationStarted) {
    applicationStarted = true;
    await initialise();
  }
}

function bindAuthentication(): void {
  loginTab.addEventListener("click", () => setAuthMode("login"));
  registerTab.addEventListener("click", () => setAuthMode("register"));
  authForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    authError.hidden = true;
    authSubmit.disabled = true;
    authSubmit.textContent = authMode === "register" ? "正在注册…" : "正在登录…";
    const url = authMode === "register"
      ? "/api/v0.5/auth/register"
      : "/api/v0.5/auth/login";
    const body = authMode === "register"
      ? {
        username: authUsername.value,
        password: authPassword.value,
        ...(authDisplayName.value === ""
          ? {}
          : { display_name: authDisplayName.value }),
      }
      : { username: authUsername.value, password: authPassword.value };
    try {
      const auth = await requestJson<AuthSession>(url, {
        method: "POST",
        body: JSON.stringify(body),
      });
      authPassword.value = "";
      await enterApplication(auth);
    } catch (error) {
      authError.textContent = authErrorMessage(error);
      authError.hidden = false;
    } finally {
      authSubmit.disabled = false;
      authSubmit.textContent = authMode === "register" ? "注册并登录" : "登录";
    }
  });

  logoutButton.addEventListener("click", async () => {
    if (!csrfToken) return;
    logoutButton.disabled = true;
    try {
      await fetch("/api/v0.5/auth/logout", {
        method: "POST",
        credentials: "include",
        headers: { "X-CSRF-Token": csrfToken },
      });
    } finally {
      csrfToken = null;
      window.location.reload();
    }
  });
}

async function bootstrap(): Promise<void> {
  initialiseWorkspace();
  bindAuthentication();
  setAuthMode("login");
  try {
    const auth = await requestJson<AuthSession>("/api/v0.5/auth/me", { method: "GET" });
    await enterApplication(auth);
  } catch {
    authShell.hidden = false;
    appRoot.hidden = true;
    authUsername.focus();
  }
}

void bootstrap();
