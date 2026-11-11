# islinxu-skills

林旭的可复用 Agent Skills 与 Prompt 集合，聚焦多模态研究、模型评测、计算机视觉实验、Agent 工程与可观测性。

本仓库把公开工作中反复使用的方法沉淀为可执行流程，而不是泛化的人格提示词。核心原则是：**证据先于结论、口径先于数字、验证先于交付、失败不得伪装成成功。**

## 技能目录

| 技能 | 用途 | 典型触发 |
| --- | --- | --- |
| [`agent-workflow`](skills/agent-workflow/SKILL.md) | 长程任务的目标、方案、专项、验证与文档承接 | 自动驾驶、复杂调试、长程协作 |
| [`code-audit`](skills/code-audit/SKILL.md) | 修改前按调用链审计实验代码并构造最小反例 | 代码审计、数值缺陷、实验排障 |
| [`surgical-coding`](skills/surgical-coding/SKILL.md) | 以清晰假设、最小实现和精准差异完成编码 | 写代码、修复、重构、代码审查 |
| [`paper-deep-read`](skills/paper-deep-read/SKILL.md) | 将论文拆成问题、方法、实验与复现清单 | 论文精读、方法复现、实验核对 |
| [`paper-curation`](skills/paper-curation/SKILL.md) | 论文条目的身份归一、去重、来源与增删台账 | paper-list、综述清单、每日更新 |
| [`multimodal-eval`](skills/multimodal-eval/SKILL.md) | 建立同口径、多切片、可复核的多模态评测 | MLLM、VLM、Benchmark、回归评测 |
| [`yolo-experiment`](skills/yolo-experiment/SKILL.md) | YOLO 训练、消融、导出与部署实验的回归门 | YOLO、检测、MoE、TensorRT |
| [`observability-pipeline`](skills/observability-pipeline/SKILL.md) | 构建有快照口径、失败状态和离线回归门的看板 | 模型观测、下载趋势、静态看板 |

## Prompt 目录

- [`code-review`](prompts/code-review.md)：只报告能定位、能证实的审查意见。
- [`deep-research`](prompts/deep-research.md)：多轮检索、交叉验证与不确定项声明。
- [`experiment-design`](prompts/experiment-design.md)：训练开跑前检查可证伪性、变量、基线、预算与评测。
- [`bug-postmortem`](prompts/bug-postmortem.md)：修复后沉淀根因、检查缺口与防复发改动。

## 快速开始

```bash
git clone https://github.com/isLinXu/islinxu-skills.git
cd islinxu-skills

# 零第三方依赖的结构校验、同步检查、测试与打包
python scripts/validate_repo.py
python scripts/sync_guides.py --check
python -m unittest discover -s tests -v
python scripts/package_skills.py
```

打包结果写入 `dist/<skill-name>.skill`。该目录是本地构建产物，不进入 Git。

### 方式一：Claude Code 插件

仓库发布后，在 Claude Code 中添加市场并安装完整技能集：

```text
/plugin marketplace add isLinXu/islinxu-skills
/plugin install islinxu-skills@islinxu
```

插件清单位于 `.claude-plugin/`。实际发现、启用和重载行为以当前 Claude Code 版本为准。

### 方式二：项目规则入口

根目录 `CLAUDE.md` 与 `.cursor/rules/surgical-coding.mdc` 为编码行为规则提供项目级入口。两者由 `surgical-coding/SKILL.md` 生成，不手工重复维护：

```bash
# 修改技能正文后重新生成
python scripts/sync_guides.py

# 检查入口是否与技能正文一致
python scripts/sync_guides.py --check
```

### 方式三：项目级复制

将某个完整技能目录复制到项目的 `.agents/skills/`，或复制到所用 Agent 宿主声明的技能目录。不要只复制 `SKILL.md` 而遗漏它引用的 `references/`、`scripts/` 或 `assets/`。

```bash
mkdir -p /path/to/project/.agents/skills
cp -R skills/multimodal-eval /path/to/project/.agents/skills/
```

不同宿主的全局技能目录和发现机制并不相同，应以宿主文档为准；本仓库不声称复制文件后已在某个宿主中自动生效。

