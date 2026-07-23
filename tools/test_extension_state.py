import json
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
        self.assertIn("textNode.nodeValue = replacement", content)
        self.assertNotIn(".normalize()", content)
        self.assertNotIn(".textContent =", content)
        self.assertIn("'TEXTAREA'", content)
        self.assertIn("!node.isContentEditable", content)

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


if __name__ == "__main__":
    unittest.main()
