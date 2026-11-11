# 贡献指南

## 添加技能

1. 先写 2–3 个真实使用例，明确什么请求应触发、什么请求不应触发。
2. 创建 `skills/<verb-led-name>/SKILL.md`，目录名与 `name` 一致。
3. description 同时说明“做什么”和“何时使用”，不要只写抽象能力。
4. 只添加会被使用的 `references/`、`scripts/` 或 `assets/`。
5. 在 `README.md` 技能表与 `observatory.json` 中登记。
6. 运行完整验证并打包；脚本行为必须有离线测试。

## 修改技能

- 优先改进触发准确性、决策分支和验收方式，不堆砌通识。
- 保留已验证的工作流；行为变化需要更新对应示例或测试。
- 不用宽泛的“更智能”“全自动”替代具体输入、步骤与产物。
- 修复缺陷时，先添加能复现原问题的测试，再改实现。

## 添加 Prompt

在 `prompts/<slug>.md` 中填写 `name`、`description`、`category`、`tags`、`version`、`author` frontmatter。Prompt 应是独立、短小的任务入口；需要多步资源或脚本时优先做成 Skill。

## 验证

```bash
python scripts/validate_repo.py
python -m unittest discover -s tests -v
python scripts/package_skills.py
```

验证必须离线完成。不要通过删除断言、跳过失败用例或降低阈值来制造通过结果；确有环境依赖时，应明确报告未运行项。

## 提交建议

使用小而完整的变更，例如 `feat: add multimodal evaluation skill`、`fix: preserve stale snapshot status`。提交信息是建议，不要求仓库历史采用特定风格。
