import os, sys, unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))
import thumbnail_visual_direction as t


def cand(text, title, source, character="a villager", emotion="strained", **kw):
    c = {"thumbnail_text": text, "title": title, "text_source_line": source,
         "character": character, "emotion": emotion,
         "thumbnail_prompt": "One Chibi character in the centre, no diagrams or arrows"}
    c.update(kw)
    return c


AMARNA_TITLE = "How Did Ancient Egyptians Get Water? A Village With No Well"
AMARNA_LINE = "The village lay about 1.2 kilometres from the city wells, so every jar came 1.2 km for water."

# One sample per channel: (channel, language, title, text, source line, expected pass)
CHANNEL_CASES = [
    ("chikyu-shikumi", "ja", "縄文人は栃の実をどう食べた？20メートルの水場の謎", "苦すぎる木の実",
     "栃の実はそのままでは苦すぎる木の実だった。", True),
    ("battlefield-bearings", "en", AMARNA_TITLE, "1.2 KM FOR WATER", AMARNA_LINE, False),  # 4 words + repeats "water"
    ("battlefield-bearings", "en", AMARNA_TITLE, "NO WELL HERE", "There was no well here.", False),
    ("terra-rewired", "en", "How Did Ancient People Make Rope?", "HE DOES NOTHING?",
     "He does nothing for an hour while the fibres soak.", False),
    ("last-safe-minute", "en", "How Did Ice Age Hunters Cook Without Pots?", "BOILING WITH STONES",
     "They were boiling with stones dropped into hide bags.", True),
    ("status-and-systems", "en", "Why Did Ancient Romans Queue for Bread?", "FREE GRAIN, MONTHLY",
     "Citizens received free grain, monthly, from the state.", True),
    ("vi-sao-noi-nay", "vi", "Người Óc Eo sống trên nước bằng cách nào?", "NHÀ TRÊN CỌC",
     "Họ dựng nhà trên cọc gỗ cao hơn mức lũ.", True),
]


class StudioThumbnailRules(unittest.TestCase):
    def test_channel_cases(self):
        for channel, lang, title, text, line, ok in CHANNEL_CASES:
            with self.subTest(channel=channel, text=text):
                errs = t.check_thumbnail_candidate(cand(text, title, line), lang)
                self.assertEqual(errs == [], ok, errs)

    def test_amarna_repeat_reason(self):
        errs = t.check_thumbnail_candidate(cand("NO WELL HERE", AMARNA_TITLE, "There was no well here."), "en")
        self.assertTrue(any("repeats the title" in e for e in errs))

    def test_amarna_1_2_km_for_water_fails_on_length_and_repeat(self):
        errs = t.check_thumbnail_candidate(cand("1.2 KM FOR WATER", AMARNA_TITLE, AMARNA_LINE), "en")
        self.assertTrue(any("4 words" in e for e in errs))
        self.assertTrue(any("water" in e for e in errs))

    def test_prompt_carries_cute_mischievous_tone(self):
        p = t.thumbnail_visual_prompt({**t.THUMBNAIL_PROFILE, "language": "en"})
        self.assertIn("slightly mischievous", p)
        self.assertIn("Never mock real people", p)

    def test_rope_question_reason(self):
        errs = t.check_thumbnail_candidate(cand("HE DOES NOTHING?", "Rope", "He does nothing."), "en")
        self.assertTrue(any("question" in e for e in errs))

    def test_word_and_char_limits(self):
        self.assertTrue(any("words" in e for e in t.check_thumbnail_text("FOUR WORDS RIGHT HERE", "X", "en")))
        self.assertTrue(any("4 words" in e for e in t.check_thumbnail_text("1.2 KM FOR WATER", "Title", "en")))
        self.assertEqual(t.check_thumbnail_text("1.2 KM WALK", "Title", "en"), [])
        self.assertTrue(any("characters" in e for e in t.check_thumbnail_text("苦すぎる木の実を食べた", "題", "ja")))

    def test_required_fields(self):
        errs = t.check_thumbnail_candidate(cand("BOILING STONES", "T", "boiling stones", character="", emotion=""), "en")
        self.assertTrue(any("character" in e for e in errs))
        self.assertTrue(any("emotion" in e for e in errs))
        errs = t.check_thumbnail_candidate(cand("BOILING STONES", "T", ""), "en")
        self.assertTrue(any("text_source_line" in e for e in errs))

    def test_text_must_be_in_narration_and_numbers_sourced(self):
        c = cand("1.2 KM WALK", AMARNA_TITLE, AMARNA_LINE)
        self.assertEqual(t.check_thumbnail_candidate(c, "en", narration="Intro. " + AMARNA_LINE), [])
        self.assertTrue(any("narration" in e for e in t.check_thumbnail_candidate(c, "en", narration="Something else.")))
        c = cand("3 KM WALK", AMARNA_TITLE, AMARNA_LINE)
        self.assertTrue(any("number 3" in e for e in t.check_thumbnail_candidate(c, "en")))

    def test_character_must_be_human_and_centred(self):
        errs = t.check_thumbnail_candidate(cand("BOILING STONES", "T", "boiling stones",
                                                character={"description": "a large jar", "position": "left"}), "en")
        self.assertTrue(any("human" in e for e in errs))
        self.assertTrue(any("center" in e for e in errs))

    def test_no_diagram_or_arrow(self):
        c = cand("BOILING STONES", "T", "boiling stones", thumbnail_prompt="villager with an arrow to the well")
        self.assertTrue(any("diagram" in e for e in t.check_thumbnail_candidate(c, "en")))

    def test_museum_image_needs_open_access_or_licence(self):
        c = cand("BOILING STONES", "T", "boiling stones", museum_images=[{"source_url": "https://museum.example/1"}])
        self.assertTrue(any("licence" in e for e in t.check_thumbnail_candidate(c, "en")))
        c["museum_images"][0]["licence"] = "CC0 Open Access"
        self.assertEqual(t.check_thumbnail_candidate(c, "en"), [])

    def test_prompt_uses_channel_identity_and_no_realistic_branch(self):
        for cid in ("chikyu-shikumi", "battlefield-bearings", "terra-rewired"):
            p = t.resolve_thumbnail_profile(cid, {"animation_style": "documentary-realistic"})
            self.assertEqual(p["revision"], "studio-chibi-thumbnail-v4")
            self.assertIn("Chibi", p["style"])
            prompt = t.thumbnail_visual_prompt(p)
            self.assertIn("Channel palette:", prompt)
            self.assertIn("No diagrams, arrows", prompt)
            self.assertNotIn("photorealistic", prompt.lower())


if __name__ == "__main__":
    unittest.main()