## 仓库结构

```text
.
├── skills/<skill-name>/
│   ├── SKILL.md                 # 必需：name、description 与执行流程
│   ├── references/              # 按需读取的专项清单与示例
│   └── scripts/                 # 可重复、确定性的辅助脚本
├── prompts/<slug>.md            # 可直接复用的 Prompt
├── CLAUDE.md                    # 生成的 Claude Code 项目规则
├── .cursor/rules/               # 生成的 Cursor 项目规则
├── .claude-plugin/
│   ├── plugin.json              # 完整技能集的插件清单
│   └── marketplace.json         # Claude Code 市场入口
├── scripts/
│   ├── validate_repo.py         # 仓库结构、清单与本地链接校验
│   ├── sync_guides.py           # 从技能正文生成项目规则入口
│   ├── package_skills.py        # 标准 .skill ZIP 打包
│   └── export_observatory.py    # 导出到 Model Observatory
├── tests/                       # 不访问网络的回归测试
├── observatory.json             # 导出所需的技能元数据
└── .github/workflows/ci.yml     # 校验 → 同步检查 → 测试 → 打包
```

## 与 Model Observatory 同步

[`model-observatory`](https://github.com/isLinXu/model-observatory) 使用 `templates/skills/<slug>.md` 和 `templates/prompts/<slug>.md` 作为看板索引源。本仓库的 `skills/` 是标准技能包，因此通过显式导出桥接，而不维护两份手写副本：

```bash
# 先预览将写入的文件，不修改目标仓库
python scripts/export_observatory.py /path/to/model-observatory --check

# 确认后导出；已有内容不同时需要 --force
python scripts/export_observatory.py /path/to/model-observatory --force
```

导出后仍需在 Model Observatory 仓库中运行它自己的采集与测试流程。本脚本不会提交、推送或部署目标仓库。

## 与 eval-skills 的分工

本仓库维护技能内容与确定性工具，CI 只证明结构、脚本和打包回归通过，**不等同于 Agent 行为质量已经达标**。需要评估单技能的完成率、延迟、错误或一致性时，将技能接入 [`eval-skills`](https://github.com/isLinXu/eval-skills) 的 L1 评测，并把行为评测报告与这里的离线测试结果分开保存。

## 质量约定

- **单一事实源**：技能正文只存在于 `skills/`；观测站模板由导出脚本生成。
- **事实、决策、假设分离**：没有来源或运行证据的内容不得写成已观察事实。
- **最小充分实现**：不增加未要求的抽象、配置和无关差异；简单任务不机械套用完整流程。
- **同口径比较**：基线与候选必须共享数据、配置、指标定义和统计窗口。
- **分级验收与差异审查**：所有技能按领域执行目标检查、邻近回归、真实流程和最终差异核对，不用最小测试替代完整交付。
- **失败可区分**：`unavailable`、`stale`、`partial`、断链和未核对不得混为“0”或“成功”。
- **离线回归门**：结构、语法、脚本行为和打包先在无网络环境通过，再考虑发布。
- **最小充分上下文**：`SKILL.md` 只放核心流程，详细清单进入 `references/`，确定性操作进入 `scripts/`。

## 内容来源与边界

仓库方向依据以下公开资料整理：

- [个人主页](https://islinxu.github.io/)：多模态模型、评测、Agent 工程与开源方向。
- [项目页](https://islinxu.github.io/projects/)：paper-list、eval-skills、YOLO、Agent 与公开知识整理项目。
- [Model Observatory](https://islinxu.github.io/model-observatory/#overview)：模板库、快照口径、实体关系、任务看板与质量保障实践。
- 随请求提供的《工作区约定》：检索边界、长程协作、专项调试与文档组织规范。

这些资料用于提炼工作方法；未公开的训练细节、业务数据、凭据和私人信息不属于本仓库内容。

## 贡献与许可

新增或修改技能前请阅读 [AGENTS.md](AGENTS.md) 与 [CONTRIBUTING.md](CONTRIBUTING.md)。

代码与原创内容采用 [MIT License](LICENSE)。
