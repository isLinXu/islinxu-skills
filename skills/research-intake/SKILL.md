---
name: research-intake
description: 将 Model Observatory 的论文与模型清单样本转成去重、带来源、待人工审核的研究候选。用于新论文入库、模型线索分诊、重复任务检查和生成研究任务草稿前的准备。
---

# 研究线索入库

把公开清单中的条目变成候选，而不是直接变成承诺。保留来源、快照、样本边界和审核状态，默认不写入任务看板。

## 1. 确认入库范围

- 论文来自 `awesome.json` 的发布样本，只处理 `is_new=true` 的条目。
- 模型来自 `homc.json` 的发布样本，处理 `new`、`unverified` 或快照差异标记为新的行。
- 已有任务来自 `tasks.json`，用于按 slug 排除已跟踪对象。
- 不把清单自报总数、下载量、引用数或来源等级复制成候选优先级。
- 详细字段与去重规则见 [入库契约](references/intake-contract.md)。

## 2. 生成候选清单

联网读取公开快照：

```bash
python scripts/research_intake.py --kind all --limit 20 --output intake.json
```

离线复现：

```bash
python scripts/research_intake.py --data-dir /path/to/snapshots --kind papers --limit 20 --output intake.json
```

数据目录需要 `awesome.json`、`homc.json`、`tasks.json`。使用 `--kind papers` 或 `--kind models` 时，未选择的来源不会发起请求。

## 3. 人工分诊

逐条选择：

- **接受**：确认主题相关、来源可访问、尚未跟踪，再创建任务或加入阅读队列。
- **暂缓**：保留候选及原因，不伪装成已阅读或已立项。
- **拒绝**：记录重复、范围外、来源不足或主题不符，不删除原始快照。
- **补充核查**：论文回原文，模型回提供方或一手来源；A/B/C 只表示原清单的来源标注，不表示当前 agent 已核实。

候选 JSON 中 `review_required` 永远为 `true`。只有人工或明确授权流程才能改变后续任务状态，初始任务仍应从 `proposal` 开始。

## 4. 去重与承接

- 论文优先按规范化条目 id 去重，同一 arXiv id 在多个清单出现时合并来源。
- 模型按清单提供的名称 slug 去重，不把同名不同型号仅凭标题合并。
- 已存在于 `tasks.json` 的 slug 计入 `already_tracked`，不生成第二张候选卡。
- 合并后来源数组保留每个清单、采集时间、分区和审核信息，不挑一个来源抹掉其他证据。
- 样本之外可能仍有条目，输出 `sample_limited` 和跳过计数，不宣称全量入库。

## 5. 分级验证与差异审查

1. **目标检查**：测试跨清单去重、已有任务排除、非法 URL、来源保留和数量限制。
2. **邻近回归**：检查空样本、旧快照、模型三态、缺 id 和部分来源失败。
3. **真实流程**：对公开快照生成一次候选，抽查 slug、链接、来源和已跟踪排除能回到原数据。
4. **差异审查**：比较相邻候选文件，区分新条目、来源合并、审核决定和快照变化；不自动改写既有任务或覆盖人工决定。

## 完成标准

每个候选都有稳定 slug、种类、标题、合法 URL、来源数组和 `review_required=true`。无法确认的内容保留未知，不通过标题猜测论文或模型事实。
