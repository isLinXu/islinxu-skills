# 研究入库契约

## 来源与准入口径

| 来源 | 准入 | 保留证据 | 边界 |
| --- | --- | --- | --- |
| `awesome.json` | `repos[].sample[]` 中 `is_new=true` | 条目 id、标题、URL、分区、发布时间、来源仓库、采集时间 | 只覆盖发布样本；不是全部新增 |
| `homc.json` | `rows[]` 中 `state=new/unverified` 或 `is_new=true` | 名称、提供方、状态、来源等级、单一 B 标记、链接、`as_of` | 等级由原清单判定；`new` 不等于当天首次发现 |
| `tasks.json` | 全部任务 slug | 已有任务状态与 URL | 只用于排除，不改写任务 |

## 候选结构

```json
{
  "slug": "paper-2611-11517",
  "kind": "paper",
  "title": "Example Paper",
  "url": "https://arxiv.org/abs/2611.11517",
  "review_required": true,
  "sources": [
    {
      "type": "awesome",
      "id": "isLinXu/awesome-agent-world-model",
      "captured_at": "2026-11-10T10:00:53Z",
      "section": "example",
      "upstream": false
    }
  ]
}
```

模型候选的 `kind` 为 `model`，来源 `type` 为 `homc`，并保留 `state`、`grades`、`single_b_source`、`vendor` 和 `as_of`。

## 去重规则

- 论文使用清单发布的稳定条目 id。arXiv id `arxiv:2611.11517` 转成 slug `paper-2611-11517`；其他前缀按相同规则安全归一。
- 模型取 `homc:` 后、`|` 前的名称部分作为 slug，例如 `homc-atlas-1-5`。缺少合法前缀或名称时跳过并计数。
- 同一 slug 的多个来源合并到 `sources`，不重复生成候选。
- `tasks.json` 已含相同 slug 时计入 `already_tracked`，候选不再输出。
- 不用模糊标题相似度自动合并，避免把同名不同版本或型号误并。

## 输出状态

顶层包含 `schema_version`、`generated_at`、`candidates`、`already_tracked`、`skipped`、`sample_limited`、`sources` 和 `errors`。

- `sample_limited=true` 表示达到候选上限或来源本身只提供样本。
- `skipped` 记录缺 id、缺标题、非法 URL、已跟踪等明确原因。
- 单个来源失败时其他来源照常输出；全部必需来源失败才退出非零。
- 输出只是审核队列，不包含任务状态、优先级或“已核实”结论。
