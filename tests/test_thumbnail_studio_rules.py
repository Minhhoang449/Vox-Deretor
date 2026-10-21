import os, sys, unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))
import thumbnail_visual_direction as t


def cand(text, title, source, character="a villager", emotion="strained", **kw):
    c = {"thumbnail_text": text, "title": title, "text_source_line": source,
         "character": character, "emotion": emotion,
         "thumbnail_prompt": "One Chibi character in the centre, no diagrams or arrows"}
    c.update({"character_count": 1, "subject_area_ratio": 0.5, "expression_readable_160px": True,
              "main_colors": ["ochre", "blue", "cream"], "text_position": "top-left",
              "variants": [{"label": "A", "thumbnail_text": text, "emotion": emotion},
                           {"label": "B", "thumbnail_text": text, "emotion": "gleeful"}]})
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
    ("terra-rewired", "en", "How Did Ancient People Make Rope?", "DOING NOTHING?",
     "He is doing nothing for an hour while the fibres soak.", True),
    ("battlefield-bearings", "en", AMARNA_TITLE, "NO WELL?!", "There was no well.", False),  # repeats "well"
    ("battlefield-bearings", "en", "How Did Amarna Workers Get Water?", "NO WELL?!", "There was no well.", True),
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

    def test_everyday_questions_allowed_and_no_is_not_a_repeat(self):
        self.assertEqual(t.check_thumbnail_text("DOING NOTHING?", "How Did Ancient People Make Rope?", "en"), [])
        self.assertEqual(t.check_thumbnail_text("NO WELL?!", "No Water Nearby", "en"), [])

    def test_japanese_limit_is_8(self):
        self.assertEqual(t.THUMBNAIL_PROFILE["max_text_chars_cjk"], 8)
        self.assertEqual(t.check_thumbnail_text("あいうえおかきく", "題", "ja"), [])
        self.assertTrue(any("9 characters" in e for e in t.check_thumbnail_text("あいうえおかきくけ", "題", "ja")))

    def test_rule1_character_count_and_area(self):
        base = lambda **kw: t.check_thumbnail_candidate(cand("BOILING STONES", "T", "boiling stones", **kw), "en")
        self.assertTrue(any("character_count" in e for e in base(character_count=2)))
        self.assertTrue(any("character_count" in e for e in base(character_count=None)))
        self.assertTrue(any("subject_area_ratio" in e for e in base(subject_area_ratio=0.3)))
        self.assertTrue(any("subject_area_ratio" in e for e in base(subject_area_ratio="big")))
        self.assertTrue(any("160" in e for e in base(expression_readable_160px=False)))

    def test_rule5_colours_and_text_position(self):
        base = lambda **kw: t.check_thumbnail_candidate(cand("BOILING STONES", "T", "boiling stones", **kw), "en")
        self.assertTrue(any("4 colours" in e for e in base(main_colors=["a", "b", "c", "d"])))
        self.assertTrue(any("main_colors" in e for e in base(main_colors=None)))
        self.assertTrue(any("bottom-right" in e for e in base(text_position="bottom right")))
        self.assertTrue(any("text_position" in e for e in base(text_position="")))

    def test_rule6_variants(self):
        base = lambda v: t.check_thumbnail_candidate(cand("BOILING STONES", "T", "boiling stones", variants=v), "en")
        self.assertTrue(any("exactly two" in e for e in base(None)))
        self.assertTrue(any("exactly two" in e for e in base([{"label": "A"}])))
        same = {"label": "A", "thumbnail_text": "X Y", "emotion": "glee"}
        self.assertTrue(any("identical" in e for e in base([same, {**same, "label": "B"}])))
        self.assertTrue(any("A and B" in e for e in base([same, {**same, "label": "C", "emotion": "sly"}])))
        self.assertTrue(any("only in text" in e for e in base([same, {**same, "label": "B", "emotion": "sly", "background": "red"}])))
        self.assertTrue(any("variant B" in e for e in base([same, {**same, "label": "B", "thumbnail_text": "ONE TWO THREE FOUR"}])))

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
