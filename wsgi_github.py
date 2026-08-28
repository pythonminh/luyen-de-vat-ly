# -*- coding: utf-8 -*-
"""Entrypoint production cho trang Ra de.
Khong khoi dong app Google Sheet cu; chi nap ngan hang GitHub.
"""
import os
from flask import Flask, redirect

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "luyen-de-github-2026")

from ra_de import bp as ra_de_bp
app.register_blueprint(ra_de_bp)

@app.get("/")
def home():
    return redirect("/ra-de")

@app.get("/health")
def health():
    return {"ok": True, "source": "github", "route": "/ra-de"}

@app.get("/github")
def github():
    return redirect("https://github.com/pythonminh/luyen-de-vat-ly")
