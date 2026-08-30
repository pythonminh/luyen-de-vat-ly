# Compatibility shim: wsgi.py imports ra_de_fixed.
# The active implementation is ra_de.py.
from ra_de import bp

__all__ = ["bp"]
