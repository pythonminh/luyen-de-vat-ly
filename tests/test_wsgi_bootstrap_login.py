import unittest
from unittest.mock import patch

import app as app_module
import wsgi_bootstrap


class WsgiBootstrapLoginTests(unittest.TestCase):
    def setUp(self):
        wsgi_bootstrap.app.config.update(TESTING=True)
        self.client = wsgi_bootstrap.app.test_client()

    def test_bootstrap_guest_sees_single_login_page_without_admin_or_github_links(self):
        res = self.client.get("/login")
        text = res.get_data(as_text=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Đăng nhập chung", text)
        self.assertIn("Chỉ có 1 trang đăng nhập duy nhất.", text)
        self.assertNotIn("Đăng nhập học viên", text)
        self.assertNotIn("href='/admin/login'", text)
        self.assertNotIn("href='/admin'", text)
        self.assertNotIn("🐙 GitHub", text)

    def test_bootstrap_legacy_login_routes_redirect_to_login(self):
        member_login = self.client.get("/member/login", follow_redirects=False)
        admin_login = self.client.get("/admin/login", follow_redirects=False)
        self.assertEqual(member_login.status_code, 302)
        self.assertEqual(admin_login.status_code, 302)
        self.assertTrue(member_login.headers["Location"].endswith("/login"))
        self.assertTrue(admin_login.headers["Location"].endswith("/login"))

    def test_bootstrap_admin_can_login_from_legacy_member_route(self):
        with patch.object(app_module, "ADMIN_USER", "ADMIN"), patch.object(
            app_module, "ADMIN_PASS", "secret"
        ):
            res = self.client.post(
                "/member/login",
                data={"username": "ADMIN", "password": "secret"},
                follow_redirects=False,
            )
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers["Location"].endswith("/admin"))

    def test_bootstrap_admin_can_use_practice_jump_route(self):
        with self.client.session_transaction() as sess:
            sess["role"] = "admin"
            sess["username"] = "ADMIN"
            sess["practice_ids"] = [0, 1]
        res = self.client.get("/practice/jump/1", follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers["Location"].endswith("/member/practice"))


if __name__ == "__main__":
    unittest.main()
