# LLM Tutor + DeepSeek 零基础教学手册

> 适用版本：Product v0.4 第一批 Tutor 基础闭环  
> 目标读者：第一次接触后端、API、LLM 的同学  
> 当前范围：教学提示，不做最终评分，不允许模型控制仿真或 Session 状态

## 1. 我们到底在做什么

这个 Tutor 不是“让 AI 随便聊天”，而是一个受程序约束的学习教练。它每一轮只做四件事：

1. 从 Session 取得学员当前能看到的公开信息；
2. 用确定性规则决定教学动作，例如“先检查证据”；
3. 可选地让 DeepSeek 把这个动作写成自然、易懂的中文；
4. 校验模型输出；出错或越界时立即使用规则回复。

最重要的原则：

- Core 和 Session 决定真实状态；
- Policy 决定教学策略；
- DeepSeek 只负责语言表达；
- LLM 不知道标准答案、评分规则和未释放证据；
- LLM 的 suggested_action 只是建议，不能直接执行操作。

## 2. 先认识六个基础概念

### 2.1 API

API 可以理解为两个程序约定好的“窗口”。前端把问题发到后端，后端再把安全上下文发给 DeepSeek。本项目新增的窗口是：

~~~text
POST /api/v0.4/sessions/{session_id}/tutor
~~~

### 2.2 JSON

JSON 是程序之间传数据的文本格式。例如：

~~~json
{"message": "我下一步应该检查什么？"}
~~~

### 2.3 环境变量

环境变量是放配置和密钥的位置。API Key 不能写进 Python 文件，也不能提交到 Git。

### 2.4 Schema

Schema 是 JSON 的“格式说明书”。它规定字段名、类型和允许的取值。DeepSeek 输出即使是合法 JSON，也必须再通过 TutorResponse 的 Pydantic 校验。

### 2.5 async / await

调用 DeepSeek 需要等待网络。async / await 让后端等待时不阻塞其他请求。初学阶段把它理解成“可以暂停并等待网络结果”即可。

### 2.6 fallback

fallback 是备用方案。网络超时、余额不足、限流、服务故障、返回格式错误或输出越权时，系统都会切回 RuleTutor，主学习流程不会中断。

## 3. 一次 Tutor 请求怎样流动

~~~text
浏览器
  │ 学员问题
  ▼
FastAPI /tutor
  ▼
TutorContextProjector ── 只复制公开 SessionView
  ▼
TutorPolicy ── 决定 intent、hint_level、suggested_action
  ├── 没开 LLM ──────────────┐
  └── DeepSeek /responses → 输出校验
                              │
                    合法 ─────┤
                    异常 ─→ RuleTutor
                              ▼
                TutorResponse + SessionView
~~~

DeepSeek 官方说明 Responses API 是无状态的：服务端不替我们保存对话，所以本项目用 TutorConversationStore 按 session_id 保存最近 12 条消息，并在下一轮一起发送。

## 4. 本批代码文件分别负责什么

### apps/training_api/tutor/settings.py

从环境变量读取 DeepSeek 配置。默认关闭 LLM，所以没有 Key 也能运行。

| 环境变量 | 默认值 | 作用 |
|---|---:|---|
| SIMTROUBLE_LLM_ENABLED | false | 是否启用真实 LLM |
| DEEPSEEK_API_KEY | 无 | DeepSeek 密钥 |
| DEEPSEEK_BASE_URL | https://api.deepseek.com | API 地址 |
| DEEPSEEK_MODEL | deepseek-flash | 模型名 |
| DEEPSEEK_TIMEOUT_SECONDS | 8 | 单次网络超时 |
| DEEPSEEK_MAX_RETRIES | 1 | 瞬时故障重试次数 |

api_key 字段设置了 repr=False，避免调试打印配置时泄漏密钥。

### apps/training_api/tutor/ports.py

定义 TutorProvider 协议。业务层只知道“供应商能生成 TutorResponse”，不知道供应商一定是 DeepSeek。以后更换模型时，不需要修改 Policy 和 Session。

### apps/training_api/tutor/context.py

把 SessionView 投影成 TutorRequest。它只包含 Case 公开状态、已释放证据、当前 Session 的对话、学员假设和当前允许动作。

它不读取 authoritative_case，因此不会把 fault、ground_truth、optimal_path、scoring_rules、information_value 或 related_faults 发给模型。

