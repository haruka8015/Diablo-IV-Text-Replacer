import json
import re
import unittest
from pathlib import Path


SOURCES = Path(__file__).resolve().parents[1] / "sources"


class ExtensionStateTests(unittest.TestCase):
    def source(self, name):
        return (SOURCES / name).read_text(encoding="utf-8")

    def test_extension_version_tracks_season_14_second_release(self):
        manifest = json.loads(self.source("manifest.json"))
        self.assertEqual(manifest["version"], "1.14.1")

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

    def test_popup_version_stays_in_normal_layout_flow(self):
        popup = self.source("popup.html")
        version_rules = re.findall(
            r"#version\s*\{(.*?)\}",
            popup,
            re.DOTALL,
        )
        version_rule = next(
            rule for rule in version_rules if "position:" in rule
        )
        self.assertIn("position: static", version_rule)
        self.assertIn("text-align: right", version_rule)
        self.assertNotIn("position: absolute", version_rule)

    def test_maxroll_guide_translation_defaults_on_and_is_saved(self):
        background = self.source("background.js")
        popup = self.source("popup.js")
        content = self.source("content.js")
        self.assertIn(
            "typeof result.guideTranslationEnabled === 'undefined'",
            background,
        )
        self.assertIn("defaults.guideTranslationEnabled = true", background)
        self.assertIn(
            "guideTranslationEnabled: translationToggle.checked",
            popup,
        )
        self.assertIn(
            "result.guideTranslationEnabled !== false",
            content,
        )
        self.assertIn("changes.guideTranslationEnabled", content)

    def test_translator_model_download_is_user_initiated_and_monitored(self):
        popup = self.source("popup.js")
        self.assertIn("'Translator' in self", popup)
        self.assertIn("Translator.availability(translatorOptions)", popup)
        self.assertIn("const createPromise = Translator.create({", popup)
        self.assertIn("downloadprogress", popup)
        self.assertIn("translator.destroy()", popup)
        self.assertLess(
            popup.index("const createPromise = Translator.create({"),
            popup.index("const translator = await createPromise"),
        )

    def test_offscreen_document_owns_sequential_translator(self):
        manifest = json.loads(self.source("manifest.json"))
        background = self.source("background.js")
        offscreen = self.source("offscreen.js")
        self.assertIn("offscreen", manifest["permissions"])
        self.assertIn("chrome.offscreen.createDocument", background)
        self.assertIn("translatorAvailability", background)
        self.assertIn("translateText", background)
        self.assertIn("let translatorPromise = null", offscreen)
        self.assertIn("let translationQueue = Promise.resolve()", offscreen)
        self.assertIn("availability !== 'available'", offscreen)
        self.assertIn("translator.translate(text)", offscreen)

    def test_translation_toggle_releases_runtime_resources(self):
        background = self.source("background.js")
        offscreen = self.source("offscreen.js")
        self.assertIn("function releaseTranslationRuntime", background)
        self.assertIn("action: 'releaseTranslator'", background)
        self.assertIn("chrome.offscreen.closeDocument()", background)
        self.assertIn("!isTranslationRuntimeEnabled()", background)
        self.assertIn("Guide translation is disabled", background)
        self.assertIn("function releaseTranslator()", offscreen)
        self.assertIn("translator?.destroy()", offscreen)
        self.assertIn("translatorPromise = null", offscreen)

    def test_maxroll_machine_translation_uses_validated_opaque_tokens(self):
        content = self.source("content.js")
        self.assertIn(
            "const GUIDE_TOKEN_PATTERN = /ZXQJ\\d{4}QJQXZ/g",
            content,
        )
        self.assertIn(
            "`ZXQJ${String(nextTokenId++).padStart(4, '0')}QJQXZ`",
            content,
        )
        self.assertIn("function applyGuideDictionary", content)
        self.assertNotIn("protectDictionaryMatches", content)
        self.assertIn("function validateGuideTranslation", content)
        self.assertIn(
            "Array.from(counts.values()).every(count => count === 1)",
            content,
        )
        self.assertIn("wrapperStack.pop() !== payload.node", content)
        self.assertIn(
            "validateGuideTranslation(response.text, record.tokens)",
            content,
        )
        self.assertIn("renderGuideBlock(block, output, record.tokens)", content)

    def test_maxroll_guide_skips_generic_text_rebuilder(self):
        content = self.source("content.js")
        self.assertIn(
            "const MAXROLL_GUIDE_ROOT_SELECTOR = '#main-article, main article'",
            content,
        )
        self.assertIn("'main article h1'", content)
        self.assertIn(
            "'[class*=\"_D4PlannerPageQuote_\"]'",
            content,
        )
        self.assertIn(
            "'[class*=\"_StrAndWeak__blockListItemText_\"]'",
            content,
        )
        self.assertIn(
            "'[class*=\"_PlannerPageSection__content_\"] > div > p'",
            content,
        )
        self.assertIn(
            "'[class*=\"_ArticleAccordion__itemHeaderTitle_\"] '",
            content,
        )
        self.assertIn("new IntersectionObserver", content)
        self.assertIn("rootMargin: '1200px 0px'", content)
        self.assertIn("pendingGuideViewportBlocks", content)
        self.assertIn("window.addEventListener('scroll'", content)
        self.assertIn("collectGuideBlocks(root, false)", content)
        self.assertNotIn(
            "pendingRoots.size > DOM_CHANGE_MUTATION_THRESHOLD",
            content,
        )
        self.assertIn("GUIDE_TRANSLATION_MAX_ATTEMPTS = 2", content)
        self.assertIn("function translateGuideTextNodesInPlace", content)
        self.assertIn("prepareGuideTranslationInput(record.source)", content)
        self.assertIn("if (isMaxrollGuideNode(node))", content)
        self.assertIn("function isD4SemanticElement", content)
        self.assertIn("function setElementTextPreservingMarkup", content)
        self.assertIn("wrapper.node.replaceChildren(wrapper.fragment)", content)
        self.assertNotIn("block.innerHTML =", content)

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
            "element.classList.contains('d4-color-inactive')", content
        )
        self.assertIn("DYNAMIC_VALUE_TEXT.test(element.textContent)", content)
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
        self.assertIn("const orderedAnchors = [...anchors].sort(", content)
        self.assertIn("fragment.appendChild(anchorRoots[index])", content)
        self.assertIn("containerNode.replaceChildren(fragment)", content)
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

    def test_specific_parameter_patterns_sort_before_generic_templates(self):
        content = self.source("content.js")
        self.assertIn("const wildcardCount = pattern =>", content)
        self.assertIn(
            "const wildcardDifference = wildcardCount(a) - wildcardCount(b)",
            content,
        )
        self.assertIn(
            "return wildcardDifference || b.length - a.length", content
        )

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
        self.assertIn("function scheduleTooltipTranslation(root)", content)
        self.assertIn("pendingTooltipRoots.add(closestTooltip)", content)
        self.assertIn("tooltipTranslationTimer = setTimeout(() =>", content)
        self.assertIn("}, 0);", content)
        self.assertIn("if (observeDOMTimer) {", content)
        self.assertIn("observeDOMTimer = null;", content)
        self.assertIn("const isConcatenatedRunePattern =", content)
        self.assertIn("isConcatenatedRunePattern ? 'g' : 'gi'", content)
        self.assertIn("const DROP_SOURCE_ITEM_SELECTOR = '.d4t-source li'", content)
        self.assertIn("const DROP_SOURCE_KEY_PREFIX =", content)
        self.assertIn("function replaceDropSourceText(element, stats)", content)
        self.assertIn("originalText.split(',').map(part =>", content)
        self.assertIn("const bossName = part.trim()", content)
        self.assertIn("translatedParts.join(', ')", content)
        self.assertIn("function isSupplementaryValueElement(element)", content)
        self.assertIn(
            "SUPPLEMENTARY_VALUE_MARKER_TEXT.test(element.textContent)",
            content,
        )
        self.assertIn("!anchorRoots.includes(root)", content)
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
        self.assertEqual(translations["Shattered Vow"], "砕かれし誓い")
        self.assertEqual(translations["Shatterd Vow"], "砕かれし誓い")

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
