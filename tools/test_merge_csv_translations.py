import csv
import contextlib
import importlib.util
import io
import json
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
    def test_resource_regeneration_expands_csv_resource_names(self):
        fixture = Path(__file__).parent / "fixtures"
        merged, _ = merge_tool.merge_csv_files(
            fixture / "s15_resource_regeneration_en.csv",
            fixture / "s15_resource_regeneration_ja.csv", {}
        )
        self.assertEqual(merged[r"Wrath\s+Regeneration"], "憤怒回復量")
        self.assertEqual(merged[r"Wrath\s+Regeneration\s+per\s+Second"], "毎秒の憤怒回復量")
        for raw, expected in [("+8 Wrath Regeneration", "憤怒回復量+8"),
                              ("+8.5 Wrath Regeneration", "憤怒回復量+8.5"),
                              ("10% Wrath Regeneration per Second", "毎秒の憤怒回復量10%")]:
            matches = []
            for pattern, value in merged.items():
                match = re.fullmatch(pattern, raw)
                if match and "(.*?)" not in pattern:
                    matches.append(re.sub(r"\$(\d+)", lambda m: match.group(int(m[1])), value))
            self.assertIn(expected, matches)

    def test_seal_effects_set_names_and_slot_counts_are_imported(self):
        fixture = Path(__file__).parent / "fixtures"
        merged, report = merge_tool.merge_csv_files(
            fixture / "s15_seal_en.csv", fixture / "s15_seal_ja.csv", {}
        )
        self.assertEqual(merged["Flesh of Abaddon"], "悪鬼の肉塊")
        cases = [
            ("Unlocks 7 Charm Slots", "チャームスロットを7個解放"),
            ("+1 Charm Slot", "チャームスロット+1"),
            ("+2 Charm Slot", "チャームスロット+2"),
            ("+15% Damage Reduction while in Demonform", "悪魔形態中のダメージ減少率+15%"),
            ("Reduces the number of Charms needed for Set bonuses by 1 (to a minimum of 2).",
             "セット・ボーナスに必要なチャーム数を1減らす（最低2個）。"),
        ]
        for english, japanese in cases:
            matched = []
            for pattern, replacement in merged.items():
                match = re.fullmatch(pattern, english)
                if match:
                    self.assertNotIn("(.*?)", pattern)
                    matched.append(re.sub(r"\$(\d+)", lambda m: match.group(int(m[1])), replacement))
            self.assertIn(japanese, matched, english)

    def soul_splinter_fixture(self):
        fixture = Path(__file__).parent / "fixtures"
        return merge_tool.merge_csv_files(fixture / "s15_soul_splinters_en.csv",
                                          fixture / "s15_soul_splinters_ja.csv", {})

    def test_soul_splinter_names_and_flavors_are_selected(self):
        merged, report = self.soul_splinter_fixture()
        self.assertEqual(report["selected_by_category"]["items"], 35)
        self.assertEqual(report["selected_by_category"]["flavors"], 35)
        self.assertEqual(merged["Abyssal Splinter of the Mother"], "母の破片（深淵）")
        self.assertEqual(merged["Abyssal Splinter of Sin"], "罪悪の破片（深淵）")
        self.assertEqual(merged["Abyssal Splinter of Pain"], "苦痛の破片（深淵）")
        self.assertGreaterEqual(report["counts"]["matched-ja-fallback"], 3)
        raw = ('"Break the chains, and discover who you were meant to be. '
               'Break the chains, and be beautiful in Sin."\n- Lilith, The Blessed Mother')
        matches = [value for pattern, value in merged.items() if re.fullmatch(pattern, raw)]
        self.assertEqual(matches, [
            '「鎖を断ち切り、お前の真の姿を見つけよ。鎖を断ち切り、罪の中で美しくあれ」\n―祝福されし母リリス'])
        self.assertTrue(any(re.fullmatch(pattern, "Can be inserted into equipment with sockets.")
                            and value == "ソケット付きの装備にはめ込み可能。"
                            for pattern, value in merged.items()))

    def test_soul_splinter_stat_numbers_are_not_split(self):
        merged, _ = self.soul_splinter_fixture()
        for number in ("4375", "4,375", "437.5", "1750", "250"):
            with self.subTest(number=number):
                matches = [(re.fullmatch(pattern, f"+{number} Physical Resistance"), value)
                           for pattern, value in merged.items()]
                matches = [(match, value) for match, value in matches if match]
                self.assertEqual(len(matches), 1)
                match, value = matches[0]
                self.assertEqual(match.groups(), (number,))
                self.assertEqual(value, "物理耐性+$1")

    def socketable_pair(self, name):
        fixture = Path(__file__).parent / "fixtures"
        en_rows, _ = merge_tool.load_csv(fixture / "s15_socketables_en.csv")
        ja_rows, _ = merge_tool.load_csv(fixture / "s15_socketables_ja.csv")
        row = next(row for row in en_rows.values() if row.key == "S15_Socketable_" + name)
        return merge_tool.create_attribute_tooltip_pairs(row, ja_rows[row.identity])

    def test_black_soulstone_matches_screenshot_and_preserves_values(self):
        pairs = self.socketable_pair("BlackSoulstone")
        self.assertEqual(len(pairs), 1)
        pattern, replacement = pairs[0]
        for damage in ("2.5%[x]", "1.5%", "[1.5 - 2.5]%[x]"):
            with self.subTest(damage=damage):
                text = (
                    "Your kills absorb a soul for 10 seconds. Each soul increases "
                    f"your damage by {damage} but increases your damage taken by 1%. "
                    "This effect stacks up to 200 times, but does not refresh."
                )
                match = re.fullmatch(pattern, text)
                self.assertIsNotNone(match)
                self.assertEqual(match.groups(), ("10", damage, "1%", "200"))
                translated = re.sub(r"\$(\d+)", lambda token: match.group(int(token[1])), replacement)
                self.assertEqual(translated,
                    "敵をキルした時に10秒間にわたり魂を吸収する。魂を吸収するごとに"
                    f"与えるダメージが{damage}増加するが、受けるダメージも1%増加する。"
                    "この効果は最大200回まで蓄積するが、効果時間はリセットされない。")

    def test_socketable_skarn_reorders_numeric_references(self):
        pattern, replacement = self.socketable_pair("Skarn")[0]
        match = re.fullmatch(pattern,
            "Killing an Elite Pack increases Monster Power by 2 and Experience gained by 30% for 60 seconds.")
        self.assertIsNotNone(match)
        self.assertEqual(match.groups(), ("2", "30%", "60"))
        self.assertEqual(re.sub(r"\$(\d+)", lambda token: match.group(int(token[1])), replacement),
            "エリートモンスターの群れを倒すと、60秒間にわたりモンスターパワーが2上昇し、獲得経験値量が30%増加する。")

    def test_azmodan_known_bad_source_is_corrected_and_additive_marker_is_preserved(self):
        pattern, replacement = self.socketable_pair("Azmodan")[0]
        for life in ("50%[+]", "50%", "[25 - 50]%[+]"):
            match = re.fullmatch(pattern,
                f"You gain {life} Maximum Life, but your Maximum Primary Resource is reduced by 30%.")
            self.assertIsNotNone(match)
            self.assertEqual(match.groups(), (life, "30%"))
            self.assertEqual(re.sub(r"\$(\d+)", lambda token: match.group(int(token[1])), replacement),
                f"ライフ最大値が{life}増加するが、プライマリリソース最大値が30%減少する。")

    def test_azmodan_correction_does_not_override_changed_sources(self):
        from dataclasses import replace
        fixture = Path(__file__).parent / "fixtures"
        en, _ = merge_tool.load_csv(fixture / "s15_socketables_en.csv")
        ja, _ = merge_tool.load_csv(fixture / "s15_socketables_ja.csv")
        row = next(row for row in en.values() if row.key == "S15_Socketable_Azmodan")
        self.assertEqual(merge_tool.create_attribute_tooltip_pairs(
            replace(row, translation=row.translation.replace("Maximum Life", "Armor")), ja[row.identity]), [])
        self.assertEqual(merge_tool.create_attribute_tooltip_pairs(
            row, replace(ja[row.identity], translation=ja[row.identity].translation + "別の効果")), [])
        corrected = replace(ja[row.identity], translation=(
            '{c_unique}最大ライフ+[{VALUE2}|%+|]、最大リソースが'
            '[PowerTag.S15_Socketable_Azmodan."Script Formula 1" * 100|%|]減少。{/c}'))
        self.assertEqual(merge_tool.create_attribute_tooltip_pairs(row, corrected)[0][1],
                         "最大ライフ+$1、最大リソースが$2減少。")

    def test_socketable_import_has_only_numeric_capture_references(self):
        fixture = Path(__file__).parent / "fixtures"
        merged, report = merge_tool.merge_csv_files(
            fixture / "s15_socketables_en.csv", fixture / "s15_socketables_ja.csv", {})
        self.assertEqual(len(merged), 9)
        self.assertEqual(report["added_by_category"], {"attributes": 9})
        self.assertEqual(merged[r"Monster\s+Power"], "モンスターパワー")
        self.assertEqual(report["counts"].get("rejected:unsupported-attribute", 0), 0)
        for pattern, value in merged.items():
            self.assertNotIn("D4T_", pattern)
            self.assertNotIn("PowerTag", pattern)
            self.assertNotIn("{", value)
            self.assertNotIn("}", value)
            self.assertNotIn("(.*?)", pattern)
            self.assertTrue(all(int(n) <= re.compile(pattern).groups
                                for n in re.findall(r"\$(\d+)", value)))

    def test_skarn_term_alias_requires_unambiguous_emphasis(self):
        from dataclasses import replace
        fixture = Path(__file__).parent / "fixtures"
        en, _ = merge_tool.load_csv(fixture / "s15_socketables_en.csv")
        ja, _ = merge_tool.load_csv(fixture / "s15_socketables_ja.csv")
        row = next(row for row in en.values() if row.key == "S15_Socketable_Skarn")
        japanese = ja[row.identity]
        for changed in [
            replace(japanese, translation=japanese.translation.replace("{c_important}", "")),
            replace(japanese, translation=japanese.translation + "{c_important}別の用語{/c}"),
        ]:
            pairs = merge_tool.create_attribute_tooltip_pairs(row, changed)
            self.assertNotIn(r"Monster\s+Power", dict(pairs))

    def test_skill_tag_wins_over_random_item_name_in_either_csv_order(self):
        for reverse in (False, True):
            with self.subTest(reverse=reverse), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                rows = [("RareNameStrings_Suffix_Weapon_Bow", "Bow003", "鷲"),
                        ("SkillTags", "Skill_Spirit_Sky_TagName", "イーグル")]
                if reverse:
                    rows.reverse()
                for language in ("en", "ja"):
                    with (root / (language + ".csv")).open("w", encoding="utf-8", newline="") as handle:
                        writer = csv.writer(handle)
                        writer.writerow(merge_tool.CSV_REQUIRED_COLUMNS)
                        for index, (file_name, key, value) in enumerate(rows):
                            writer.writerow([str(index), file_name, "0", str(index), key,
                                             "Eagle" if language == "en" else value])
                merged, report = merge_tool.merge_csv_files(
                    root / "en.csv", root / "ja.csv", {"Eagle": "以前の訳"}, overwrite_existing=True)
                self.assertEqual(merged, {"Eagle": "イーグル"})
                self.assertEqual(report["counts"]["skill-tag-preferred-over-rare-name"], 1)

    def test_season_update_overwrites_existing_and_includes_item_flavor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = {"Enigma": "旧名", r"An\s+old\s+tale\.": "旧フレーバー",
                        "Web-only label": "サイト専用"}
            output = root / "translations.json"
            output.write_text(json.dumps(existing), encoding="utf-8")
            before = output.read_bytes()
            rows = [
                ("Item_Runeword_Enigma", "Name", "Enigma", "エニグマ"),
                ("Item_Runeword_Enigma", "Flavor", "An old tale.", "新フレーバー"),
                ("Item_Talisman_Charm_Set_Barb_01_01", "Flavor", "A set tale.", "セットの物語"),
                ("Quest_Test", "Name", "Quest tale", "クエスト"),
                ("Conv_Test", "Text", "NPC tale", "会話"),
            ]
            for language, column in (("en", 2), ("ja", 3)):
                with (root / (language + ".csv")).open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(merge_tool.CSV_REQUIRED_COLUMNS)
                    for index, row in enumerate(rows):
                        writer.writerow([str(index), row[0], "0", str(index), row[1], row[column]])
            report_path = root / "report.json"
            args = [str(output), "--en", str(root / "en.csv"), "--ja", str(root / "ja.csv"),
                    "--overwrite-existing", "--report", str(report_path)]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(merge_tool.main(args + ["--dry-run"]), 0)
                self.assertEqual(output.read_bytes(), before)
                self.assertEqual(merge_tool.main(args), 0)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, {"Enigma": "エニグマ", r"An\s+old\s+tale\.": "新フレーバー",
                                      r"A\s+set\s+tale\.": "セットの物語", "Web-only label": "サイト専用"})
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["counts"]["added"], 1)
            self.assertEqual(report["counts"]["overwritten"], 2)
            self.assertEqual(report["added_by_category"], {"flavors": 1})
            self.assertEqual(report["overwritten_by_category"], {"items": 1, "flavors": 1})
            self.assertEqual(len(report["overwritten_rules"]), 2)

    def test_season_rule_comparison_separates_backlog_and_translation_changes(self):
        result = merge_tool.compare_season_rules(
            {"old": "旧", "changed": "以前", "removed": "削除"},
            {"old": "旧", "changed": "現在", "new": "新", "covered": "登録済"},
            {"changed": "手動訳", "covered": "登録済"},
        )
        self.assertEqual(result["new_rules_missing_from_dictionary"], 1)
        self.assertEqual(result["previous_rules_missing_from_dictionary"], 1)
        self.assertEqual(result["removed_rule_keys"], ["removed"])
        self.assertEqual(result["changed_translations"], [
            {"key": "changed", "previous": "以前", "current": "現在"}])

    def test_gameplay_additions_exclude_story_and_enemy_skill_descriptions(self):
        cases = [
            ("Item_Runeword_Enigma", "Name", "items"),
            ("Item_Talisman_Charm_Uniq_Generic_001", "Name", "items"),
            ("Affix_Runeword_Grief", "Desc", "effects"),
            ("Affix_Talisman_SetPower_Warlock04_01", "Desc", "effects"),
            ("Affix_HellfireTorch_Barb_01", "Desc", "effects"),
            ("Affix_x1_unique_Test", "Desc", "effects"),
            ("Power_S15_TriadA_Player_FireStomp", "desc", "skills"),
            ("Power_S15_Opal_Boss_OverrideSkill", "desc", None),
            ("Conv_Test", "Name", None),
            ("Quest_Test", "Name", None),
            ("Item_Boots_Cosmetic_Test", "Name", None),
        ]
        for file_name, key, expected in cases:
            with self.subTest(file_name=file_name):
                row = merge_tool.CsvRow(("1", file_name, "0", "2", key),
                                       file_name, key, "value", 2)
                self.assertEqual(merge_tool.selected_category(
                    row, merge_tool.DEFAULT_CATEGORIES), expected)

    def test_item_index_fallback_requires_unique_rows_in_both_languages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def write(language, indexes, text):
                path = root / (language + ".csv")
                with path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(merge_tool.CSV_REQUIRED_COLUMNS)
                    for index in indexes:
                        writer.writerow(["1", "Item_Runeword_Enigma", index,
                                         "2", "Name", text])
                return path
            for en_indexes, ja_indexes, expected in [
                ([0], [1], {"Enigma": "謎"}),
                ([0, 2], [1], {}),
                ([0], [1, 2], {}),
            ]:
                with self.subTest(en=en_indexes, ja=ja_indexes):
                    merged, _ = merge_tool.merge_csv_files(
                        write("en", en_indexes, "Enigma"),
                        write("ja", ja_indexes, "謎"), {})
                    self.assertEqual(merged, expected)

    def test_new_equipment_effects_preserve_numeric_captures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for language, value in [
                ("en", "Gain [Affix_Value_1*100|%|] Armor."),
                ("ja", "防御力が[Affix_Value_1*100|%|]増加する。"),
            ]:
                with (root / (language + ".csv")).open(
                    "w", encoding="utf-8", newline=""
                ) as handle:
                    writer = csv.writer(handle)
                    writer.writerow(merge_tool.CSV_REQUIRED_COLUMNS)
                    writer.writerow(["1", "Affix_Runeword_Grief", "0", "2", "Desc", value])
            merged, report = merge_tool.merge_csv_files(root / "en.csv", root / "ja.csv", {})
            pattern = next(key for key in merged if re.fullmatch(key, "Gain 25% Armor."))
            self.assertEqual(re.fullmatch(pattern, "Gain 25% Armor.").group(1), "25%")
            self.assertEqual(merged[pattern], "防御力が$1増加する。")
            self.assertEqual(report["added_rules"][0]["category"], "effects")

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
        for file_name, key in (
            ("Power_Paragon_Spiritborn_Legendary_007", "desc"),
            ("Power_ParagonGlyph_001", "desc"),
            ("ParagonGlyphAffix_DamageBonus_Intelligence_Generic", "Desc"),
            ("ParagonBoardUI", "ThresholdBonusAttribute"),
            ("ParagonBoardUI", "RequirementsNotMet"),
            ("ParagonBoardUI", "GlyphLevel"),
            ("ParagonBoardUI", "GlyphSocketed"),
            ("ParagonBoardUI", "GlyphSizeName"),
            ("ParagonBoardUI", "GlyphRadiusUpgrade"),
        ):
            with self.subTest(file_name=file_name, key=key):
                self.assertEqual(
                    merge_tool.selected_category(
                        row(file_name, key), merge_tool.DEFAULT_CATEGORIES
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
        for key in ("desc", "rankup_desc", "Mod6_Description"):
            with self.subTest(skill_power_key=key):
                self.assertEqual(
                    merge_tool.selected_category(
                        row("Power_Spiritborn_Jaguar_Potency", key),
                        merge_tool.DEFAULT_CATEGORIES,
                    ),
                    "skills",
                )
        self.assertEqual(
            merge_tool.selected_category(
                row("SkillTree_SpiritBorn", "Modifiers"),
                merge_tool.DEFAULT_CATEGORIES,
            ),
            "skills",
        )
        self.assertIsNone(
            merge_tool.selected_category(
                row("Power_NPC_Test", "desc"),
                merge_tool.DEFAULT_CATEGORIES,
            )
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

    def test_maxroll_paragon_attribute_aliases_reorder_requirement_values(self):
        def csv_row(key, translation):
            return merge_tool.CsvRow(
                ("4080", "AttributeDescriptions", "1", "1", key),
                "AttributeDescriptions",
                key,
                translation,
                2,
            )

        key, value, rejection = merge_tool.make_translation_pair(
            "[{VALUE}|~|] Intelligence",
            "知力[{VALUE}|~|]",
        )
        self.assertIsNone(rejection)
        aliases = merge_tool.make_attribute_alias_pairs(
            csv_row("Intelligence", "[{VALUE}|~|] Intelligence"),
            csv_row("Intelligence", "知力[{VALUE}|~|]"),
            key,
            value,
        )
        requirement_pattern, requirement_replacement = aliases[0]
        match = re.fullmatch(
            requirement_pattern,
            "+303 / 435 Intelligence",
            flags=re.IGNORECASE,
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.groups(), ("303", "435"))
        self.assertEqual(requirement_replacement, "$1 / 知力+$2")
        glyph_pattern, glyph_replacement = aliases[1]
        glyph_match = re.fullmatch(
            glyph_pattern,
            "+69 / Intelligence +25",
            flags=re.IGNORECASE,
        )
        self.assertIsNotNone(glyph_match)
        self.assertEqual(glyph_match.groups(), ("69", "25"))
        self.assertEqual(glyph_replacement, "$1 / 知力+$2")

        key, value, rejection = merge_tool.make_translation_pair(
            "[{VALUE}*100|1%|] Maximum Life",
            "ライフ最大値の[{VALUE}*100|1%|]",
        )
        self.assertIsNone(rejection)
        aliases = merge_tool.make_attribute_alias_pairs(
            csv_row(
                "Hitpoints_Max_Percent_Bonus",
                "[{VALUE}*100|1%|] Maximum Life",
            ),
            csv_row(
                "Hitpoints_Max_Percent_Bonus",
                "ライフ最大値の[{VALUE}*100|1%|]",
            ),
            key,
            value,
        )
        max_life_pattern, max_life_replacement = aliases[0]
        self.assertRegex("4.0% Maximum Life", max_life_pattern)
        self.assertEqual(max_life_replacement, "ライフ最大値の$1")

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

    def test_paragon_raw_sf_values_and_plural_tokens_match_maxroll(self):
        self.assertEqual(
            merge_tool.D4_VALUE_TOKEN_RE.findall("{SF_4} for {SF_3}"),
            ["{SF_4}", "{SF_3}"],
        )
        self.assertEqual(
            merge_tool.D4_FORMAT_TAG_RE.sub(
                "", "{c_number}{SF_4}{/c}"
            ),
            "{SF_4}",
        )
        prodigy_pair = merge_tool.create_d4_description_pair(
            "Every {c_number}3rd{/c} consecutive Cast of the same "
            "{c_important}Basic{/c} Skill increases all purchased Skills' "
            "Ranks by {c_number}{SF_4}{/c} for "
            "{c_number}{SF_3}{/c} seconds.",
            "同じ{c_important}基本{/c}スキルの連続使用"
            "{c_number}3回目{/c}ごとに、{c_number}{SF_3}{/c}秒間"
            "すべての購入済みスキルのランクが"
            "{c_number}{SF_4}{/c}上昇する。",
        )
        self.assertIsNotNone(prodigy_pair)
        prodigy_pattern, prodigy_replacement = prodigy_pair
        self.assertRegex(
            "Every 3rd consecutive Cast of the same Basic Skill increases "
            "all purchased Skills' Ranks by 5 for 5 seconds.",
            prodigy_pattern,
        )
        self.assertEqual(
            prodigy_replacement,
            "同じ基本スキルの連続使用3回目ごとに、$2秒間"
            "すべての購入済みスキルのランクが$1上昇する。",
        )

        drive_pair = merge_tool.create_d4_description_pair(
            "Gain {c_number}[{SF_4}|+|]{/c} additional "
            "{c_important}Evade{/c} |4Charge:Charges;. After moving "
            "{c_number}[SF_3]{/c} meters, you deal "
            "{c_number}[SF_2*100|1%x|]{/c} increased damage for "
            "{c_number}[SF_1]{/c} seconds.",
            "{c_important}回避{/c}のチャージを追加で"
            "{c_number}[{SF_4}|+|]{/c}獲得する。"
            "{c_number}[SF_3]{/c}メートル移動後に"
            "{c_number}[SF_1]{/c}秒間ダメージが"
            "{c_number}[SF_2*100|1%x|]{/c}増加する。",
        )
        self.assertIsNotNone(drive_pair)
        drive_pattern, drive_replacement = drive_pair
        self.assertRegex(
            "Gain 1+ additional Evade Charge. After moving 10 meters, "
            "you deal 6.0%x increased damage for 5 seconds.",
            drive_pattern,
        )
        self.assertRegex(
            "Gain 1+ additional Evade Charges. After moving 10 meters, "
            "you deal 6.0%x increased damage for 5 seconds.",
            drive_pattern,
        )
        self.assertEqual(
            drive_replacement,
            "回避のチャージを追加で$1獲得する。$2メートル移動後に"
            "$4秒間ダメージが$3増加する。",
        )

    def test_template_allows_missing_space_after_maxroll_span(self):
        pair = merge_tool.create_template_pair(
            "Bonus: Another {s1} if requirements met:",
            "ボーナス: 条件を満たしている場合、{s1}を1つ追加:",
        )
        self.assertIsNotNone(pair)
        pattern, replacement = pair
        self.assertRegex(
            "Bonus: Another Elite Damageif requirements met:",
            pattern,
        )
        self.assertEqual(
            replacement,
            "ボーナス: 条件を満たしている場合、$1を1つ追加:",
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

    def test_skill_tooltip_payload_matches_live_maxroll_value_markup(self):
        pair = merge_tool.create_d4_description_pair(
            "{/if}Smash down next to you with devastating force, creating "
            "{c_number}2{/c} shockwaves on either side that overlap and each "
            "deal {c_number}{payload:IMPACT}{/c} damage.",
            "{/if}自身のそばを強烈に叩きつけ、両側に{c_number}2{/c}つの"
            "衝撃波を発生させる。衝撃波は重なり合う部分があり、それぞれが"
            "{c_number}{payload:IMPACT}{/c}のダメージを与える。",
        )
        self.assertIsNotNone(pair)
        pattern, replacement = pair
        rendered = (
            "Smash down next to you with devastating force, creating 2 "
            "shockwaves on either side that overlap and each deal "
            "2094979 [262.5%] damage."
        )
        match = re.fullmatch(pattern, rendered)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "2094979 [262.5%]")
        self.assertEqual(
            replacement,
            "自身のそばを強烈に叩きつけ、両側に2つの衝撃波を発生させる。"
            "衝撃波は重なり合う部分があり、それぞれが$1のダメージを与える。",
        )

    def test_skill_tooltip_payload_keeps_maxroll_damage_annotation(self):
        pair = merge_tool.create_d4_description_pair(
            "Slash a short distance through an enemy, striking all enemies "
            "along the way twice for a total of "
            "{c_number}{payload:IMPACT_TOOLTIP}{/c} total damage.",
            "敵をすり抜けるように短い距離を切り裂き、進路上のすべての敵を"
            "2回攻撃して合計{c_number}{payload:IMPACT_TOOLTIP}{/c}の"
            "ダメージを与える。",
        )
        self.assertIsNotNone(pair)
        pattern, replacement = pair
        rendered = (
            "Slash a short distance through an enemy, striking all enemies "
            "along the way twice for a total of 160% x [Damage] total damage."
        )
        match = re.fullmatch(pattern, rendered)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "160% x [Damage]")
        self.assertIn("$1", replacement)

    def test_skill_modifier_conditionals_create_each_rendered_branch(self):
        pairs = merge_tool.create_d4_description_pairs(
            "You gain {if:SF_26}{c_number}{SF_18}{/c} Vigor per second "
            "while you have {c_important}Withering Fist's{/c} "
            "{c_important}{u}Barrier{/u}{/c}."
            "{else}{c_number}{SF_16}{/c} Vigor per second for every "
            "Nearby enemy Poisoned by {c_important}Withering Fist{/c}, "
            "up to {c_number}{SF_17}{/c}.{/if}",
            "{if:SF_26}{c_important}〈萎縮を呼ぶ拳〉{/c}の"
            "{c_important}{u}障壁{/u}{/c}が発動している間、"
            "活力が毎秒{c_number}{SF_18}{/c}付与される。"
            "{else}{c_important}〈萎縮を呼ぶ拳〉{/c}による毒を"
            "受けている付近の敵1体ごとに、活力が毎秒"
            "{c_number}{SF_16}{/c}付与される。最大"
            "{c_number}{SF_17}{/c}。{/if}",
        )
        rendered_branches = (
            "You gain 4 Vigor per second while you have "
            "Withering Fist's Barrier.",
            "You gain 5 Vigor per second for every Nearby enemy Poisoned by "
            "Withering Fist, up to 15.",
        )
        for rendered in rendered_branches:
            with self.subTest(rendered=rendered):
                self.assertTrue(
                    any(re.fullmatch(pattern, rendered) for pattern, _ in pairs)
                )

    def test_skill_conditionals_create_rules_for_each_rendered_line(self):
        pairs = merge_tool.create_d4_description_pairs(
            "{if:RESOURCE_COST}Costs 10 Vigor.{else}Cooldown: 15 seconds."
            "{/if}\n"
            "Smash enemies in front of you.\n"
            "When attacked, you have a 5% chance to "
            "{if:GAIN_VIGOR}gain 10 Vigor.{else}reset Payback's Cooldown."
            "{/if}",
            "{if:RESOURCE_COST}活力を10消費する。{else}クールダウン: 15秒。"
            "{/if}\n"
            "前方の敵を強打する。\n"
            "攻撃を受けると、5%の確率で"
            "{if:GAIN_VIGOR}活力を10得る。{else}〈仕返し〉のクールダウンが"
            "リセットされる。{/if}",
        )

        rendered_line = (
            "When attacked, you have a 5% chance to reset Payback's Cooldown."
        )
        matches = [
            replacement
            for pattern, replacement in pairs
            if re.fullmatch(pattern, rendered_line)
        ]
        self.assertEqual(
            matches,
            ["攻撃を受けると、5%の確率で〈仕返し〉のクールダウンが"
             "リセットされる。"],
        )

    def test_skill_value_markers_can_differ_between_language_csvs(self):
        pair = merge_tool.create_d4_description_pair(
            "Passive: Whenever you receive Healing, gain "
            "[{SF_23}*100|%+|] Critical Strike Damage until your next "
            "Critical Strike, up to [{SF_24}*100|%+|].",
            "パッシブ: 回復効果を受けると、次のクリティカルヒットが発生するまで"
            "クリティカルヒットダメージが[{SF_23}*100|%+|]増加する。"
            "最大[{SF_24}*100|%|]。",
        )

        self.assertIsNotNone(pair)
        pattern, replacement = pair
        rendered = (
            "Passive: Whenever you receive Healing, gain 25% Critical Strike "
            "Damage until your next Critical Strike, up to 200%."
        )
        self.assertRegex(rendered, pattern)
        self.assertEqual(
            replacement,
            "パッシブ: 回復効果を受けると、次のクリティカルヒットが発生するまで"
            "クリティカルヒットダメージが$1増加する。最大$2。",
        )

    def test_value_only_description_fragments_are_rejected(self):
        self.assertIsNone(
            merge_tool.create_d4_description_pair(
                "[{SF_1}|%|].",
                "[{SF_1}|%|]増加する。",
            )
        )
        self.assertIsNone(
            merge_tool.create_d4_description_pair(
                "[{SF_1}][{SF_2}]",
                "[{SF_1}][{SF_2}]",
            )
        )

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

    def test_mot_description_preserves_shadow_count_and_renders_plural(self):
        def row(text):
            return merge_tool.CsvRow(
                ("2089934", "Item_Rune_Effect_Rogue_DarkShroud", "0", "3679068894", "RuneDescription"),
                "Item_Rune_Effect_Rogue_DarkShroud", "RuneDescription", text, 1,
            )

        pairs = merge_tool.create_rune_tooltip_pairs(
            row("{c_RuneEffect}Gain {c_number}{s1}{/c} |4 shadow:shadows;, from the Rogue's {c_important}Dark Shroud{/c} Skill, reducing damage taken per shadow.{/c}"),
            row("{c_RuneEffect}ローグのスキル{c_important}〈ダークシュラウド〉{/c}の影を{c_number}{s1}{/c}個獲得し、影1つごとに受けるダメージを減少させる。{/c}"),
        )
        for count, noun in [("1", "shadow"), ("2", "shadows"), ("5", "shadows")]:
            text = f"Gain {count} {noun}, from the Rogue's Dark Shroud Skill, reducing damage taken per shadow."
            matches = [(re.fullmatch(key, text), value) for key, value in pairs]
            matches = [(match, value) for match, value in matches if match]
            self.assertTrue(matches)
            for match, value in matches:
                self.assertEqual(match.groups(), (count,))
                self.assertEqual(value, "ローグのスキル〈ダークシュラウド〉の影を$1個獲得し、影1つごとに受けるダメージを減少させる。")

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

    def test_paragon_tooltip_effects_and_ui_templates_are_generated(self):
        rows_en = [
            [
                "1",
                "Power_Paragon_Spiritborn_Legendary_007",
                "1",
                "10",
                "desc",
                "You deal bonus damage equal to "
                "{c_number}[SF_1 * 100|1x%|]{/c} of all your bonuses to "
                "Damage with Physical, Fire, Lightning, Cold, Poison, and "
                "Shadow combined, up to "
                "{c_number}[SF_0 * 100|x%|]{/c} total.",
            ],
            [
                "2",
                "ParagonBoardUI",
                "70",
                "11",
                "ThresholdBonusAttribute",
                "{c_label}Bonus:{/c} Another {s1} if requirements met:",
            ],
            [
                "3",
                "ParagonBoardUI",
                "72",
                "12",
                "RequirementsNotMet",
                "{c_red}Requirements not met{/c}",
            ],
        ]
        rows_ja = [
            [
                "1",
                "Power_Paragon_Spiritborn_Legendary_007",
                "1",
                "10",
                "desc",
                "物理、火炎、電撃、冷気、毒、シャドウダメージの全ボーナスの"
                "合計の{c_number}[SF_1 * 100|1x%|]{/c}に等しいボーナス"
                "ダメージを与える。最大量は合計"
                "{c_number}[SF_0 * 100|x%|]{/c}。",
            ],
            [
                "2",
                "ParagonBoardUI",
                "70",
                "11",
                "ThresholdBonusAttribute",
                "{c_label}ボーナス:{/c} 条件を満たしている場合、"
                "{s1}を1つ追加:",
            ],
            [
                "3",
                "ParagonBoardUI",
                "72",
                "12",
                "RequirementsNotMet",
                "{c_red}条件が満たされていません{/c}",
            ],
        ]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            en_path = root / "en.csv"
            ja_path = root / "ja.csv"
            for path, rows in ((en_path, rows_en), (ja_path, rows_ja)):
                with path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(merge_tool.CSV_REQUIRED_COLUMNS)
                    writer.writerows(rows)
            merged, _ = merge_tool.merge_csv_files(
                en_path, ja_path, {}, categories=("paragon",)
            )

        effect_pattern = next(
            pattern
            for pattern in merged
            if pattern.startswith(r"You\s+deal\s+bonus\s+damage")
        )
        self.assertRegex(
            "You deal bonus damage equal to 7.5% of all your bonuses to "
            "Damage with Physical, Fire, Lightning, Cold, Poison, and "
            "Shadow combined, up to 60% total.",
            effect_pattern,
        )
        self.assertEqual(
            merged[effect_pattern],
            "物理、火炎、電撃、冷気、毒、シャドウダメージの全ボーナスの"
            "合計の$1に等しいボーナスダメージを与える。最大量は合計$2。",
        )
        bonus_pattern = next(
            pattern
            for pattern in merged
            if pattern.startswith(r"Bonus:\s+Another")
        )
        self.assertRegex(
            "Bonus: Another +3.0% Resistance to All Elements "
            "if requirements met:",
            bonus_pattern,
        )
        self.assertEqual(
            merged[bonus_pattern],
            "ボーナス: $1（条件を満たしている場合）",
        )
        self.assertEqual(
            merged["Requirements not met"],
            "条件が満たされていません",
        )

    def test_paragon_glyph_socket_maxroll_variants_are_generated(self):
        def csv_row(key, translation):
            return merge_tool.CsvRow(
                ("659576", "ParagonBoardUI", "1", "1", key),
                "ParagonBoardUI",
                key,
                translation,
                2,
            )

        cases = (
            (
                "GlyphSocketed",
                "Socketed Glyph:",
                "ソケットにはめ込んだグリフ:",
                "SOCKETED Glyph:",
                "ソケットにはめ込んだグリフ:",
            ),
            (
                "GlyphLevel",
                "Level {s1}",
                "レベル{s1}",
                "Level: 25",
                "レベル: 25",
            ),
            (
                "ThresholdBonusAttribute",
                "{c_label}Bonus:{/c} Another {s1} if requirements met:",
                "{c_label}ボーナス:{/c} 条件を満たしている場合、{s1}を1つ追加:",
                "(if requirements met)",
                "（条件を満たしている場合）",
            ),
            (
                "ThresholdRequirementsInRangeHeader",
                "{c_label}Requirements:{/c}\n"
                "{c_lightgray}(purchased in radius range){/c}",
                "{c_label}条件:{/c}\n"
                "{c_lightgray}（範囲内で購入）{/c}",
                "(purchased in radius range)",
                "（範囲内で購入）",
            ),
            (
                "RequirementListThresholdMetInRange",
                "{icon:bullet, 1.4} {c_green}{s1}{/c} / {s2} "
                "(purchased in range)",
                "{icon:bullet, 1.4} {c_green}{s1}{/c} / {s2} "
                "（範囲内で購入）",
                "69 / +25 Intelligence (purchased in range)",
                "69 / +25 Intelligence （範囲内で購入）",
            ),
        )

        for key, english, japanese, rendered, expected in cases:
            with self.subTest(key=key):
                pairs = merge_tool.create_paragon_tooltip_ui_pairs(
                    csv_row(key, english),
                    csv_row(key, japanese),
                )
                matched = [
                    re.sub(
                        pattern,
                        re.sub(r"\$(\d+)", r"\\\1", replacement),
                        rendered,
                        flags=re.IGNORECASE,
                    )
                    for pattern, replacement in pairs
                    if re.search(pattern, rendered, flags=re.IGNORECASE)
                ]
                self.assertIn(expected, matched)

        header_pairs = merge_tool.create_paragon_tooltip_ui_pairs(
            csv_row(
                "ThresholdRequirementsInRangeHeader",
                "{c_label}Requirements:{/c}\n"
                "{c_lightgray}(purchased in radius range){/c}",
            ),
            csv_row(
                "ThresholdRequirementsInRangeHeader",
                "{c_label}条件:{/c}\n"
                "{c_lightgray}（範囲内で購入）{/c}",
            ),
        )
        self.assertFalse(
            any(
                pattern.startswith(r"Requirements:\s+")
                and "purchased" in pattern
                for pattern, _ in header_pairs
            )
        )

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
