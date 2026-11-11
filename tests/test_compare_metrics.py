import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "multimodal-eval" / "scripts" / "compare_metrics.py"
SPEC = importlib.util.spec_from_file_location("compare_metrics", SCRIPT)
compare_metrics = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(compare_metrics)


class CompareMetricsTest(unittest.TestCase):
    def test_delta_counts_and_missing_metrics(self):
        baseline = {
            "run_id": "base",
            "metrics": {
                "overall": {"value": 0.8, "count": 80, "total": 100},
                "old-only": {"value": 2},
            },
        }
        candidate = {
            "run_id": "candidate",
            "metrics": {
                "overall": {"value": 0.82, "count": 82, "total": 100},
                "new-only": {"value": 1},
            },
        }
        result = compare_metrics.compare_runs(baseline, candidate)
        self.assertAlmostEqual(result["metrics"]["overall"]["delta"], 0.02)
        self.assertEqual(result["metrics"]["overall"]["baseline_count"], 80)
        self.assertIsNone(result["metrics"]["old-only"]["delta"])
        self.assertEqual(result["metrics"]["old-only"]["status"], "missing_in_candidate")
        self.assertEqual(result["metrics"]["new-only"]["status"], "missing_in_baseline")
        self.assertEqual(result["significance"], "not_evaluated")

    def test_invalid_denominator_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps({"metrics": {"x": {"value": 1, "count": 2, "total": 1}}}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "count exceeds total"):
                compare_metrics._load_run(path)

    def test_non_finite_value_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"metrics": {"x": {"value": NaN}}}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "finite"):
                compare_metrics._load_run(path)


if __name__ == "__main__":
    unittest.main()