### apps/training_api/tutor/policy.py

这是 Tutor 的“大脑规则”：

- 没有证据：建议 inspect_evidence；
- 有证据但没有假设：建议 submit_hypothesis；
- 证据不足：提示再找一条有区分力的证据；
- 有新证据：建议 revise_hypothesis；
- 条件成熟：提醒引用证据后 submit_diagnosis。

Policy 同时固定 intent、hint_level 和 suggested_action。模型不能提高提示等级，也不能把下一步改成程序未允许的动作。

### apps/training_api/tutor/deepseek.py

这是 DeepSeek 适配器，使用项目已有的 httpx，不额外安装 SDK。它向以下地址发送 POST 请求：

~~~text
https://api.deepseek.com/responses
~~~

关键请求内容：

~~~json
{
  "model": "deepseek-flash",
  "reasoning": {"effort": "none"},
  "stream": false,
  "text": {
    "format": {
      "type": "json_schema",
      "name": "tutor_response_v04",
      "schema": "由 TutorResponse 自动生成"
    }
  }
}
~~~

第一批关闭 reasoning，因为教学动作已由 Policy 决定，无需模型再次推理真实故障；这样能降低延迟、Token 消耗和越界猜答案的机会。

第一批不做流式输出，因为 Product v0.4 冻结契约把 streaming 放在范围外；完整 JSON 到达后才能做 Schema 与安全校验，也更容易调试。

### apps/training_api/tutor/validation.py

模型返回后会检查：

1. contract_version 必须是 0.4.0；
2. intent 必须与 Policy 一致；
3. hint_level 必须与 Policy 一致；
4. suggested_action 必须与 Policy 一致且属于 allowed_actions；
5. 文本不能出现私有字段标记。

任何一项失败都会触发规则回退。

### apps/training_api/tutor/fallback.py

提供不依赖网络的中文回复。它保证演示、测试和比赛现场在 DeepSeek 不可用时仍能继续。

### apps/training_api/tutor/service.py

这是总编排器：取 Session、建上下文、跑 Policy、调用供应商、校验、回退、保存对话，最后返回 TutorTurnResponse。

### apps/training_api/main.py

暴露 HTTP 路由。请求格式：

~~~json
{"message": "我该从哪条证据开始？"}
~~~

响应核心格式：

~~~json
{
  "tutor": {
    "contract_version": "0.4.0",
    "intent": "question",
    "message": "……",
    "hint_level": 0,
    "suggested_action": "inspect_evidence"
  },
  "session": {},
  "tutor_mode": "llm"
}
~~~

tutor_mode 为 rule_fallback 时，说明本轮使用了确定性规则回复。

## 5. 第一次在本机运行

以下命令均在仓库根目录的 PowerShell 执行。

### 5.1 安装依赖

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
~~~

### 5.2 先不开 DeepSeek

不设置任何密钥，直接启动：

~~~powershell
.\.venv\Scripts\python.exe -B -m apps.training_api
~~~

此时 Tutor 正常工作，但 tutor_mode 是 rule_fallback。

### 5.3 开启 DeepSeek

先到 DeepSeek 平台创建 API Key。只把 Key 放进当前 PowerShell 进程：

~~~powershell
$env:SIMTROUBLE_LLM_ENABLED = "true"
$env:DEEPSEEK_API_KEY = "替换成你自己的Key"
$env:DEEPSEEK_MODEL = "deepseek-flash"
.\.venv\Scripts\python.exe -B -m apps.training_api
~~~

关闭这个 PowerShell 窗口后，临时环境变量会消失。

严禁把真实 Key 写入代码、教学截图或 Git，也不要在日志中打印 Authorization 请求头。

## 6. 手动调用 API

先创建 Session：

~~~powershell
$session = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v0.4/sessions" -ContentType "application/json" -Body '{"case_id":"ST-001"}'
$session.session_id
~~~

再询问 Tutor：

