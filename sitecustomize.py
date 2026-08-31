# Auto-loaded by Python's site initialization when this repository is on sys.path.
# This keeps the stable wsgi.py untouched while enabling the student-provided
# Gemini key endpoint and browser UI for the practice page.
try:
    import student_gemini
    import student_gemini_ui
except Exception:
    # Never prevent the main Flask app from starting if the optional Gemini UI fails.
    pass
