# 观测简报数据契约

默认基础地址：`https://islinxu.github.io/model-observatory/data/`。

| 文件 | 简报用途 | 关键字段 | 不能怎样解释 |
| --- | --- | --- | --- |
| `runs.json` | 采集与索引健康 | `runs[0].status`、`steps_failed`、`steps_missing`、`covers` | 运行绿不等于后续构建和部署成功 |
| `tasks.json` | 当前任务与引用 | `tasks[]`、`summary.by_status`、`graph` | `proposal` 不是已承诺，`doing` 不是完成度 |
| `awesome.json` | 论文清单变化与样本 | `summary`、`repos[].diff`、`repos[].sample` | 样本不等于全量；实测与自报不相加 |
| `entities.json` | 研究对象与登记缺口 | `entries`、`validation`、`coverage` | 未核对不是断链，范围外不是待办 |
| `conferences.json` | 投稿窗口 | `conferences[].editions[].events[]` | 社区目录不等于官网，未知时刻不猜测 |
| `github.json` | 公开仓库活动快照 | `repositories[]`、`account` | 推送活动不等于优先级，fork 不默认计入自有项目 |

## 时间口径

- 来源使用自己的 `captured_at`；运行记录使用 `recorded_at`。
- 简报生成时间只说明何时整理，不改写数据的新旧。
- 截止窗口由调用时的 `--at` 或当前 UTC 时间计算；离线复现必须显式传 `--at`。
- 仓库 `pushed_at` 只表示最近推送，不表示某个具体文件更新或研究进展。

## 状态与样本

- 单个来源失败时保留其他板块，并列出失败文件和原因。
- `awesome.repos[].sample` 是受预算限制的样本；`is_new` 只按该快照自己的差异口径使用。
- `entities.coverage` 的未登记列表可以截断，优先读 `unregistered_count` 和 `truncated`，不把数组长度当全量。
- `conferences` 只展开 `kind=paper`、`time_status=ok`、`tbd=false` 且 `utc` 可解析的事件。

## 输出边界

输出是只读 Markdown 简报，不是任务看板的第二份事实源。后续行动仍回到原任务、原快照或官网执行。
