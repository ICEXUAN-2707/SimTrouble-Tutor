# v0.5 单服务器发布

候选基线：develop c45dcb5。发布准备改动尚未提交，不能仅部署该 SHA 就获得本目录能力。
独立工作区不含原工作区的未提交文件及账号数据库。Python 使用 3.12，Node CI 使用 22；
前端 npm ci 使用已有 package-lock.json，Python 使用 requirements-release.txt 的完整固定版本。
锁文件是版本锁定，不是制品哈希验证或漏洞扫描；上线前须经 Linux CI 再验。

## 主机准备与安装

以下为管理员审核后执行的模板，不自动更改服务器。要求 Linux、systemd、Nginx、Python 3.12、
Node 22 构建工具和有效 TLS 证书；创建无登录权限的 simtrouble 服务用户。
创建 /opt/simtrouble/releases、/var/lib/simtrouble、/etc/simtrouble；数据库目录属于服务用户，权限 0700。
版本目录为 root 所有、服务只读，静态资源需 Nginx 可读；不要复制本机 venv 或 node_modules。

在每个不可变版本目录（示例 /opt/simtrouble/releases/<release>）执行：

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-release.txt
.venv/bin/python -m pip check
npm ci --prefix apps/training_web
npm run build --prefix apps/training_web
.venv/bin/python -B -m unittest discover -s tests -p 'test_*.py'
```

执行测试时使用隔离 SIMTROUBLE_AUTH_DB_PATH，禁止指向正式数据库。
保存代码 SHA、requirements-release.txt、package-lock.json 与 dist 文件的校验和。
将 current 链接指向候选目录；维护窗口内切换，禁止双实例/多 worker，活动训练保存在内存。
服务使用的数据库必须位于 /var/lib/simtrouble/auth.db，不随代码回滚删除。

把 api.env.example 复制到 /etc/simtrouble/api.env（root:simtrouble，0640），
只在服务器填密钥。先保持 LLM 关闭，完成启动检查后显式验证真实 Provider。
将 simtrouble.service 安装到 /etc/systemd/system；检查配置后 daemon-reload 并启动服务。
将 nginx.conf 的所有 tutor.example.com 和证书路径替换为真实值；nginx -t 成功后才 reload。
仅开放 443、用于重定向的 80 与受限 SSH，8001 不对公网开放。
HTTPS 同源使用 /api，代理不重写路径；生产不运行 Vite Preview。

## 本地一致性备份与恢复

工具只接受 schema 3；使用 SQLite Backup API，支持 WAL 已提交事务；快照验证完整性、
外键、版本、行数和 SHA-256。输出目录必须不存在，父目录必须存在且权限受限。
失败目录没有有效 manifest 不得当作成功备份，保留排查，不自动覆盖或清理。

```sh
umask 077
/opt/simtrouble/current/.venv/bin/python tools/sqlite_backup.py backup \
  --source /var/lib/simtrouble/auth.db \
  --directory /secure-backups/<unique-backup-id> --revision <code-sha>
/opt/simtrouble/current/.venv/bin/python tools/sqlite_backup.py verify \
  --directory /secure-backups/<unique-backup-id>
/opt/simtrouble/current/.venv/bin/python tools/sqlite_backup.py restore \
  --directory /secure-backups/<unique-backup-id> \
  --destination /isolated-recovery/restored.db
```

命令从版本目录执行；备份账户需要读取数据库及 SQLite sidecar 的权限。
恢复只写入新路径，拒绝覆盖数据库及现有 sidecar；默认撤销所有恢复的认证会话，要求重新登录。
验证报告、登录与隔离后，才可停服并由管理员用恢复文件替换正式数据库；确认所有进程已停止，
保留故障数据库及其 sidecar，处理旧 sidecar 后再启动，禁止直接覆盖仍运行的数据库。

工具生成的是**本机明文备份**，不包含加密/上传功能。Linux 文件 0600、目录 0700；
Windows 权限需要 ACL 管理，不能把 POSIX mode 当作 Windows 保护。
上线前接入受控调度：每小时一次、发布前一次；用组织认可工具加密后上传异机，
校验上传和解密恢复成功后才清理本地副本。密钥分离管理，未完成前不满足异机备份门禁。
保留策略：24 小时点、7 日点、4 周点；失败告警，每月恢复演练。
manifest 的哈希检测意外损坏，不抵御攻击者同时篡改文件与 manifest，需受信存储或签名保护。

## 发布和回滚

1. 维护窗口停止新训练/写入，等待现有训练结束；明确重启不能恢复未完成训练。
2. 停止 API，强制备份并验证；记录旧代码路径、配置版本、schema 与备份 ID。
3. 审核迁移兼容性，切换 current 并启动。检查 /healthz 返回 version 0.5.0，
   HTTPS 登录、CSRF、训练、报告和用户隔离通过后才开放。
4. 若失败，停止 API 并保留故障现场；仅在旧代码兼容当前 schema 时单独回退代码。
   不兼容则恢复匹配的数据库与代码；恢复后的账号/报告回退到备份时刻，先确认数据损失。
5. 当前工具只支持 v0.5 schema 3，未来迁移必须带上对应旧版恢复工具与兼容说明，
   不执行未知逆向 SQL。重新验证健康、登录、报告和隔离后才开放。

服务器地址、域名、证书、异机存储与维护授权尚未提供；这里的配置没有在 Linux 主机安装或验证。
