# 前端首屏模块拆分计划

## 目标

在不改变 `/api/v0.4` 契约、学习状态机和三维交互行为的前提下，让页面骨架、任务区和连接状态先于 Three.js 场景运行时完成加载与渲染。

## 当前基线

整合前的生产构建只有一个 JavaScript 主包：

| 产物 | 原始大小 | Gzip |
| --- | ---: | ---: |
| `index` | 585.11 KB | 149.36 KB |

本分支已经完成低风险的依赖分组：

| 产物 | 原始大小 | Gzip | 用途 |
| --- | ---: | ---: | --- |
| `index` | 26.44 KB | 10.22 KB | 页面状态机、API 与业务交互 |
| `three-runtime` | 558.64 KB | 138.69 KB | Three.js 与轨道控制器 |

这一步建立了稳定缓存边界，业务代码更新时浏览器无需重复下载 Three.js。但是当前 HTML 仍会预加载 `three-runtime`，因此总首屏传输量尚未显著下降，不能把它视为真正的延迟加载。

## 目标架构

```text
index.html
  └─ bootstrap.ts                 <= 15 KB gzip
      ├─ workspace-controller.ts
      ├─ learning-client.ts       会话、证据、假设、诊断、助教
      ├─ scene API                先获取轻量场景配置
      ├─ import(scene-runtime.ts)  视口可见或浏览器空闲时加载
      │   └─ Three.js + OrbitControls
      └─ import(report-view.ts)    仅在报告就绪后加载
```

## 分阶段实施

### 阶段一：拆出三维场景运行时

新增 `src/scene-runtime.ts`，迁移以下职责：

- Three.js 和 `OrbitControls` 导入。
- 场景、相机、灯光、机械臂和工件创建。
- 动画插值、播放、暂停、跳步和复位。
- 视口缩放、网格、坐标轴和相机适配。
- `__SIMTROUBLE_INSPECT__` 测试探针。

对外只暴露一个小接口：

```ts
export interface SceneRuntime {
  play(): void;
  pause(): void;
  reset(): void;
  skip(): void;
  fit(): void;
  dispose(): void;
}

export async function createSceneRuntime(options: SceneRuntimeOptions): Promise<SceneRuntime>;
```

`main.ts` 只保留业务状态和 DOM 协调。先渲染页面骨架并请求场景 JSON；场景容器进入视口或浏览器空闲时，再通过动态 `import()` 加载运行时。设置最长 1 秒兜底，避免桌面端出现长期空场景。

### 阶段二：按需加载报告模块

把 `report-renderer.ts` 改为仅在诊断完成、报告响应成功后动态导入。报告不属于首次训练页面的关键路径，不应进入初始业务包。

### 阶段三：建立构建体积门禁

增加产物预算检查：

- 初始业务入口不超过 40 KB，Gzip 不超过 15 KB。
- 初始 HTML 不得出现 `three-runtime` 的 `modulepreload`。
- Three.js 必须保持独立异步块，避免重新合并进业务入口。
- 页面骨架在 Three.js 请求完成前可见且可读取连接状态。
- 390、768、1280 和 1440 像素视口的现有流程测试全部保留。

建议新增 `npm run test:bundle`，解析 `dist/.vite/manifest.json` 和构建产物，超过预算直接失败。

## 性能验收

在无缓存与已缓存两种状态下，使用相同机器、相同浏览器和模拟慢速 4G 各执行五次，记录中位数：

- 首次内容绘制时间。
- 最大内容绘制时间。
- 首屏 JavaScript 传输量。
- Three.js 请求开始时间。
- 场景首次可交互时间。

阶段一的验收目标：页面骨架无需等待 Three.js 下载；初始关键 JavaScript Gzip 不超过 15 KB；场景可交互时间相较当前基线不回退超过 10%。

## 风险控制

- 动态导入失败时保留中文错误状态和重试入口，不创建伪造场景。
- `dispose()` 必须释放渲染器、几何体、材质、事件监听和动画帧，防止热更新或页面返回造成 GPU 内存泄漏。
- API 请求与 Three.js 加载可并行，但学习会话初始化不能依赖三维模块。
- 每个拆分阶段单独提交；任一阶段出现交互回归时可以独立回滚，不回退本次 UI 产品化整合。
