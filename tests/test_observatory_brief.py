import importlib.util
from datetime import datetime, timezone
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "observatory-brief" / "scripts" / "observatory_brief.py"
SPEC = importlib.util.spec_from_file_location("observatory_brief", SCRIPT)
brief = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(brief)

AT = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)


class ObservatoryBriefTest(unittest.TestCase):
    def test_deadlines_filter_past_tbd_and_unknown_time(self):
        payload = {
            "conferences": [
                {
                    "key": "AI/test",
                    "editions": [
                        {
                            "id": "test27",
                            "url": "https://example.com/conf",
                            "events": [
                                {"id": "future", "kind": "paper", "utc": "2026-11-12T00:00:00Z", "time_status": "ok", "tbd": False},
                                {"id": "past", "kind": "paper", "utc": "2026-11-01T00:00:00Z", "time_status": "ok", "tbd": False},
                                {"id": "abstract", "kind": "abstract", "utc": "2026-11-12T00:00:00Z", "time_status": "ok", "tbd": False},
                                {"id": "tbd", "kind": "paper", "utc": None, "time_status": "tbd", "tbd": True},
                            ],
                        }
                    ],
                }
            ]
        }
        rows = brief.upcoming_deadlines(payload, AT, 30, 5)
        self.assertEqual([row[3]["id"] for row in rows], ["future"])

    def test_brief_preserves_health_status_and_sample_boundary(self):
        payloads = {
            "runs.json": {"covers": "采集与索引", "runs": [{"status": "partial", "recorded_at": "2026-11-10T10:00:00Z", "steps_failed": ["papers"], "steps_missing": []}]},
            "tasks.json": {"captured_at": "2026-11-10T10:00:00Z", "summary": {"by_status": {"doing": 1}}, "tasks": [{"slug": "real-task", "title": "Real task", "status": "doing", "url": "https://example.com/task"}]},
            "awesome.json": {
                "status": "partial",
                "captured_at": "2026-11-10T10:00:00Z",
                "summary": {"added": 2, "removed": 0, "repos_ok": 1, "repos_stale": 1, "stalled": 0},
                "repos": [{"id": "owner/list", "sample": [{"id": "arxiv:1", "title": "Paper", "url": "https://arxiv.org/abs/1", "is_new": True}]}],
            },
        }
        output = brief.render_brief(payloads, {"github.json": "offline"}, at=AT, limit=5)
        self.assertIn("**partial**", output)
        self.assertIn("覆盖范围：采集与索引", output)
        self.assertIn("不等于遍历全部新增", output)
        self.assertIn("github.json` 读取失败", output)
        self.assertIn("Real task", output)

    def test_url_whitelist(self):
        self.assertIsNone(brief.safe_url("javascript:alert(1)"))
        self.assertEqual(brief.safe_url("https://example.com/a"), "https://example.com/a")


if __name__ == "__main__":
    unittest.main()
