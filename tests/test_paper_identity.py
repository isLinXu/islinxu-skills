import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "paper-curation" / "scripts" / "paper_identity.py"
SPEC = importlib.util.spec_from_file_location("paper_identity", SCRIPT)
paper_identity = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(paper_identity)


class PaperIdentityTest(unittest.TestCase):
    def test_arxiv_url_and_version_are_normalized(self):
        self.assertEqual(
            paper_identity.normalize_arxiv("https://arxiv.org/abs/2401.00001v2"),
            "arxiv:2401.00001",
        )
        self.assertEqual(
            paper_identity.normalize_arxiv("arXiv:2401.00001v10"),
            "arxiv:2401.00001",
        )
        self.assertEqual(
            paper_identity.normalize_arxiv("https://arxiv.org/pdf/2401.00001.pdf"),
            "arxiv:2401.00001",
        )

    def test_old_style_identifier_is_supported(self):
        self.assertEqual(paper_identity.normalize_arxiv("hep-th/9901001v2"), "arxiv:hep-th/9901001")

    def test_non_ascii_title_uses_stable_nonempty_hash(self):
        first = paper_identity.title_identity("多模态评测：方法与挑战")
        self.assertRegex(first, r"^title:[0-9a-f]{16}$")
        self.assertEqual(first, paper_identity.title_identity(" 多模态评测：方法与挑战 "))
        self.assertNotEqual(first, paper_identity.title_identity("另一篇论文"))

    def test_ascii_title_is_human_readable(self):
        self.assertEqual(paper_identity.title_identity("A Survey of MLLM Evaluation"), "title:a-survey-of-mllm-evaluation")

    def test_invalid_or_ambiguous_input_is_rejected(self):
        with self.assertRaises(ValueError):
            paper_identity.normalize_arxiv("https://example.com/abs/2401.00001")
        with self.assertRaises(ValueError):
            paper_identity.paper_identity()
        with self.assertRaises(ValueError):
            paper_identity.paper_identity(arxiv="2401.00001", title="duplicate")


if __name__ == "__main__":
    unittest.main()
