# ST-001 规则引导演示层

此目录是在 GitHub `main` 提交 `836a650385cd3c21a10965458221d4028f0527d3` 基础上新增的本地演示应用。它调用原有 `CaseLoader`、`CaseSession` 和 `EvidenceManager`，展示单案例检查、假设、三轮 Tutor 对话和诊断提交。

## 运行

在仓库根目录执行：

```powershell
python -m pip install -r requirements.txt
python -m demo_app.server
```

打开 <http://127.0.0.1:8000/>。默认端口为 8000，可通过环境变量 `PORT` 修改。Windows 用户也可运行根目录的 `start_demo.ps1`。

## 已实现与边界

- 只包含原仓库的 `ST-001`；证据 ID 为 E01、E02、E03。
- Tutor 输出由 `server.py` 中的显式规则生成，仅使用已开放证据；未调用在线大模型。
- 前端只接收公开案例字段。预设真因只在服务端用于提交后的简化判定。
- 会话存于内存，服务重启后清空；无需账号。这是本地演示，不是公开部署。
- 操作记录是演示层事件列表，尚不是 Phase 3 正式 Trace；未实现五维能力评分、用户管理和物理仿真。

完整原仓库的 29 项回归测试可在仓库根目录运行：

```powershell
python -B -m unittest discover -s tests -p 'test_*.py' -q
```
