# Review / QA / Release Gate

## 1. Feature Gate
进入 develop 前：
- 单元测试通过
- Contract 未破坏
- Out of Scope 未越界
- Reviewer 通过

## 2. Integration Gate
测试：
- Case 加载
- Evidence 查询
- Hypothesis 更新
- State transition
- Trace 保存
- Skill 计算
- Tutor 不剧透
- UI 状态同步

## 3. Release Gate
进入 release 前：
- 8–12 Case 可运行
- 无阻断级 bug
- Demo 稳定
- Agent fallback 可用
- 页面可用
- 数据库初始化稳定

## 4. Main Gate
合 main 前：
- A 技术验收
- B 集成验收
- C 产品验收
- Demo 3–5 分钟可完成
- 答辩脚本与产品一致
- 截图/录屏完成
- main build 可重现

## 5. Demo Checklist
1. Dashboard
2. 进入训练
3. Case 初始状态
4. 用户查 Evidence
5. 提出 Hypothesis
6. Tutor 追问 / Hint
7. 用户修改判断
8. 提交 Diagnosis
9. Skill Report
10. 推荐下一 Case
