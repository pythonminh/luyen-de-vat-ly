# Compatibility shim: wsgi.py imports ra_de_fixed.
# The active implementation is ra_de.py.
import ra_de

# Patch the Word exporter so LaTeX formulas are written as native
# editable Word equations (OMML), while keeping the existing generator.
try:
    from word_math import patch_module
    patch_module(ra_de.__dict__)
except Exception as _word_math_error:
    # Keep /ra-de usable even if the optional math patch fails.
    ra_de._WORD_MATH_PATCH_ERROR = str(_word_math_error)

bp = ra_de.bp

__all__ = ["bp"]
