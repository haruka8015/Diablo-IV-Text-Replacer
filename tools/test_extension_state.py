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


if __name__ == "__main__":
    unittest.main()
