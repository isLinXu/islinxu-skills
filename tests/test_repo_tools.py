import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from export_observatory import export
from package_skills import package_skill
from sync_guides import sync_guides
from validate_repo import validate_repo


class RepositoryToolsTest(unittest.TestCase):
    def test_repository_is_valid(self):
        self.assertEqual(validate_repo(ROOT), [])

    def test_all_skills_require_real_flow_and_diff_review(self):
        skill_files = list((ROOT / "skills").glob("*/SKILL.md"))
        self.assertTrue(skill_files)
        for skill_file in skill_files:
            with self.subTest(skill=skill_file.parent.name):
                body = skill_file.read_text(encoding="utf-8")
                self.assertIn("真实流程", body)
                self.assertIn("差异审查", body)

    def test_plugin_manifest_covers_every_skill(self):
        plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        declared = {Path(item).name for item in plugin["skills"]}
        actual = {path.name for path in (ROOT / "skills").iterdir() if path.is_dir()}
        self.assertEqual(declared, actual)
        self.assertEqual(len(declared), len(plugin["skills"]))
        self.assertEqual(marketplace["plugins"][0]["name"], plugin["name"])
        self.assertEqual(marketplace["plugins"][0]["source"], "./")

    def test_generated_guides_are_current_and_reproducible(self):
        self.assertEqual(sync_guides(ROOT, check=True), [])
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            source = ROOT / "skills" / "surgical-coding" / "SKILL.md"
            destination = target / "skills" / "surgical-coding" / "SKILL.md"
            destination.parent.mkdir(parents=True)
            destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            stale = sync_guides(target)
            self.assertEqual(stale, ["CLAUDE.md", ".cursor/rules/surgical-coding.mdc"])
            self.assertIn("管理假设、歧义与矛盾", (target / "CLAUDE.md").read_text(encoding="utf-8"))
            cursor = (target / ".cursor" / "rules" / "surgical-coding.mdc").read_text(encoding="utf-8")
            self.assertIn("alwaysApply: true", cursor)
            self.assertIn("../../skills/surgical-coding/references/examples.md", cursor)
            (target / "CLAUDE.md").write_text("stale\n", encoding="utf-8")
            self.assertEqual(sync_guides(target, check=True), ["CLAUDE.md"])
            sync_guides(target)
            self.assertEqual(sync_guides(target, check=True), [])

    def test_package_preserves_skill_root_and_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            archive_path = package_skill(ROOT / "skills" / "paper-curation", Path(directory))
            self.assertEqual(archive_path.suffix, ".skill")
            with zipfile.ZipFile(archive_path) as archive:
                names = set(archive.namelist())
                self.assertIn("paper-curation/SKILL.md", names)
                self.assertIn("paper-curation/scripts/paper_identity.py", names)
                self.assertIsNone(archive.testzip())

    def test_observatory_export_preview_conflict_and_force(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            statuses, conflicts = export(ROOT, target, check=True)
            self.assertTrue(any(line.startswith("CREATE") for line in statuses))
            self.assertEqual(conflicts, [])
            self.assertFalse((target / "templates").exists())

            export(ROOT, target)
            skill_template = target / "templates" / "skills" / "paper-curation.md"
            self.assertTrue(skill_template.is_file())
            original = skill_template.read_text(encoding="utf-8")
            skill_template.write_text("local draft\n", encoding="utf-8")

            _, conflicts = export(ROOT, target)
            self.assertIn("templates/skills/paper-curation.md", conflicts)
            self.assertEqual(skill_template.read_text(encoding="utf-8"), "local draft\n")

            _, conflicts = export(ROOT, target, force=True)
            self.assertIn("templates/skills/paper-curation.md", conflicts)
            self.assertEqual(skill_template.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
