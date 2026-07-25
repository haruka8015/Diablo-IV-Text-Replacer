import csv
import importlib.util
import re
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
    def test_load_csv_joins_blizzard_continuation_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.csv"
            path.write_text(
                "SNO,FileName,Index,KeyHash,Key,Translation\n"
                "1,Affix_Helm_Unique_Test,0,2,Desc,Intro:\n"
                '"{icon:bullet,1.2} First bonus.",,,,,\n'
                ",,,,,\n"
                '"{icon:bullet,1.2} Second bonus.",,,,,\n',
                encoding="utf-8",
            )
            rows, _ = merge_tool.load_csv(path)
        self.assertEqual(
            rows[("1", "Affix_Helm_Unique_Test", "0", "2", "Desc")].translation,
            "Intro:\n{icon:bullet,1.2} First bonus.\n"
            "{icon:bullet,1.2} Second bonus.",
        )

    def test_category_rules_cover_requested_content(self):
        row = lambda file_name, key: merge_tool.CsvRow(  # noqa: E731
            ("1", file_name, "0", "2", key), file_name, key, "value", 2
        )
        self.assertEqual(
            merge_tool.selected_category(
                row("ModifiedLootDescriptions", "Duriel"),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "drop-sources",
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
                row("Affix_Amulet_Unique_Spiritborn_103", "Desc"),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "effects",
        )
        self.assertEqual(
            merge_tool.selected_category(
                row("Affix_legendary_spiritborn_test", "Desc"),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "effects",
        )
        self.assertEqual(
            merge_tool.selected_category(
                row("Affix_X2_Transfiguration_Mythic_Shako", "Desc"),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "effects",
        )
        self.assertEqual(
            merge_tool.selected_category(
                row("Item_Ring_Unique_Spiritborn_002", "Flavor"),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "flavors",
        )
        self.assertEqual(
            merge_tool.selected_category(
                row("Item_Rune_Effect_Spiritborn_Vortex", "RuneDescription"),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "runes",
        )
        self.assertEqual(
            merge_tool.selected_category(
                row("UIToolTips", "RunewordCompleteWithFrequency"),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "runes",
        )
        self.assertEqual(
            merge_tool.selected_category(
                row("Hero", "ItemPower"),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "tooltip-labels",
        )
        self.assertEqual(
            merge_tool.selected_category(
                row("ItemQuality", "Legendary"),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "tooltip-labels",
        )
        self.assertEqual(
            merge_tool.selected_category(
                row("H2OLayout", "TooltipRatingLabelDPS"),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "weapon-tooltip",
        )
        self.assertEqual(
            merge_tool.selected_category(
                row("UIToolTips", "WeaponSpeed_Slow1"),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "weapon-tooltip",
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
            "skill-tags",
        )
        self.assertEqual(
            merge_tool.selected_category(
                row("SkillTags", "Keyword_PestilentSwarm_Description"),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "skill-tags",
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

    def test_attribute_template_uses_numeric_capture_and_flexible_whitespace(self):
        key, value, rejection = merge_tool.make_translation_pair(
            "+[{VALUE}] Maximum Life",
            "ライフ最大値+[{VALUE}]",
        )
        self.assertIsNone(rejection)
        self.assertRegex("+1,813 Maximum Life", key)
        self.assertRegex("+1,813\nMaximum Life", key)
        self.assertEqual(value, "ライフ最大値+$1")

        key, value, rejection = merge_tool.make_translation_pair(
            "+{VALUE2} to {c_important}{VALUE1}{/c}",
            "{c_important}{VALUE1}{/c}+{VALUE2}",
        )
        self.assertIsNone(rejection)
        match = re.search(
            key,
            "+5 to Counterattack (Spiritborn Only) [4 - 5]",
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.group(2), "Counterattack")
        self.assertEqual(value, "$2+$1")

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

    def test_d4_effect_description_matches_maxroll_without_game_tags(self):
        english = (
            "{if:SF.IsMythic}{c_mythic}{/if}Your Critical Strikes cause your "
            "Poisoning on an enemy to burst, dealing "
            "{if:SF.IsMythic}{c_number}{else}{c_random}{/if}"
            "[Affix_Value_1|%|]{/c} of the total Poisoning instantly to them "
            'and {c_number}[Affix."Static Value 0"|%|]{/c} of the burst to '
            "surrounding enemies before removing the Poisoning effect from "
            "the primary target.{if:SF.IsMythic}{/c_mythic}{/if}"
        )
        japanese = (
            "{if:SF.IsMythic}{c_mythic}{/if}クリティカルヒットが敵に与えた"
            "中毒効果を炸裂させ、即座に合計中毒ダメージの"
            "{if:SF.IsMythic}{c_number}{else}{c_random}{/if}"
            "[Affix_Value_1|%|]{/c}を標的に与えると同時に、この炸裂の"
            '{c_number}[Affix."Static Value 0"|%|]{/c}のダメージを周囲の敵に'
            "与え、メインの標的から中毒効果を除去する。"
            "{if:SF.IsMythic}{/c_mythic}{/if}"
        )

        pair = merge_tool.create_d4_description_pair(english, japanese)
        self.assertIsNotNone(pair)
        pattern, replacement = pair
        maxroll_text = (
            "Your Critical Strikes cause your Poisoning on an enemy to burst, "
            "dealing [167 - 200]% of the total Poisoning instantly to them and "
            "10% of the burst to surrounding enemies before removing the "
            "Poisoning effect from the primary target."
        )
        self.assertRegex(maxroll_text, pattern)
        self.assertEqual(
            replacement,
            "クリティカルヒットが敵に与えた中毒効果を炸裂させ、即座に合計"
            "中毒ダメージの$1を標的に与えると同時に、この炸裂の$2のダメージ"
            "を周囲の敵に与え、メインの標的から中毒効果を除去する。",
        )
        self.assertNotIn("{", replacement)
        self.assertNotIn("}", replacement)

    def test_multiplicative_value_matches_maxroll_bracket_marker(self):
        pair = merge_tool.create_d4_description_pair(
            "Your Skills deal {c_random}"
            "[Affix_Value_1*100|%x|]{/c} increased damage per Spirit type "
            "they have.",
            "スキルの持つ精霊の種類1つにつき、そのダメージが{c_random}"
            "[Affix_Value_1*100|%x|]{/c}増加する。",
        )
        self.assertIsNotNone(pair)
        pattern, replacement = pair
        maxroll_text = (
            "Your Skills deal [25 - 30]%[x] increased damage per Spirit type "
            "they have."
        )
        match = re.fullmatch(pattern, maxroll_text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "[25 - 30]%[x]")
        self.assertEqual(
            replacement,
            "スキルの持つ精霊の種類1つにつき、そのダメージが$1増加する。",
        )

    def test_d4_static_mythic_effect_is_also_translated(self):
        pair = merge_tool.create_d4_description_pair(
            "{c_mythic}Enemies afflicted by more Damage over Time than "
            "remaining Life are Executed.{/c}",
            "{c_mythic}残りのライフを上回る継続ダメージを受けた敵を処刑する。{/c}",
        )
        self.assertEqual(
            pair,
            (
                r"Enemies\s+afflicted\s+by\s+more\s+Damage\s+over\s+Time"
                r"\s+than\s+remaining\s+Life\s+are\s+Executed\.",
                "残りのライフを上回る継続ダメージを受けた敵を処刑する。",
            ),
        )

    def test_multiline_effect_also_generates_rules_for_rendered_blocks(self):
        pairs = merge_tool.create_d4_description_pairs(
            "While choices match:\n"
            "{icon:bullet,1.2} Their bonuses are "
            '{c_number}[Affix.""Static Value 0""|%|]{/c} more potent.',
            "選択が同じ間:\n"
            "{icon:bullet,1.2}それらのボーナスの効力が"
            '{c_number}[Affix.""Static Value 0""|%|]{/c}上昇する。',
        )
        self.assertEqual(len(pairs), 3)
        self.assertIn(("While\\s+choices\\s+match:", "選択が同じ間:"), pairs)
        bullet_pattern, bullet_replacement = pairs[2]
        self.assertRegex("Their bonuses are 30% more potent.", bullet_pattern)
        self.assertEqual(
            bullet_replacement, "それらのボーナスの効力が$1上昇する。"
        )

    def test_flavor_uses_fallback_identity_and_strips_format_tags(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            en_path = directory / "en.csv"
            ja_path = directory / "ja.csv"
            en_path.write_text(
                "SNO,FileName,Index,KeyHash,Key,Translation\n"
                "1,Item_Ring_Unique_Test,2,3,Flavor,"
                "{c_flavor}An old tale.{/c}\n",
                encoding="utf-8",
            )
            ja_path.write_text(
                "SNO,FileName,Index,KeyHash,Key,Translation\n"
                "1,Item_Ring_Unique_Test,1,3,Flavor,"
                "{c_flavor}古い物語。{/c}\n",
                encoding="utf-8",
            )
            merged, report = merge_tool.merge_csv_files(
                en_path, ja_path, {}, categories=("flavors",)
            )

        self.assertEqual(merged[r"An\s+old\s+tale\."], "古い物語。")
        self.assertEqual(report["counts"]["matched-ja-fallback"], 1)

    def test_rune_uses_fallback_identity_when_language_indexes_differ(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            en_path = directory / "en.csv"
            ja_path = directory / "ja.csv"
            en_path.write_text(
                "SNO,FileName,Index,KeyHash,Key,Translation\n"
                "1,Item_Rune_Effect_Test,2,10,RuneOverflowBehavior,"
                "Up to 100% Increased Size\n",
                encoding="utf-8",
            )
            ja_path.write_text(
                "SNO,FileName,Index,KeyHash,Key,Translation\n"
                "1,Item_Rune_Effect_Test,3,10,RuneOverflowBehavior,"
                "範囲が最大100%拡大\n",
                encoding="utf-8",
            )
            merged, report = merge_tool.merge_csv_files(
                en_path, ja_path, {}, categories=("runes",)
            )

        self.assertEqual(
            merged[r"Up\s+to\s+100%\s+Increased\s+Size"],
            "範囲が最大100%拡大",
        )
        self.assertEqual(report["counts"]["matched-ja-fallback"], 1)

    def test_flavor_generates_maxroll_quoted_body_variant(self):
        pairs = merge_tool.create_flavor_description_pairs(
            "One touch is all it took. She looked into my eyes. -Jios, "
            "Sarat's Servant",
            "「一度触れれば十分だった。彼女は私の目を見つめた」"
            "―サラットの従僕、ジオス",
        )

        maxroll_text = (
            '"One touch is all it took. She looked into my eyes." -Jios, '
            "Sarat's Servant"
        )
        matching = [
            replacement
            for pattern, replacement in pairs
            if re.fullmatch(pattern, maxroll_text)
        ]
        self.assertEqual(
            matching,
            ["「一度触れれば十分だった。彼女は私の目を見つめた」"
             "―サラットの従僕、ジオス"],
        )

    def test_skill_tag_description_strips_formatting_and_preserves_values(self):
        pair = merge_tool.create_d4_description_pair(
            "{c_important}{b}{u}Resolve{/u}{/b}{/c} increases your Armor by "
            "[25|+%|] while active.",
            "{c_important}{b}{u}決意{/u}{/b}{/c}の発動中、荘厳度が"
            "[25|+%|]増加する。",
        )
        self.assertIsNotNone(pair)
        pattern, replacement = pair
        self.assertRegex("Resolve increases your Armor by 25% while active.", pattern)
        self.assertEqual(replacement, "決意の発動中、荘厳度が$1増加する。")
        self.assertNotIn("{", replacement)
        self.assertNotIn("}", replacement)

    def test_weapon_tooltip_rows_include_values_in_japanese_order(self):
        def csv_row(key, translation):
            return merge_tool.CsvRow(
                ("1", "H2OLayout", "1", "2", key),
                "H2OLayout",
                key,
                translation,
                2,
            )

        samples = (
            (
                "TooltipRatingLabelDPS",
                "Damage Per Second",
                "毎秒ダメージ",
                "4,146 Damage Per Second",
                "$1 毎秒ダメージ",
            ),
            (
                "TooltipRatingLabelDamagePerHit",
                "{s1} Damage per Hit",
                "命中ごとのダメージ{s1}",
                "[3,839 - 5,375] Damage per Hit",
                "命中ごとのダメージ$1",
            ),
            (
                "TooltipRatingLabelAttackSpeed",
                "{s1} Attacks per Second {s2}",
                "秒間攻撃回数{s1} {s2}",
                "0.90 Attacks per Second (Slow)",
                "秒間攻撃回数$1 $2",
            ),
        )
        for key, english, japanese, rendered, expected in samples:
            with self.subTest(key=key):
                pairs = merge_tool.create_weapon_tooltip_pairs(
                    csv_row(key, english),
                    csv_row(key, japanese),
                )
                self.assertEqual(len(pairs), 1)
                pattern, replacement = pairs[0]
                self.assertRegex(rendered, pattern)
                self.assertEqual(replacement, expected)

    def test_concatenated_rune_names_use_camel_case_boundaries(self):
        def csv_row(file_name, translation):
            return merge_tool.CsvRow(
                ("1", file_name, "1", "2", "Name"),
                file_name,
                "Name",
                translation,
                1,
            )

        pairs = []
        pairs.extend(
            merge_tool.create_rune_tooltip_pairs(
                csv_row("Item_Rune_Condition_AllSkillsOnCD", "Yul"),
                csv_row("Item_Rune_Condition_AllSkillsOnCD", "ユル"),
            )
        )
        pairs.extend(
            merge_tool.create_rune_tooltip_pairs(
                csv_row("Item_Rune_Effect_Druid_EarthenBulwark", "Que"),
                csv_row("Item_Rune_Effect_Druid_EarthenBulwark", "キュー"),
            )
        )
        rendered = "YulQue"
        for pattern, replacement in pairs:
            rendered = re.sub(pattern, replacement, rendered)
        self.assertEqual(rendered, "ユルキュー")

    def test_drop_source_pairs_include_maxroll_duriel_alias(self):
        row = lambda translation: merge_tool.CsvRow(  # noqa: E731
            (
                "2226815",
                "ModifiedLootDescriptions",
                "1",
                "4056506661",
                "Duriel",
            ),
            "ModifiedLootDescriptions",
            "Duriel",
            translation,
            1,
        )
        pairs = merge_tool.create_drop_source_pairs(
            row("Duriel"),
            row("デュリエル"),
        )
        self.assertEqual(
            pairs,
            [
                (
                    merge_tool.DROP_SOURCE_KEY_PREFIX + "Duriel",
                    "デュリエル",
                ),
                (
                    merge_tool.DROP_SOURCE_KEY_PREFIX + "King of Maggots",
                    "マゴット・キング",
                ),
            ],
        )

    def test_rune_effect_keeps_s_placeholder_as_dynamic_value(self):
        english = (
            "{c_RuneEffect}Invoke the Druid's "
            "{c_important}Earthen Bulwark{/c} Skill for "
            "{c_number}{s1}{/c} seconds, granting yourself a "
            "{c_important}{u}Barrier{/u}{/c}.{/c}"
        )
        japanese = (
            "{c_RuneEffect}{c_number}{s1}{/c}秒間、ドルイドのスキル"
            "{c_important}〈大地の護り〉を引き起こし、"
            "{c_important}{u}障壁{/u}{/c}を獲得する。{/c}"
        )
        pairs = merge_tool.create_d4_description_pairs(english, japanese)
        matching = [
            replacement
            for pattern, replacement in pairs
            if re.search(
                pattern,
                "Invoke the Druid's Earthen Bulwark Skill for "
                "3 seconds, granting yourself a Barrier.",
            )
        ]
        self.assertIn(
            "$1秒間、ドルイドのスキル〈大地の護り〉を引き起こし、"
            "障壁を獲得する。",
            matching,
        )

    def test_runeword_frequency_matches_singular_and_plural(self):
        row = lambda translation: merge_tool.CsvRow(  # noqa: E731
            (
                "4280",
                "UIToolTips",
                "224",
                "946958237",
                "RunewordCompleteWithFrequency",
            ),
            "UIToolTips",
            "RunewordCompleteWithFrequency",
            translation,
            1,
        )
        pairs = merge_tool.create_rune_tooltip_pairs(
            row("{s1}([RunewordFrequency()] |4time:times;)"),
            row("{s1}（これを[RunewordFrequency()]回行う）"),
        )
        pattern, replacement = pairs[0]
        self.assertRegex("(6 times)", pattern)
        self.assertRegex("(1 time)", pattern)
        self.assertEqual(replacement, "（これを$1回行う）")

    def test_evade_cooldown_attribute_expands_plural_control_text(self):
        def csv_row(translation):
            return merge_tool.CsvRow(
                (
                    "4080",
                    "AttributeDescriptions",
                    "229",
                    "3688852659",
                    "Evade_Reduce_Cooldown_On_Attack",
                ),
                "AttributeDescriptions",
                "Evade_Reduce_Cooldown_On_Attack",
                translation,
                1,
            )

        pairs = merge_tool.create_attribute_tooltip_pairs(
            csv_row(
                "Attacks Reduce Evade's Cooldown by "
                "[{VALUE}|1|] |4Second:Seconds;"
            ),
            csv_row(
                "攻撃すると回避のクールダウンが[{VALUE}|1|]秒減少"
            ),
        )
        self.assertIsNotNone(pairs)
        self.assertEqual(len(pairs), 1)
        pattern, replacement = pairs[0]
        self.assertRegex(
            "Attacks Reduce Evade's Cooldown by 1.9 Seconds",
            pattern,
        )
        self.assertRegex(
            "Attacks Reduce Evade's Cooldown by 1 Second",
            pattern,
        )
        self.assertEqual(
            replacement,
            "攻撃すると回避のクールダウンが$1秒減少",
        )

    def test_evade_cooldown_attribute_pair_is_kept_during_merge(self):
        header = "SNO,FileName,Index,KeyHash,Key,Translation\n"
        english = (
            "4080,AttributeDescriptions,229,3688852659,"
            "Evade_Reduce_Cooldown_On_Attack,"
            "Attacks Reduce Evade's Cooldown by "
            "[{VALUE}|1|] |4Second:Seconds;\n"
        )
        japanese = (
            "4080,AttributeDescriptions,229,3688852659,"
            "Evade_Reduce_Cooldown_On_Attack,"
            "攻撃すると回避のクールダウンが[{VALUE}|1|]秒減少\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            en_path = directory / "en.csv"
            ja_path = directory / "ja.csv"
            en_path.write_text(header + english, encoding="utf-8")
            ja_path.write_text(header + japanese, encoding="utf-8")
            merged, _ = merge_tool.merge_csv_files(
                en_path,
                ja_path,
                {},
                categories=("attributes",),
            )

        matching = [
            replacement
            for pattern, replacement in merged.items()
            if re.search(
                pattern,
                "Attacks Reduce Evade's Cooldown by 1.9 Seconds",
            )
        ]
        self.assertEqual(
            matching,
            ["攻撃すると回避のクールダウンが$1秒減少"],
        )

    def test_effect_wording_conflict_keeps_first_game_variant(self):
        rows = (
            "SNO,FileName,Index,KeyHash,Key,Translation\n"
            "1,Affix_Helm_Unique_Current,0,2,Desc,Skills gain power.\n"
            "2,Affix_Helm_Unique_Charm,0,3,Desc,Skills gain power.\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            en_path = directory / "en.csv"
            ja_path = directory / "ja.csv"
            en_path.write_text(rows, encoding="utf-8")
            ja_path.write_text(
                rows.replace(
                    "Skills gain power.",
                    "スキルが力を得る。",
                    1,
                ).replace(
                    "Skills gain power.",
                    "スキルの力が増す。",
                    1,
                ),
                encoding="utf-8",
            )
            merged, report = merge_tool.merge_csv_files(
                en_path, ja_path, {}, categories=("effects",)
            )
        self.assertEqual(
            merged[r"Skills\s+gain\s+power\."], "スキルが力を得る。"
        )
        self.assertEqual(
            report["counts"]["effect-conflict-kept-first"], 1
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
