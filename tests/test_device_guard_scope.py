"""Static regression checks for the scoped device lock (no database needed).

Run: python -m unittest discover -s tests -p 'test_device_guard_scope.py'
"""
import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def extract_function(path, name):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    module = ast.Module(body=[node], type_ignores=[])
    namespace = {}
    exec(compile(ast.fix_missing_locations(module), str(path), "exec"), namespace)
    return namespace[name]


class ScopedDeviceLockTests(unittest.TestCase):
    def test_protected_routes(self):
        guarded = extract_function("device_guard.py", "guarded")
        for path in ("/member/html-practice", "/member/start", "/member/start-selected",
                     "/member/practice", "/member/answer", "/member/exams/open",
                     "/member/exam", "/api/exam/variant/apply",
                     "/api/practice/reshuffle", "/practice/jump/1",
                     "/practice/redo/2"):
            with self.subTest(path=path):
                self.assertTrue(guarded(path))

    def test_login_and_catalog_unlocked(self):
        guarded = extract_function("device_guard.py", "guarded")
        for path in ("/member", "/member/login", "/member/register",
                     "/member/logout", "/member/html-menu", "/member/html-saved",
                     "/admin/members"):
            with self.subTest(path=path):
                self.assertFalse(guarded(path))

    def test_legacy_lock_disabled(self):
        skip = extract_function("app.py", "_skip_device_check")
        for path in ("/member", "/member/login", "/member/start",
                     "/member/html-practice", "/member/answer"):
            self.assertTrue(skip(path))


if __name__ == "__main__":
    unittest.main()
