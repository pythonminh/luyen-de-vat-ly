import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (REPO_ROOT / "app.py").read_text(encoding="utf-8")


class AppTopBarButtonsTest(unittest.TestCase):
    def test_app_html_contains_github_button(self):
        self.assertIn('href="https://github.com/pythonminh/luyen-de-vat-ly"', APP_SOURCE)
        self.assertIn('🐙 GitHub', APP_SOURCE)
        self.assertIn('target="_blank"', APP_SOURCE)
        self.assertIn('rel="noopener noreferrer"', APP_SOURCE)

    def test_app_html_contains_admin_compose_button_and_handler(self):
        self.assertIn('id="topComposeExamBtn"', APP_SOURCE)
        self.assertIn('📄 Ra đề', APP_SOURCE)
        self.assertIn('ldvlOpenAdminComposeFromTopBar', APP_SOURCE)
        self.assertIn("toggleQuizElHide('topComposeExamBtn',!adm);", APP_SOURCE)


if __name__ == "__main__":
    unittest.main()
