# -*- coding: utf-8 -*-
"""Prevent JavaScript object literals/regex braces from being parsed as Jinja tags."""

try:
    import re
    import github_question_editor as m

    if not getattr(m, "_JINJA_BRACE_FIX", False) and hasattr(m, "TPL"):
        tpl = m.TPL
        saved = []

        # Protect real Jinja print expressions first.
        def protect(match):
            saved.append(match.group(0))
            return f"__LDVL_JINJA_{len(saved)-1}__"

        tpl = re.sub(r"\{\{.*?\}\}", protect, tpl, flags=re.S)

        # The editor template contains JS objects such as {{n:1,...}} and
        # regex character classes like [^{{}}]. They are JavaScript, not Jinja.
        tpl = tpl.replace("{{", "{").replace("}}", "}")

        # Restore the actual Jinja expressions used by Flask.
        for i, value in enumerate(saved):
            tpl = tpl.replace(f"__LDVL_JINJA_{i}__", value)

        m.TPL = tpl
        m._JINJA_BRACE_FIX = True
except Exception:
    # Do not stop the application if the optional patch cannot load.
    pass
