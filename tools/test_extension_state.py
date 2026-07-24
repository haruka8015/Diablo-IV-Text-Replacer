import json
import re
import unittest
from pathlib import Path


SOURCES = Path(__file__).resolve().parents[1] / "sources"


class ExtensionStateTests(unittest.TestCase):
    def source(self, name):
        return (SOURCES / name).read_text(encoding="utf-8")

    def test_update_does_not_force_extension_on_or_inject_twice(self):
        background = self.source("background.js")
        self.assertIn("typeof result.enabled === 'undefined'", background)
        self.assertNotIn("chrome.tabs.onUpdated", background)
        self.assertNotIn("executeScript", background)

    def test_content_script_reloads_all_open_target_tabs_on_state_change(self):
        content = self.source("content.js")
        self.assertIn("chrome.storage.onChanged.addListener", content)
        self.assertIn("window.location.reload()", content)
        self.assertIn("message.action === 'convert' && extensionEnabled", content)

    def test_popup_cannot_convert_while_disabled(self):
        popup = self.source("popup.js")
        self.assertIn("convertButton.disabled = !enabled", popup)
        self.assertIn("result.enabled !== true", popup)
        self.assertNotIn("chrome.tabs.reload", popup)

    def test_adjacent_text_nodes_are_translated_without_rebuilding_elements(self):
        content = self.source("content.js")
        self.assertIn("function replaceTextNodeRun", content)
        self.assertIn("textNodes.map(textNode => textNode.nodeValue).join('')", content)
        self.assertIn("textNodes[index].nodeValue = replacement", content)
        self.assertNotIn(".normalize()", content)
        self.assertNotIn(".textContent =", content)
        self.assertIn("'TEXTAREA'", content)
        self.assertIn("!node.isContentEditable", content)

    def test_inline_maxroll_markup_is_joined_without_replacing_elements(self):
        content = self.source("content.js")
        self.assertIn("function collectInlineTextNodes", content)
        self.assertIn("function hasBlockBoundaryChild", content)
        self.assertIn("const inlineTextNodes = []", content)
        self.assertIn("const supplementaryRangeNodes = []", content)
        self.assertIn("supplementaryRangeNodes,\n              node", content)
        self.assertIn("BLOCK_BOUNDARY_TAGS", content)
        self.assertIn("DYNAMIC_VALUE_TEXT", content)
        self.assertIn("textNodes[anchor.nodeIndex].nodeValue = anchor.value", content)
        self.assertNotIn(".innerHTML =", content)
        self.assertNotIn("replaceWith(", content)

    def test_equipment_tooltip_supplementary_ranges_are_excluded_from_matching(self):
        content = self.source("content.js")
        self.assertIn(
            "child.classList.contains('d4-color-inactive')", content
        )
        self.assertIn("DYNAMIC_VALUE_TEXT.test(child.textContent)", content)
        self.assertIn("SUPPLEMENTARY_VALUE_MARKER_TEXT", content)
        self.assertIn(
            "これは原文データには存在しない補足表示なので、効果文の照合から外す",
            content,
        )
        self.assertIn("supplementaryRangeNodes = []", content)
        self.assertIn(
            "collectInlineTextNodes(child, supplementaryRangeNodes)", content
        )
        self.assertNotIn(
            "supplementaryRangeNodes.forEach(textNode =>", content
        )
        self.assertIn("anchors.length === requiredAnchorCount", content)

    def test_full_tooltip_sentence_preserves_formatting_spans_as_anchors(self):
        content = self.source("content.js")
        self.assertIn("matchInfo.wholeSentence", content)
        self.assertIn(
            "containerNode.closest(LONG_TEXT_TOOLTIP_SELECTOR)", content
        )
        self.assertIn("function isStyledTextNode", content)
        self.assertIn("element.classList.contains('d4-style-u')", content)
        self.assertIn("textNodes[anchor.nodeIndex].nodeValue = anchor.value", content)
        self.assertIn(
            "if (isTooltipSentence && requiredAnchorCount > 0)", content
        )
        self.assertNotIn("textNode === outputNode ? newText : ''", content)

    def test_long_effect_rules_are_limited_to_game_tooltips(self):
        content = self.source("content.js")
        self.assertIn("allowWholeSentence = false", content)
        self.assertIn(
            "let compiledWholeSentencePatterns = null", content
        )
        self.assertIn(
            "compiledWholeSentencePatterns.push(compiledPattern)", content
        )
        self.assertIn(
            "if (allowWholeSentence)", content
        )
        self.assertIn(
            "applyCompiledPatternList(\n"
            "          text,\n"
            "          compiledWholeSentencePatterns",
            content,
        )
        self.assertIn(
            "'.d4t-GameTooltip, .d4t-SkillTagTooltip'",
            content,
        )
        self.assertIn(
            "textNodes[0]?.parentElement?.closest(LONG_TEXT_TOOLTIP_SELECTOR)",
            content,
        )
        self.assertIn("Boolean(tooltipContainer)", content)

    def test_straight_and_curly_apostrophes_both_match(self):
        content = self.source("content.js")
        self.assertIn(
            "pattern.replace(/['’]/g, \"['’]\")",
            content,
        )

    def test_maxroll_br_separated_effect_lines_are_joined_independently(self):
        content = self.source("content.js")
        self.assertIn(
            "function replaceInlineRunsBetweenBlockBoundaries", content
        )
        self.assertIn("BLOCK_BOUNDARY_TAGS.has(child.tagName)", content)
        self.assertIn(
            "replaceInlineRunsBetweenBlockBoundaries(node, regexTable, stats)",
            content,
        )
        self.assertIn(
            "collectInlineTextNodes(child, supplementaryRangeNodes)", content
        )

    def test_react_text_rewrites_and_tab_visibility_changes_are_observed(self):
        content = self.source("content.js")
        self.assertIn("characterData: true", content)
        self.assertIn("mutation.type === 'characterData'", content)
        self.assertIn("scheduleTranslation(mutation.target.parentElement)", content)
        self.assertIn("'aria-selected'", content)
        self.assertIn("'title'", content)
        self.assertIn("replaceTitleAttributes(regexTable, undefined, root)", content)

    def test_sentence_patterns_ending_in_punctuation_do_not_get_a_word_boundary(self):
        content = self.source("content.js")
        self.assertIn("function createTranslationRegex", content)
        self.assertIn("const trailingBoundary = /[A-Za-z0-9_]$/.test(pattern)", content)
        self.assertNotIn("`\\\\b${escapedPattern}\\\\b`", content)

    def test_all_paragon_node_types_have_translations(self):
        translations = json.loads(self.source("translations.json"))
        self.assertEqual(translations["Common Node"], "コモン・ノード")
        self.assertEqual(translations["Magic Node"], "マジック・ノード")
        self.assertEqual(translations["Rare Node"], "レア・ノード")
        self.assertEqual(
            translations["Legendary Node"], "レジェンダリー・ノード"
        )
        self.assertEqual(translations["Glyph"], "グリフ")
        self.assertEqual(translations["Magic Glyph"], "マジック・グリフ")
        self.assertEqual(translations["Rare Glyph"], "レア・グリフ")
        self.assertEqual(
            translations["Legendary Glyph"], "レジェンダリー・グリフ"
        )

    def test_spiritborn_skill_categories_have_translations(self):
        translations = json.loads(self.source("translations.json"))
        self.assertEqual(translations["Gorilla"], "ゴリラ")
        self.assertEqual(translations["Jaguar"], "ジャガー")
        self.assertEqual(translations["Incarnate"], "顕現")
        self.assertEqual(translations["Centipede"], "センティピード")

    def test_maxroll_spiritborn_affix_short_names_have_translations(self):
        translations = json.loads(self.source("translations.json"))
        self.assertEqual(translations["Pestilence"], "悪疫")
        self.assertEqual(translations["Infestation"], "寄生する毒虫")
        self.assertEqual(translations["Kinetic Suppression"], "動的制圧")
        self.assertEqual(translations["Apprehension"], "危惧")
        self.assertEqual(translations["Fleet Wings"], "速やかなる羽")

    def test_widows_web_full_effect_has_tag_free_translation(self):
        translations = json.loads(self.source("translations.json"))
        key = next(
            key
            for key in translations
            if key.startswith(
                r"Your\s+Critical\s+Strikes\s+cause\s+your\s+Poisoning"
            )
        )
        value = translations[key]
        self.assertEqual(
            value,
            "クリティカルヒットが敵に与えた中毒効果を炸裂させ、即座に合計"
            "中毒ダメージの$1を標的に与えると同時に、この炸裂の$2のダメージ"
            "を周囲の敵に与え、メインの標的から中毒効果を除去する。",
        )
        self.assertNotIn("{", value)
        self.assertNotIn("}", value)

    def test_reported_midgame_equipment_effects_have_renderable_rules(self):
        translations = json.loads(self.source("translations.json"))
        samples = {
            "Enemies\\s+you\\s+kill": (
                "Enemies you kill while an Ultimate Skill is active grants a "
                "stack of Supremacy, each increasing your damage by 5%, up to "
                "30%. When an Ultimate Skill ends, you gain 10 stacks of "
                "Supremacy, but you begin to lose one stack every second."
            ),
            "Casting\\s+a\\s+Non-Basic": (
                "Casting a Non-Basic Mobility Skill grants 3 Resolve."
            ),
            "Pestilent\\s+Swarms\\s+deal": (
                "Pestilent Swarms deal 50% increased damage, last 25% longer, "
                "and spiral outwards."
            ),
            "A\\s+Pestilent\\s+Swarm": (
                "A Pestilent Swarm spawns from you every 2 seconds, dealing "
                "250 Poison damage per hit."
            ),
            "Your\\s+Pestilent\\s+Swarms\\s+now": (
                "Your Pestilent Swarms now orbit around you and reduce an "
                "equipped Eagle Skill's cooldown by 0.5 seconds per hit."
            ),
            "While\\s+your\\s+Spirit\\s+Hall": (
                "While your Spirit Hall choices match:"
            ),
            "Their\\s+bonuses\\s+are": (
                "Their bonuses are 30% more potent."
            ),
        }
        for prefix, sample in samples.items():
            with self.subTest(prefix=prefix):
                patterns = [
                    key for key in translations if key.startswith(prefix)
                ]
                pattern = next(
                    (
                        key
                        for key in patterns
                        if re.search(key, sample, re.IGNORECASE)
                    ),
                    None,
                )
                self.assertIsNotNone(pattern)
                self.assertNotIn("{", translations[pattern])
                self.assertNotIn("}", translations[pattern])

    def test_live_maxroll_flavors_with_quoted_body_have_rules(self):
        translations = json.loads(self.source("translations.json"))
        samples = {
            (
                '"Within this corpse-bound carapace we writhe. Chaotic winds '
                "converge to churn your bones. Our beat and breath a ceaseless "
                'war to break. The wretched cyclone black beyond the bounds." '
                "- Balazan's Dream"
            ): (
                "「いずれ死体となりし殻の中に、我らもがけり。秩序なき風が集いて、"
                "骨をかき回さん。鼓動も呼吸も勝利の望めぬ死戦たり。哀しきかの旋風の、"
                "底の見えぬ黒さかな」―バラザンの夢"
            ),
            (
                '"One touch is all it took. She looked into my eyes, and I '
                "understood her hunger, endless and painful. I will start with "
                'the taverns and find a strong one, with strong blood." '
                "-Jios, Sarat's Servant"
            ): (
                "「一度触れれば十分だった。彼女が私の目を見つめ、私は彼女の飢えを"
                "感じ取った。それは永遠に満たされない、痛ましいものだった。まずは"
                "酒場に行き、強い血を持つ強い者を見つけるとしよう」"
                "―サラットの従僕、ジオス"
            ),
        }
        for live_text, expected in samples.items():
            with self.subTest(live_text=live_text):
                replacement = next(
                    (
                        value
                        for pattern, value in translations.items()
                        if re.fullmatch(pattern, live_text, re.IGNORECASE)
                    ),
                    None,
                )
                self.assertEqual(replacement, expected)
                self.assertNotIn("{", replacement)
                self.assertNotIn("}", replacement)

    def test_pestilent_swarm_skill_tag_annotation_has_renderable_rule(self):
        translations = json.loads(self.source("translations.json"))
        live_text = (
            "Pestilent Swarms move quickly and deal Poison damage to enemies hit."
        )
        replacement = next(
            (
                value
                for pattern, value in translations.items()
                if re.fullmatch(pattern, live_text, re.IGNORECASE)
            ),
            None,
        )
        self.assertEqual(
            replacement,
            "悪疫の虫の群れは素早く移動し、命中した敵に毒ダメージを与える。",
        )
        self.assertNotIn("{", replacement)
        self.assertNotIn("}", replacement)


if __name__ == "__main__":
    unittest.main()
