import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
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
    updateInterface();
    loadingState.hidden = true;
    new ResizeObserver(resizeViewport).observe(viewport);
    requestAnimationFrame(animate);
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
