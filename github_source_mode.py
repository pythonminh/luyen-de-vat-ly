# -*- coding: utf-8 -*-
from app import app

try:
    import github_route_hook  # noqa: F401
    app.config['GITHUB_ROUTE_HOOK'] = True
except Exception as e:
    app.config['GITHUB_ROUTE_HOOK'] = False
    app.config['GITHUB_ROUTE_HOOK_ERROR'] = str(e)

app.config['GITHUB_SOURCE_ONLY'] = True
