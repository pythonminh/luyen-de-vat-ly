import hashlib
import json
import unittest
from unittest.mock import patch

import app as app_module


SAMPLE_TEX = r"""\dang{Dao động}
\begin{ex}
% Mức: NB
Câu hỏi mẫu?
\choice{\True $A$}{$B$}{$C$}{$D$}
\loigiai{Lời giải mẫu}
\end{ex}
"""


def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()


class FakeGeminiResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(
            {"candidates": [{"content": {"parts": [{"text": "Phản biện mẫu"}]}}]}
        ).encode()


class AppAuthAndGeminiTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config.update(TESTING=True)
        self.client = app_module.app.test_client()
        self.members_patch = patch.object(
            app_module,
            "members_data",
            return_value={
                "members": [
                    {
                        "username": "hocvien",
                        "name": "Học viên",
                        "class": "12",
                        "account_type": "FREE",
                        "status": "ON",
                        "password_sha256": sha256("matkhau"),
                    },
                    {
                        "username": "khoa",
                        "name": "Bị khóa",
                        "class": "12",
                        "account_type": "VIP",
                        "status": "OFF",
                        "password_sha256": sha256("matkhau"),
                    },
                ]
            },
        )
        self.index_patch = patch.object(
            app_module,
            "index_data",
            return_value={
                "lessons": [
                    {
                        "Mon": "Vật lý",
                        "Lop": "12",
                        "Chuong": "Dao động",
                        "BaiHoc": "Bài VIP",
                        "path": "ngan-hang/vip.tex",
                        "questions": 1,
                        "dang": {"Dao động": 1},
                    }
                ],
                "total_files": 1,
                "total_questions": 1,
            },
        )
        self.access_patch = patch.object(
            app_module,
            "access_data",
            return_value={"default": "FREE", "lessons": {"ngan-hang/vip.tex": "VIP"}},
        )
        self.read_tex_patch = patch.object(
            app_module, "read_tex", return_value=("sha", SAMPLE_TEX)
        )
        self.admin_user_patch = patch.object(app_module, "ADMIN_USER", "ADMIN")
        self.admin_pass_patch = patch.object(app_module, "ADMIN_PASS", "admin-secret")
        self.gemini_key_patch = patch.object(app_module, "GEMINI_KEY", "")
        for p in (
            self.members_patch,
            self.index_patch,
            self.access_patch,
            self.read_tex_patch,
            self.admin_user_patch,
            self.admin_pass_patch,
            self.gemini_key_patch,
        ):
            p.start()
            self.addCleanup(p.stop)

    def login_as(self, role, username):
        with self.client.session_transaction() as sess:
            sess["role"] = role
            sess["username"] = username

    def test_shared_login_accepts_member_account(self):
        res = self.client.post(
            "/login",
            data={"username": "hocvien", "password": "matkhau"},
            follow_redirects=False,
        )
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers["Location"].endswith("/member"))
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["role"], "member")
            self.assertEqual(sess["username"], "hocvien")

    def test_legacy_login_routes_redirect_to_single_login_page(self):
        member_login = self.client.get("/member/login", follow_redirects=False)
        admin_login = self.client.get("/admin/login", follow_redirects=False)
        main_login = self.client.get("/login")
        self.assertEqual(member_login.status_code, 302)
        self.assertEqual(admin_login.status_code, 302)
        self.assertTrue(member_login.headers["Location"].endswith("/login"))
        self.assertTrue(admin_login.headers["Location"].endswith("/login"))
        text = main_login.get_data(as_text=True)
        self.assertIn("Chỉ có 1 trang đăng nhập duy nhất.", text)
        self.assertIn("action='/login'", text)
        self.assertIn("hocvien01 hoặc ADMIN", text)

    def test_shared_login_accepts_admin_from_member_route(self):
        res = self.client.post(
            "/login",
            data={"username": "ADMIN", "password": "admin-secret"},
            follow_redirects=False,
        )
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers["Location"].endswith("/admin"))
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["role"], "admin")
            self.assertEqual(sess["username"], "ADMIN")

    def test_login_shows_clear_member_errors(self):
        wrong = self.client.post(
            "/login",
            data={"username": "hocvien", "password": "sai"},
        )
        locked = self.client.post(
            "/login",
            data={"username": "khoa", "password": "matkhau"},
        )
        self.assertIn("Sai tài khoản hoặc mật khẩu.", wrong.get_data(as_text=True))
        self.assertIn(
            "Tài khoản của bạn hiện đang bị tắt. Vui lòng liên hệ ADMIN.",
            locked.get_data(as_text=True),
        )

    def test_github_link_and_route_are_admin_only(self):
        guest = self.client.get("/login")
        self.assertNotIn("🐙 GitHub", guest.get_data(as_text=True))

        self.login_as("member", "hocvien")
        member_page = self.client.get("/member")
        self.assertNotIn("🐙 GitHub", member_page.get_data(as_text=True))
        blocked = self.client.get("/github/repo", follow_redirects=False)
        self.assertEqual(blocked.status_code, 302)
        self.assertTrue(blocked.headers["Location"].endswith("/member"))

        self.login_as("admin", "ADMIN")
        admin_page = self.client.get("/member")
        self.assertIn("🐙 GitHub", admin_page.get_data(as_text=True))
        allowed = self.client.get("/github/repo", follow_redirects=False)
        self.assertEqual(allowed.status_code, 302)
        self.assertIn("github.com/pythonminh/luyen-de-vat-ly", allowed.headers["Location"])

    def test_admin_can_access_vip_practice_flow_and_see_gemini_input(self):
        self.login_as("admin", "ADMIN")
        select_page = self.client.get("/member/select?path=ngan-hang/vip.tex")
        self.assertEqual(select_page.status_code, 200)
        self.assertIn("Tạo bài luyện tập", select_page.get_data(as_text=True))

        started = self.client.post(
            "/member/start",
            data={"path": "ngan-hang/vip.tex", "pick:0:TN:N": "1"},
            follow_redirects=False,
        )
        self.assertEqual(started.status_code, 302)
        self.assertTrue(started.headers["Location"].endswith("/member/practice"))

        practice_page = self.client.get("/member/practice")
        text = practice_page.get_data(as_text=True)
        self.assertIn("Gemini API key cá nhân", text)
        self.assertIn("localStorage", text)

    def test_gemini_review_prefers_client_api_key(self):
        self.login_as("admin", "ADMIN")
        captured = {}
        api_key = "AIza" + ("a" * 35)

        def fake_urlopen(req, timeout=0):
            captured["url"] = req.full_url
            captured["body"] = req.data.decode()
            return FakeGeminiResponse()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            res = self.client.post(
                "/api/gemini/review",
                json={"text": "Câu hỏi", "student": "Đáp án", "api_key": api_key},
            )

        self.assertEqual(res.status_code, 200)
        self.assertIn(f"key={api_key}", captured["url"])
        self.assertNotIn("api_key", captured["body"])
        self.assertTrue(res.get_json()["ok"])


if __name__ == "__main__":
    unittest.main()
