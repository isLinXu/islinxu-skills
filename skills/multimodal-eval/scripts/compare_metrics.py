#!/usr/bin/env python3
"""Compare same-contract evaluation metrics without inferring significance."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def _load_run(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        run = json.load(handle)
    if not isinstance(run, dict):
        raise ValueError(f"{source}: top level must be an object")
    if run.get("schema_version", 1) != 1:
        raise ValueError(f"{source}: unsupported schema_version")
    metrics = run.get("metrics")
    if not isinstance(metrics, dict):
        raise ValueError(f"{source}: metrics must be an object")
    for name, metric in metrics.items():
        if not isinstance(name, str) or not name:
            raise ValueError(f"{source}: metric names must be non-empty strings")
        if not isinstance(metric, dict):
            raise ValueError(f"{source}: metric {name!r} must be an object")
        value = metric.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{source}: metric {name!r} value must be numeric")
        if not math.isfinite(value):
            raise ValueError(f"{source}: metric {name!r} value must be finite")
        count, total = metric.get("count"), metric.get("total")
        if (count is None) != (total is None):
            raise ValueError(f"{source}: metric {name!r} count and total must appear together")
        if count is not None:
            for field, number in (("count", count), ("total", total)):
                if isinstance(number, bool) or not isinstance(number, int) or number < 0:
                    raise ValueError(f"{source}: metric {name!r} {field} must be a non-negative integer")
            if count > total:
                raise ValueError(f"{source}: metric {name!r} count exceeds total")
    return run


def compare_runs(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Return explicit value deltas and preserve missing metrics as unknown."""
    baseline_metrics = baseline["metrics"]
    candidate_metrics = candidate["metrics"]
    rows: dict[str, Any] = {}
    for name in sorted(set(baseline_metrics) | set(candidate_metrics)):
        old = baseline_metrics.get(name)
        new = candidate_metrics.get(name)
        if old is None:
            row = {"baseline": None, "candidate": new["value"], "delta": None, "status": "missing_in_baseline"}
        elif new is None:
            row = {"baseline": old["value"], "candidate": None, "delta": None, "status": "missing_in_candidate"}
        else:
            row = {
                "baseline": old["value"],
                "candidate": new["value"],
                "delta": new["value"] - old["value"],
                "status": "compared",
            }
        for label, metric in (("baseline", old), ("candidate", new)):
            if metric is not None and "count" in metric:
                row[f"{label}_count"] = metric["count"]
                row[f"{label}_total"] = metric["total"]
        rows[name] = row
    return {
        "schema_version": 1,
        "baseline_run_id": baseline.get("run_id"),
        "candidate_run_id": candidate.get("run_id"),
        "significance": "not_evaluated",
        "metrics": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", help="baseline JSON run")
    parser.add_argument("candidate", help="candidate JSON run")
    parser.add_argument("--output", help="write diff JSON here instead of stdout")
    args = parser.parse_args()
    try:
        result = compare_runs(_load_run(args.baseline), _load_run(args.candidate))
        payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.output:
            Path(args.output).write_text(payload, encoding="utf-8")
        else:
            print(payload, end="")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
