# v0.5 发布准备与 SQLite 恢复演练

## 基线及改动

- 独立 detached 工作区：`.tmp/v05-release-preparation`，基于 `origin/develop@c45dcb5`。
- 原工作区改动、根账号数据库保持不变；没有创建分支、提交或推送。
- Python 3.12.10，新建独立 venv；22 个直接及传递依赖全部固定版本，pip check 通过。
- 前端使用既有 package-lock.json 与 npm ci。本机 Node 24.13.0、npm 11.6.2；
  Linux CI 仍为 Node 22，不能把本地结果等同于 Linux CI 结果。
- Product CI 改为安装 requirements-release.txt，后续 PR 需验证 Linux 结果。
- 新增 systemd 单 worker 服务、Nginx HTTPS 同源静态/代理模板和后端环境配置示例。
- 新增 SQLite backup/verify/restore CLI 与六项新增专项测试。

## 锁文件校验和（SHA-256）

- requirements-release.txt：AA67E1AC704D7B6DA82EC077D010ECE32419666801B6F6AD403FD709C310DF80
- apps/training_web/package-lock.json：F59694600FE46612E3E0BAF4A6E47FE1CAB71D07AC856C03DD563E37C7D6A7A2

## SQLite 演练

隔离临时数据库，使用项目真实账号/诊断/报告逻辑，不使用生产数据。

1. WAL 连接保持打开，备份已提交用户数据，校验并恢复，行数一致。
2. 创建测试账号，完成 ST-001 训练并保存报告；快照包含一条完成记录。
3. 在新路径恢复数据库并创建全新应用，原认证 Cookie 无效，必须重新登录。
4. 重新登录后读取原 Session ID 的报告，与备份前 JSON 一致。
5. 另一账号读取该报告返回 404；恢复后的 auth_sessions 初始为空。
6. 损坏快照、修改 manifest、未知 schema、缺失源文件、覆盖现有路径和 sidecar 均被拒绝。

六项专项测试通过；日志在工作区忽略目录 var/backup-tests.log。
测试数据库由临时目录自动清理，不保留含测试凭据的快照。
初次测试发现 Windows 只读句柄 fsync 不兼容，改用可写句柄后通过。

## 验证与剩余门禁

- 独立环境 pip check：通过。
- TypeScript/Vite 生产构建：通过，保留既有 Three.js >500 kB 警告。
- npm audit：0 漏洞。未执行 Python 安全漏洞扫描，不把 pip check 当作漏洞审计。
- 最终全量后端与生产浏览器测试结果见下方完成记录。
- Linux systemd/Nginx 配置是待主机参数替换的模板，未在服务器安装或执行 nginx -t。
- 工具完成本机一致性备份及恢复；加密、异机上传、自动调度/保留和监控仍须接入服务器。
- 不声称 RPO/RTO 达标，不声称生产运行环境验收通过，不包含真实 Provider 新调用。

安装、演练与回滚指引：deploy/README.md。

## 最终完成记录

- 最终 Python 全量回归：176 项，67.784 秒，退出码 0；
  包含原 170 项及六项新增备份/恢复测试，无重复继承测试计数。
- 独立 venv + 真实 FastAPI + 生产 Preview + 无头 Edge 浏览器：退出码 0。
  覆盖注册/退出/登录/身份恢复/撤销、训练与报告、第 4 步解锁、
  受控 Tutor 成功与超时/非法/泄漏回退，以及桌面/平板/手机。
- 本轮服务结束后已自动停止。没有真实 Provider 请求或线上部署。
- 完整日志：var/release-final-regression.log、var/release-browser.log；均为本机忽略文件。
