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
                row("ParagonBoardUI", "NodeTypeMagic"),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "paragon",
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

    def test_paragon_node_color_tags_are_removed(self):
        key, value, reason = merge_tool.make_translation_pair(
            "{c_magic}Magic Node", "{c_magic} マジック・ノード"
        )
        self.assertIsNone(reason)
        self.assertEqual(key, "Magic Node")
        self.assertEqual(value, "マジック・ノード")
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
