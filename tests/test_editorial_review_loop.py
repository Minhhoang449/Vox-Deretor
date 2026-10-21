"""Keep the adapted humanizer/red-pen workflow wired into active authoring."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class EditorialReviewLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loop = (ROOT / "references/editorial-review-loop.md").read_text(encoding="utf-8")
        cls.pipeline = (ROOT / "references/local-pipeline.md").read_text(encoding="utf-8")
        cls.skill = (ROOT / "skills/vox-channel-documentary/SKILL.md").read_text(encoding="utf-8")
        cls.story_card = (ROOT / "references/templates/story-card.md").read_text(encoding="utf-8")

    def test_loop_runs_red_pen_edit_fact_check_voice_and_second_review_in_order(self):
        stages = [
            "**Red-pen pass.**",
            "**Fact-check the proposed edits.**",
            "**Channel-voice and naturalness pass.**",
            "**Pattern and wording check.**",
            "**Second red-pen pass.**",
            "**Separate story and retention reviews.**",
        ]
        offsets = [self.loop.index(stage) for stage in stages]
        self.assertEqual(offsets, sorted(offsets))

    def test_wording_review_is_contextual_not_a_global_blocklist(self):
        self.assertIn("Do not use a universal banned-word list", self.loop)
        self.assertIn("not executable slash commands", self.loop)

    def test_active_pipeline_and_skill_require_the_loop(self):
        self.assertIn("editorial-review-loop.md", self.pipeline)
        self.assertIn("editorial-review-loop.md", self.skill)
        self.assertIn("do not use universal banned-word lists", self.skill)

    def test_story_card_captures_findings_and_reviewed_version(self):
        self.assertIn("factual rechecks after edits", self.story_card)
        self.assertIn("normalized SHA-256", self.story_card)
        self.assertIn("unresolved blockers", self.story_card)


if __name__ == "__main__":
    unittest.main()
