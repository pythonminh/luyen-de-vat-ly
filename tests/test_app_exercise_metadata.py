import json
import os
import tempfile
import unittest
from unittest.mock import patch

import app


class PhysicsExerciseMetadataTests(unittest.TestCase):
    def setUp(self):
        app.load_physics_exercise_metadata_map.cache_clear()

    def tearDown(self):
        app.load_physics_exercise_metadata_map.cache_clear()

    def test_load_physics_exercise_metadata_map_reads_lesson_counts(self):
        rel = "Vật lý/Lớp 10/Chương I. Mở đầu/L10C1 Bài 1. Làm quen với Vật lí/de.tex"
        with tempfile.TemporaryDirectory() as tmp:
            metadata_path = os.path.join(tmp, "bai_tap_phan_loai_metadata.json")
            with open(metadata_path, "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "lessons": [
                            {
                                "path": rel,
                                "counts_by_type": {
                                    "Trắc nghiệm": 60,
                                    "Đúng sai": 30,
                                    "Trả lời ngắn": 36,
                                    "Tự luận": 36,
                                },
                            }
                        ]
                    },
                    fh,
                    ensure_ascii=False,
                )
            meta = app.load_physics_exercise_metadata_map(metadata_path)
        self.assertEqual(meta[rel]["Trắc nghiệm"], 60)
        self.assertEqual(
            meta[rel[: -len("/de.tex")]],
            meta[rel],
        )

    def test_rebuild_github_catalog_includes_dbt_counts_and_order(self):
        rel = "Vật lý/Lớp 10/Chương I. Mở đầu/L10C1 Bài 1. Làm quen với Vật lí/de.tex"
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "Vật lý"), exist_ok=True)
            with open(
                os.path.join(tmp, "Vật lý", "bai_tap_phan_loai_metadata.json"),
                "w",
                encoding="utf-8",
            ) as fh:
                json.dump(
                    {
                        "lessons": [
                            {
                                "path": rel,
                                "counts_by_type": {
                                    "Tự luận": 36,
                                    "Trắc nghiệm": 60,
                                    "Đúng sai": 30,
                                    "Trả lời ngắn": 36,
                                },
                            }
                        ]
                    },
                    fh,
                    ensure_ascii=False,
                )
            store = app.SheetStore()
            lesson = {
                "Mon": "Vật lý",
                "Lop": "10",
                "Chuong": "Chương I. Mở đầu",
                "BaiHoc": "L10C1 Bài 1. Làm quen với Vật lí",
                "path": rel,
                "count_questions": 162,
            }
            cfg = {"local_dir": tmp, "cache_dir": ""}
            with patch.object(app, "github_tex_config", return_value=cfg), patch.object(
                app, "load_muc_luc_lessons", return_value=[lesson]
            ), patch.object(app, "list_local_tex_files", return_value=[]), patch.object(
                app.SheetStore, "_count_tex_on_disk", return_value=162
            ):
                store._rebuild_github_catalog_from_files()
        self.assertEqual(len(store.catalog), 1)
        item = store.catalog[0]
        self.assertEqual(
            item["FilterCounts"]["dangbaitap"],
            {
                "Tự luận": 36,
                "Trắc nghiệm": 60,
                "Đúng sai": 30,
                "Trả lời ngắn": 36,
            },
        )
        self.assertEqual(
            item["DbtOrder"],
            ["Trắc nghiệm", "Đúng sai", "Trả lời ngắn", "Tự luận"],
        )
        self.assertEqual(
            item["DangBaiTap"],
            "Trắc nghiệm, Đúng sai, Trả lời ngắn, Tự luận",
        )

    def test_lesson_card_has_colored_button_classes_for_exercise_types(self):
        with open(app.__file__, "r", encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn(".bookDbtBtn.bookDbtType-tn", src)
        self.assertIn("bookDbtType-'+tone.replace('dang-','')", src)


if __name__ == "__main__":
    unittest.main()
