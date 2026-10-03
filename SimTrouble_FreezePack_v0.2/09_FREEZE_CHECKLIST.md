# Development Freeze Checklist

Phase 0 结束后，开发前必须完成：

## Product
- [ ] V0 场景冻结
- [ ] 4 类异常冻结
- [ ] V0 页面冻结
- [ ] Out of Scope 冻结

## Architecture
- [ ] 技术栈冻结
- [ ] 分层架构冻结
- [ ] Simulation Adapter 冻结
- [ ] Tutor Contract 冻结

## Data Contracts
- [ ] Case Schema
- [ ] Session Schema
- [ ] Skill Schema
- [ ] API Contract
- [ ] ST-001

## Git
- [ ] main protected
- [ ] develop created
- [ ] PR template
- [ ] CODEOWNERS
- [ ] GitHub Actions baseline
- [ ] branch naming rules

## Team
- [ ] A/B/C role confirmed
- [ ] Review ownership confirmed
- [ ] weekly sync confirmed

全部完成后：
```text
tag: spec-v0.2-freeze
```

此后核心需求只能通过正式 Change Proposal 修改。
