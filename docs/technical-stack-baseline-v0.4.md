# Product v0.4 技术栈正式基线

> 状态：**FROZEN / 正式基线**
> 生效日期：2026-10-22
> 适用产品：SimTrouble Tutor Product v0.4
> 产品代码基准：`task/product-v0.4-ui-productization@3221401`
> 冻结依据：本机全量 Python 回归与前端生产构建通过

## 1. 基线用途

本文件是 Product v0.4 当前开发、联调和验收环境的精确版本基线。团队成员在复现问题、执行验收或提交集成 PR 时，应优先与本文件对齐。

本基线冻结的是当前实际实现，不代表早期目标架构中的所有组件均已引入。任何版本升级、框架替换或新增基础设施，都必须通过独立 PR 更新本文件并附带完整验证结果。

## 2. 产品与代码基准

| 项目 | 正式基线 |
|---|---|
| 产品版本 | `0.4.0` |
| API 版本 | `v0.4` |
| 基准分支 | `task/product-v0.4-ui-productization` |
| 产品代码提交 | `3221401` |
| Python 测试 | `129/129` 通过 |
| 前端检查 | TypeScript strict check 通过 |
| 前端构建 | Vite production build 通过 |

## 3. 本机验证环境

| 组件 | 正式基线版本 |
|---|---:|
| 操作系统验证环境 | Microsoft Windows `10.0.26200.9711` |
| Python | `3.12.10` |
| pip | `25.0.1` |
| Node.js | `24.13.0` |
| npm | `11.6.2` |
| Git | `2.52.0.windows.1` |

Windows 构建号用于记录本次验证环境，不作为应用运行的唯一操作系统限制。Python、Node.js、npm 版本是开发环境对齐基准。

## 4. 后端直接依赖

| 组件 | 正式基线版本 | 用途 |
|---|---:|---|
| FastAPI | `0.143.1` | Product v0.4 HTTP API |
| Pydantic | `2.13.5` | 领域模型、输入输出与契约校验 |
| Uvicorn | `0.51.0` | ASGI 本地运行服务 |
| HTTPX | `0.28.1` | LLM Provider HTTP 调用与 API 测试 |
| JSONSchema | `4.26.0` | JSON Schema 合约验证 |

### 4.1 已验证的关键传递依赖

```text
annotated-doc==0.0.4
annotated-types==0.7.0
anyio==4.14.0
attrs==26.1.0
certifi==2026.5.20
click==8.4.2
h11==0.16.0
httpcore==1.0.9
idna==3.18
jsonschema-specifications==2025.9.1
opentelemetry-api==1.45.1
pydantic-core==2.46.5
referencing==0.37.0
rpds-py==2026.6.3
starlette==1.3.1
typing-extensions==4.15.0
typing-inspection==0.4.2
```

测试框架使用 Python 3.12.10 标准库 `unittest`，当前未引入 Pytest。

## 5. 前端与三维展示依赖

| 组件 | 正式基线版本 | 用途 |
|---|---:|---|
| TypeScript | `7.0.2` | 前端业务实现与严格类型检查 |
| Vite | `8.3.4` | 开发服务与生产构建 |
| Three.js | `0.186.1` | CAD 风格三维场景与动画 |
| `@types/three` | `0.186.0` | Three.js 类型定义 |
| Playwright | `1.64.0` | 浏览器 E2E 与 UI 验证 |
| Playwright Core | `1.64.0` | 浏览器自动化运行时 |
| Chromium | `156.0.8078.4`，revision `1248` | 正式浏览器测试基线 |
| Rolldown | `1.2.13` | Vite 间接构建依赖 |

TypeScript 编译目标固定为 `ES2022`，模块格式为 `ESNext`，启用 `strict`、`noUnusedLocals` 和 `noUnusedParameters`。

当前前端采用原生 HTML/CSS、TypeScript、Vite 和 Three.js。Product v0.4 **未使用** React、Next.js、Vue 或 Tailwind CSS。

## 6. AI 与 Tutor 实现基线

当前 Tutor 不依赖 OpenAI SDK、DeepSeek SDK、LangChain 或 LangGraph。正式实现为：

```text
自建 Provider Registry
  -> HTTPX 0.28.1
  -> Responses / Chat Completions 兼容 HTTP 接口
  -> Pydantic 2.13.5 结构化校验
  -> Tutor Output Guard
  -> 确定性规则回退
```

Provider 模型名称属于可配置的远程服务标识，不视为本地软件依赖版本。API Key 只允许通过服务端环境变量提供。

## 7. 数据存储基线

Product v0.4 当前没有数据库依赖，不包含 SQLite、PostgreSQL、SQLAlchemy、Redis 或数据库迁移工具。

- Case、Scene、Device、Module：版本库 JSON 文件；
- Session、Trace、Tutor 对话、诊断报告：Python 进程内存；
- LLM 配置与密钥：服务端环境变量；
- 前端交互状态：浏览器运行内存。

持久化和登录认证必须在后续独立 Spec 中设计，不得通过未审查依赖直接加入本基线。

## 8. 已执行验证

### Python 回归

```powershell
python -B -m unittest discover -s tests -p "test_*.py" -v
```

结果：`Ran 129 tests`，`OK`。

### 前端严格检查与生产构建

```powershell
cd apps/training_web
npm run build
```

结果：TypeScript 检查通过，Vite `8.3.4` 构建通过。当前保留一个非阻塞警告：`three-runtime` 压缩前约 `558.64 kB`，超过默认 `500 kB` 提示阈值。

## 9. 对齐规则

1. 前端依赖必须使用 `npm ci`，不得使用会改写锁文件的方式作为验收环境安装命令。
2. Python 验收环境必须与第 3、4 节版本一致；当前 `requirements.txt` 中的版本范围不能单独证明环境已经对齐。
3. 提交前至少执行第 8 节两项验证。
4. 版本升级必须在独立 PR 中同时更新依赖清单、锁定材料、本文件和验证结果。
5. 未更新本文件的本机新版本，不自动成为新的正式基线。

## 10. 当前自动化差距

本文件已经完成“版本口径冻结”，但仓库尚未完成全部机械约束：

- CI 当前使用浮动的 Python `3.12`，没有锁定到 `3.12.10`；
- CI 当前使用 Node.js `22`，与本机正式基线 `24.13.0` 不一致；
- CI 的 npm 版本没有精确锁定；
- `requirements.txt` 除 Pydantic 外仍使用版本范围；
- Python 尚无独立 lock/constraints 文件；
- CI 使用 `ubuntu-latest`，操作系统镜像会随时间变化。

在完成上述自动化锁定前，本文件是人工对齐和验收的唯一精确版本依据。
