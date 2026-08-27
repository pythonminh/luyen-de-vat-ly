import unittest

from phan_loai_bai_tap import PhysicsExerciseClassifier, ROOT_DIR, map_complexity, summarize_complexity


class ExerciseClassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classifier = PhysicsExerciseClassifier(ROOT_DIR / "bai_tap_phan_loai.json")

    def test_multiple_choice_graph_and_application_detection(self):
        block = r"""
% ===== Câu 1 =====
% ID: TEST-01-TN
% Mức: VD
\dangbt{Khai thác đồ thị vận tốc - thời gian trong tình huống thực tế}
\begin{ex}
Quan sát đồ thị vận tốc - thời gian của xe và xác định quãng đường xe đi được.
\choice
{\True 40 m}
{20 m}
{10 m}
{5 m}
\loigiai{...}
\end{ex}
"""
        question = self.classifier.classify_question_block(block, lesson_name="Bài thực tế về đồ thị")
        self.assertIsNotNone(question)
        self.assertEqual(question["question_type"], "TN")
        self.assertIn("multiple_choice", question["exercise_types"])
        self.assertIn("graph_diagram", question["exercise_types"])
        self.assertIn("application", question["exercise_types"])
        self.assertIn("calculation", question["exercise_types"])

    def test_practical_short_answer_detection(self):
        block = r"""
% ===== Câu 2 =====
% ID: TEST-02-TLN
% Mức: TH
\dangbt{Thí nghiệm đo gia tốc rơi tự do và đánh giá sai số}
\begin{ex}
Nêu dụng cụ cần dùng để đo gia tốc rơi tự do trong thí nghiệm.
\shortans{Đồng hồ đo thời gian}
\loigiai{...}
\end{ex}
"""
        question = self.classifier.classify_question_block(block, lesson_name="Bài thực hành")
        self.assertIsNotNone(question)
        self.assertIn("short_answer_essay", question["exercise_types"])
        self.assertIn("practical", question["exercise_types"])
        self.assertIn("analysis", question["exercise_types"])

    def test_complexity_mapping_and_summary(self):
        self.assertEqual(map_complexity("NB"), "dễ")
        self.assertEqual(map_complexity("TH"), "trung bình")
        self.assertEqual(map_complexity("VD"), "khó")
        self.assertEqual(summarize_complexity({"dễ": 3, "trung bình": 1}), "dễ")
        self.assertEqual(summarize_complexity({"trung bình": 2, "khó": 2}), "khó")


if __name__ == "__main__":
    unittest.main()
