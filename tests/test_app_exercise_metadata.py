import unittest

from app import SheetStore, load_physics_exercise_metadata_map


class AppExerciseMetadataTests(unittest.TestCase):
    def test_metadata_map_contains_sample_physics_lesson(self):
        lesson_map = load_physics_exercise_metadata_map()
        sample = lesson_map.get(
            "Vật lý/Lớp 11/Chương I. Dao động/L11C1 Bài 1. Dao động điều hòa/de.tex"
        )
        self.assertIsNotNone(sample)
        self.assertIn("Dạng trắc nghiệm", sample["ExerciseTypeNames"])
        self.assertGreater(sample["ExerciseTypeCounts"]["Dạng tính toán"], 0)

    def test_github_catalog_is_enriched_with_exercise_types(self):
        store = SheetStore()
        store._rebuild_github_catalog_from_files()
        item = next(x for x in store.catalog if x.get("BaiHoc") == "L11C1 Bài 1. Dao động điều hòa")
        self.assertIn("Dạng trắc nghiệm", item.get("ExerciseTypeNames", []))
        self.assertGreater(item.get("ExerciseTypeCounts", {}).get("Dạng tính toán", 0), 0)


if __name__ == "__main__":
    unittest.main()
