import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "research-intake" / "scripts" / "research_intake.py"
SPEC = importlib.util.spec_from_file_location("research_intake", SCRIPT)
intake = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(intake)


def awesome_fixture():
    return {
        "status": "partial",
        "captured_at": "2026-11-10T10:00:00Z",
        "repos": [
            {
                "id": "owner/one",
                "status": "ok",
                "sample": [{"id": "arxiv:2611.00001", "title": "Paper One", "url": "https://arxiv.org/abs/2611.00001", "is_new": True}],
            },
            {
                "id": "owner/two",
                "status": "ok",
                "upstream": True,
                "sample": [
                    {"id": "arxiv:2611.00001", "title": "Paper One", "url": "https://arxiv.org/abs/2611.00001", "is_new": True, "section": "Agents"},
                    {"id": "arxiv:2611.00002", "title": "Already Tracked", "url": "https://arxiv.org/abs/2611.00002", "is_new": True},
                    {"id": "arxiv:2611.00003", "title": "Bad URL", "url": "javascript:alert(1)", "is_new": True},
                ],
            },
        ],
    }


def homc_fixture():
    return {
        "status": "ok",
        "captured_at": "2026-11-10T10:00:00Z",
        "as_of": "2026-11-09",
        "rows": [
            {
                "id": "homc:example-model|abc123",
                "name": "Example Model",
                "url": "https://example.com/model",
                "state": "unverified",
                "is_new": False,
                "vendor": "Example",
                "grades": ["B"],
                "single_b_source": True,
            }
        ],
    }


class ResearchIntakeTest(unittest.TestCase):
    def test_cross_list_dedup_tracking_and_source_preservation(self):
        result = intake.collect_candidates(
            awesome=awesome_fixture(),
            homc=homc_fixture(),
            tasks={"tasks": [{"slug": "paper-2611-00002"}]},
            generated_at="2026-11-10T12:00:00Z",
        )
        self.assertEqual(len(result["candidates"]), 2)
        self.assertEqual([item["kind"] for item in result["candidates"]], ["paper", "model"])
        paper = next(item for item in result["candidates"] if item["kind"] == "paper")
        model = next(item for item in result["candidates"] if item["kind"] == "model")
        self.assertEqual(len(paper["sources"]), 2)
        self.assertTrue(paper["sources"][1]["upstream"])
        self.assertTrue(model["review_required"])
        self.assertEqual(model["sources"][0]["state"], "unverified")
        self.assertTrue(model["sources"][0]["single_b_source"])
        self.assertEqual(result["already_tracked"], ["paper-2611-00002"])
        self.assertEqual(result["skipped"]["invalid_url"], 1)

    def test_limit_is_explicit_and_missing_tasks_is_not_claimed_as_checked(self):
        result = intake.collect_candidates(awesome=awesome_fixture(), tasks=None, kind="papers", limit=1)
        self.assertEqual(len(result["candidates"]), 1)
        self.assertTrue(result["sample_limited"])
        self.assertIn("over_limit", result["skipped"])
        self.assertFalse(result["tracking_checked"])

    def test_stale_sources_do_not_produce_fresh_candidates(self):
        awesome = awesome_fixture()
        for repo in awesome["repos"]:
            repo["status"] = "stale"
        result = intake.collect_candidates(awesome=awesome, tasks={"tasks": []}, kind="papers")
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["skipped"]["stale_or_unavailable_repositories"], 2)


if __name__ == "__main__":
    unittest.main()