~~~powershell
$body = @{ message = "我下一步应该做什么？" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v0.4/sessions/$($session.session_id)/tutor" -ContentType "application/json" -Body $body
~~~

刚创建的 Session 没有已释放证据，因此正确结果应建议 inspect_evidence，而不是直接公布故障答案。

## 7. 怎样运行测试

真实供应商 smoke（不会打印 API Key、原始提示词或模型正文）：

~~~powershell
$env:SIMTROUBLE_LLM_ENABLED = "true"
$env:DEEPSEEK_API_KEY = "替换成你自己的Key"
.\.venv\Scripts\python.exe -B tools/deepseek_tutor_smoke.py
~~~

脚本只有在返回 `tutor_mode=llm`、结构化响应通过程序校验时才会打印
`PASS`；如果触发规则回退，会仅显示脱敏后的原因代码。

运行全部 Python 测试：

~~~powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_*.py" -v
~~~

只运行 Tutor 第一批测试：

~~~powershell
.\.venv\Scripts\python.exe -B -m unittest tests.v0_4.test_tutor_policy tests.v0_4.test_tutor_service tests.v0_4.test_deepseek_adapter tests.v0_4.test_session_api -v
~~~

测试使用 httpx.MockTransport 模拟 DeepSeek，不消耗余额、不需要联网，也不会读取真实 API Key。

测试覆盖：

- Policy 随学习进度改变建议；
- 两个 Session 的对话不会串线；
- 上下文不含私有字段；
- DeepSeek 请求使用 json_schema；
- 503 会有限重试，401 不会盲目重试；
- 无效 JSON/契约会被拒绝；
- 越权动作会自动回退；
- Tutor HTTP 路由和错误码稳定。

## 8. 常见错误怎么排查

| 现象/状态码 | 常见原因 | 处理方式 |
|---|---|---|
| tutor_mode 一直是 rule_fallback | LLM 未启用或没有 Key | 检查两个环境变量 |
| 400 | 请求格式不符合 API | 检查模型名和请求字段 |
| 401 | Key 错误 | 重新复制 Key，检查多余空格 |
| 402 | 余额不足 | 到平台检查余额 |
| 422 | 参数不合法 | 检查消息非空、字段名正确 |
| 429 | 请求过快 | 稍后重试；当前代码最多重试一次 |
| 500/503 | 服务端故障或过载 | 系统自动回退，稍后再试 |
| 返回不是 Tutor JSON | 模型输出异常 | Pydantic 拒绝并走规则回退 |
| 看见最终答案或私有字段名 | 安全边界疑似失效 | 立即停用真实 LLM 并补回归测试 |

不要把完整供应商响应和请求上下文直接返回给浏览器。当前实现只记录异常类型，不记录 API Key、原始 Prompt 或供应商错误正文。

## 9. 为什么暂时不用 LangGraph

第一批只有一条清晰链路：

~~~text
project context → decide policy → call provider → validate → fallback
~~~

普通 Python 服务最容易读、测和排错。只有后续出现真正的多节点分支、工具调用或可恢复工作流时，才评估引入 LangGraph。不要为了“看起来像 AI 项目”提前增加复杂度。

## 10. 给初学者的练习

1. 在 RuleTutor 中修改一条回复，运行对应测试；
2. 给 TutorPolicy 新增一个不会泄露答案的规则，并先写测试；
3. 把 DEEPSEEK_MAX_RETRIES 改成 0，观察 503 测试应怎样变化；
4. 构造一个 suggested_action 越权响应，确认 tutor_mode 变成 rule_fallback；
5. 新建两个 Session 连续对话，确认历史不会互相出现。

## 11. 第一批之后还要做什么

1. 前端 Tutor 面板接入真实 /tutor 路由；
2. 在 Trace 中记录 Tutor 请求、交付和回退事件，但不存原始 Prompt；
3. 增加同一 Session 并发请求串行化；
4. 增加调用耗时、fallback 原因、Token 用量等脱敏指标；
5. 用真实 DeepSeek Key 做人工 smoke test；
6. 完成 diagnosis、Evaluator 与确定性五维评分，不让 LLM 直接给最终分数。

## 12. 官方参考

- DeepSeek 首次 API 调用与当前模型名：https://api-docs.deepseek.com/
- DeepSeek Responses API：https://api-docs.deepseek.com/api/create-response/
- DeepSeek 错误码：https://api-docs.deepseek.com/quick_start/error_codes/

官方文档说明当前 OpenAI-compatible base URL 是 https://api.deepseek.com，Responses API 支持 json_schema，并且多轮对话需要客户端每次携带完整历史。本项目按这些约束实现。
