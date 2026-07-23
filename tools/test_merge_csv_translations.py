import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("merge_csv_translations.py")
SPEC = importlib.util.spec_from_file_location("merge_csv_translations", MODULE_PATH)
assert SPEC and SPEC.loader
merge_tool = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = merge_tool
SPEC.loader.exec_module(merge_tool)


class MergeCsvTranslationsTests(unittest.TestCase):
    def test_category_rules_cover_requested_content(self):
        row = lambda file_name, key: merge_tool.CsvRow(  # noqa: E731
            ("1", file_name, "0", "2", key), file_name, key, "value", 2
        )
        self.assertEqual(
            merge_tool.selected_category(
                row("ItemType_Axe", "Name"), merge_tool.DEFAULT_CATEGORIES
            ),
            "items",
        )
        self.assertEqual(
            merge_tool.selected_category(
                row("Item_Talisman_Charm_Set_Barb_01_01", "Name"),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "items",
        )
        self.assertEqual(
            merge_tool.selected_category(
                row("Item_Talisman_Seal_Ancestral", "Name"),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "items",
        )
        self.assertEqual(
            merge_tool.selected_category(
                row("Affix_Crit", "Name_Prefix"), merge_tool.DEFAULT_CATEGORIES
            ),
            "affixes",
        )
        self.assertEqual(
            merge_tool.selected_category(
                row("ParagonGlyph_001", "Name"), merge_tool.DEFAULT_CATEGORIES
            ),
            "paragon",
        )
        self.assertEqual(
            merge_tool.selected_category(
                row("SkillTags", "Skill_Spirit_Forest_TagName"),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "skills",
        )
        self.assertEqual(
            merge_tool.selected_category(
                row("ParagonBoardUI", "NodeTypeMagic"),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "paragon",
        )
        self.assertEqual(
            merge_tool.selected_category(
                row("ParagonBoardUI", "NodeTypeLegendary"),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "paragon",
        )
        self.assertEqual(
            merge_tool.selected_category(
                row("ParagonBoardUI", "GlyphRarity_Legendary"),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "paragon",
        )
        self.assertEqual(
            merge_tool.selected_category(
                merge_tool.CsvRow(
                    ("1", "ItemLabels", "39", "2", "Glyph"),
                    "ItemLabels",
                    "Glyph",
                    "Glyph",
                    2,
                ),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "paragon",
        )
        self.assertIsNone(
            merge_tool.selected_category(
                merge_tool.CsvRow(
                    ("1", "RareNameStrings_Prefix", "23", "2", "ArmorP024"),
                    "RareNameStrings_Prefix",
                    "ArmorP024",
                    "Glyph",
                    2,
                ),
                merge_tool.DEFAULT_CATEGORIES,
            )
        )
        self.assertEqual(
            merge_tool.selected_category(
                merge_tool.CsvRow(
                    ("1", "UITestStrings", "109", "2", "Common"),
                    "UITestStrings",
                    "Common",
                    "Common Node",
                    2,
                ),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "paragon",
        )
        self.assertIsNone(
            merge_tool.selected_category(
                row("Quest_Main", "Desc"), merge_tool.DEFAULT_CATEGORIES
            )
        )

    def test_template_values_are_reordered_for_japanese(self):
        pair = merge_tool.create_template_pair(
            "+[{VALUE2}*100|1%|] {VALUE1} Damage",
            "{VALUE1}ダメージ+[{VALUE2}*100|1%|]",
        )
        self.assertIsNotNone(pair)
        pattern, replacement = pair
        self.assertRegex("+25% Fire Damage", pattern)
        self.assertEqual(replacement, "$2ダメージ+$1")

    def test_corrupt_japanese_is_rejected(self):
        _, _, reason = merge_tool.make_translation_pair("Axe", "�")
        self.assertEqual(reason, "corrupt")

    def test_affix_aliases_cover_maxroll_short_names(self):
        self.assertEqual(
            merge_tool.make_affix_alias_pairs("of Pestilence", "悪疫の"),
            [
                ("Pestilence", "悪疫"),
                ("Aspect of Pestilence", "悪疫の化身"),
            ],
        )
        self.assertEqual(
            merge_tool.make_affix_alias_pairs(
                "of Kinetic Suppression", "動的制圧の"
            ),
            [
                ("Kinetic Suppression", "動的制圧"),
                ("Aspect of Kinetic Suppression", "動的制圧の化身"),
            ],
        )

    def test_paragon_node_color_tags_are_removed(self):
        cases = (
            (
                "{c_magic}Magic Node",
                "{c_magic} マジック・ノード",
                "Magic Node",
                "マジック・ノード",
            ),
            (
                "{c_legendary}Legendary Node",
                "{c_legendary} レジェンダリー・ノード",
                "Legendary Node",
                "レジェンダリー・ノード",
            ),
            (
                "{c_legendary}Legendary Glyph{/c}",
                "{c_legendary}レジェンダリー・グリフ{/c}",
                "Legendary Glyph",
                "レジェンダリー・グリフ",
            ),
        )
        for english, japanese, expected_key, expected_value in cases:
            with self.subTest(english=english):
                key, value, reason = merge_tool.make_translation_pair(
                    english, japanese
                )
                self.assertIsNone(reason)
                self.assertEqual(key, expected_key)
                self.assertEqual(value, expected_value)
                self.assertNotIn("{", key + value)

    def test_existing_wins_and_ambiguous_new_key_is_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            en_path = root / "en.csv"
            ja_path = root / "ja.csv"
            rows_en = [
                ["1", "ItemType_Axe", "0", "10", "Name", "Axe"],
                ["2", "Affix_Test", "0", "11", "Name", "New Key"],
                ["3", "Affix_Test2", "0", "12", "Name", "New Key"],
            ]
            rows_ja = [
                ["1", "ItemType_Axe", "0", "10", "Name", "斧"],
                ["2", "Affix_Test", "0", "11", "Name", "新規"],
                ["3", "Affix_Test2", "0", "12", "Name", "別訳"],
            ]
            for path, rows in ((en_path, rows_en), (ja_path, rows_ja)):
                with path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(merge_tool.CSV_REQUIRED_COLUMNS)
                    writer.writerows(rows)

            merged, report = merge_tool.merge_csv_files(
                en_path, ja_path, {"Axe": "既存の斧"}
            )
            self.assertEqual(merged, {"Axe": "既存の斧"})
            self.assertEqual(report["counts"]["kept-existing"], 1)
            self.assertEqual(report["counts"]["conflict-key"], 1)

    def test_merge_adds_maxroll_affix_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            en_path = root / "en.csv"
            ja_path = root / "ja.csv"
            rows_en = [
                [
                    "1",
                    "Affix_legendary_spiritborn_test",
                    "0",
                    "10",
                    "Name",
                    "of Apprehension",
                ]
            ]
            rows_ja = [
                [
                    "1",
                    "Affix_legendary_spiritborn_test",
                    "0",
                    "10",
                    "Name",
                    "危惧の",
                ]
            ]
            for path, rows in ((en_path, rows_en), (ja_path, rows_ja)):
                with path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(merge_tool.CSV_REQUIRED_COLUMNS)
                    writer.writerows(rows)

            merged, _ = merge_tool.merge_csv_files(en_path, ja_path, {})
            self.assertEqual(merged["of Apprehension"], "危惧の")
            self.assertEqual(merged["Apprehension"], "危惧")
            self.assertEqual(
                merged["Aspect of Apprehension"], "危惧の化身"
            )

    def test_paragon_glyph_labels_override_rare_name_fragment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            en_path = root / "en.csv"
            ja_path = root / "ja.csv"
            rows_en = [
                ["1", "ItemLabels", "39", "10", "Glyph", "Glyph"],
                [
                    "2",
                    "RareNameStrings_Prefix",
                    "23",
                    "11",
                    "ArmorP024",
                    "Glyph",
                ],
                [
                    "3",
                    "ParagonBoardUI",
                    "111",
                    "12",
                    "GlyphRarity_Legendary",
                    "{c_legendary}Legendary Glyph{/c}",
                ],
            ]
            rows_ja = [
                ["1", "ItemLabels", "39", "10", "Glyph", "グリフ"],
                [
                    "2",
                    "RareNameStrings_Prefix",
                    "23",
                    "11",
                    "ArmorP024",
                    "グリフ刻まれし",
                ],
                [
                    "3",
                    "ParagonBoardUI",
                    "111",
                    "12",
                    "GlyphRarity_Legendary",
                    "{c_legendary}レジェンダリー・グリフ{/c}",
                ],
            ]
            for path, rows in ((en_path, rows_en), (ja_path, rows_ja)):
                with path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(merge_tool.CSV_REQUIRED_COLUMNS)
                    writer.writerows(rows)

            merged, _ = merge_tool.merge_csv_files(en_path, ja_path, {})
            self.assertEqual(merged["Glyph"], "グリフ")
            self.assertEqual(
                merged["Legendary Glyph"], "レジェンダリー・グリフ"
            )

    def test_unique_fallback_match_allows_different_csv_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            en_path = root / "en.csv"
            ja_path = root / "ja.csv"
            rows_en = [
                [
                    "1",
                    "UITestStrings",
                    "109",
                    "10",
                    "Common",
                    "Common Node",
                ]
            ]
            rows_ja = [
                [
                    "1",
                    "UITestStrings",
                    "108",
                    "10",
                    "Common",
                    "コモン・ノード",
                ]
            ]
            for path, rows in ((en_path, rows_en), (ja_path, rows_ja)):
                with path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(merge_tool.CSV_REQUIRED_COLUMNS)
                    writer.writerows(rows)

            merged, report = merge_tool.merge_csv_files(en_path, ja_path, {})
            self.assertEqual(merged, {"Common Node": "コモン・ノード"})
            self.assertEqual(report["counts"]["matched-ja-fallback"], 1)


if __name__ == "__main__":
    unittest.main()
