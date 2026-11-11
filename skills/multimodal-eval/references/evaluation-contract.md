# 评测契约参考

## 契约字段

| 维度 | 至少记录 |
| --- | --- |
| 模型 | 名称、权重或 API 版本、适配器、量化、推理后端 |
| 数据 | 数据集版本、划分、样本 id、图像或文本预处理、哈希 |
| 提示 | 系统提示、问题模板、选项顺序、few-shot 示例 |
| 解码 | 温度、top-p、最大 token、种子、停止词、重试策略 |
| 工具 | 工具版本、权限、超时、外部环境和可用网络 |
| 解析 | 原始输出、答案提取规则、等价答案、失败类别 |
| 指标 | 公式、分母、宏微平均、切片、缺失值和统计窗口 |
| Judge | 模型、Prompt、温度、校准集、人工一致性与盲评设置 |
| 环境 | 代码提交、依赖、硬件、运行时间、脚本版本 |

## 对比输入格式

`compare_metrics.py` 接受一个 JSON 对象：

```json
{
  "schema_version": 1,
  "run_id": "baseline-001",
  "metrics": {
    "overall": {"value": 0.8, "count": 80, "total": 100},
    "slice/counting": {"value": 0.6, "count": 12, "total": 20}
  }
}
```

- `value` 必须是有限数值；脚本不假设它一定是 0–1 比例。
- `count` 与 `total` 可选，但若出现必须是非负数，且 `count <= total`。
- 顶层额外字段会保留在输入中，但比较器只读取 `run_id`、`metrics` 和各指标的 `value`、`count`、`total`。
- 同一指标只在一个对象中缺失时，差异写 `null`，状态为 `missing_in_baseline` 或 `missing_in_candidate`，不按 0 计算。
- 输出 `delta = candidate - baseline`；脚本不判断显著性、不自动写“提升”。

示例输出摘要：

```json
{
  "schema_version": 1,
  "baseline_run_id": "baseline-001",
  "candidate_run_id": "candidate-001",
  "metrics": {
    "overall": {
      "baseline": 0.8,
      "candidate": 0.82,
      "delta": 0.02,
      "status": "compared"
    }
  }
}
```

## 报告边界

- 同一模型的原始输出可复核，才能区分模型错误与解析错误。
- 只有汇总均值、没有样本数和切片时，将结论限制为汇总观察。
- 小样本差异、单次运行和未校准 Judge 不作为强结论。
- 数据或 Prompt 改变时建立新评测契约，不与旧结果直接拼成趋势。
