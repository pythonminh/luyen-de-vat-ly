import unittest
from unittest.mock import patch

from flask import Flask

import ra_de_fixed


class RaDeFixedTestCase(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.register_blueprint(ra_de_fixed.bp)
        self.client = app.test_client()

    def test_make_block_preview_strips_tex_wrappers(self):
        block = r"""
\dangbt{Dạng mẫu}
\begin{ex}
% ID: SAMPLE
Cho \textbf{biểu thức} $x+1$.
\choice
{Đáp án A}
\loigiai{Lời giải dài}
\end{ex}
"""
        preview = ra_de_fixed.make_block_preview(block, limit=80)
        self.assertIn("Cho biểu thức x+1.", preview)
        self.assertNotIn(r"\begin{ex}", preview)
        self.assertNotIn(r"\loigiai", preview)
        self.assertNotIn("Lời giải dài", preview)

    @patch("ra_de_fixed._read_tex_text")
    def test_preview_endpoint_returns_question_previews(self, read_text_mock):
        read_text_mock.return_value = r"""
\dangbt{Dạng A}
\begin{ex}Câu thứ nhất.\end{ex}
\begin{ex}Câu thứ hai.\end{ex}
"""

        resp = self.client.get("/ra-de/preview?path=ngan-hang/test.tex&dang=D%E1%BA%A1ng%20A")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["items"][0]["index"], 0)
        self.assertIn("Câu thứ nhất.", data["items"][0]["preview"])

    def test_preview_endpoint_rejects_invalid_path(self):
        resp = self.client.get("/ra-de/preview?path=../ra_de_fixed.py&dang=D%E1%BA%A1ng%20A")
        self.assertEqual(resp.status_code, 404)
        data = resp.get_json()
        self.assertFalse(data["ok"])

    @patch("ra_de_fixed.random.shuffle", side_effect=lambda items: None)
    @patch("ra_de_fixed.random.sample", side_effect=lambda pool, k: pool[:k])
    @patch("ra_de_fixed.blocks_grouped_by_dang")
    def test_generate_prefers_manual_selection_over_count(self, grouped_mock, _sample_mock, _shuffle_mock):
        grouped_mock.return_value = {
            "Dạng A": ["A0", "A1", "A2"],
            "Dạng B": ["B0", "B1"],
        }

        resp = self.client.post(
            "/ra-de/generate",
            data={
                "ten_de": "Đề chọn tay",
                "c__ngan-hang/test.tex__Dạng A": "2",
                "q__ngan-hang/test.tex__Dạng A__1": "1",
                "c__ngan-hang/test.tex__Dạng B": "1",
            },
        )

        self.assertEqual(resp.status_code, 200)
        text = resp.get_data(as_text=True)
        self.assertIn("Đã tạo đề — 2 câu", text)
        self.assertIn("A1", text)
        self.assertIn("B0", text)
        self.assertNotIn("A0", text)
        self.assertNotIn("A2", text)


if __name__ == "__main__":
    unittest.main()
