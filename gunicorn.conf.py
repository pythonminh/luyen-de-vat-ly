# Gunicorn — 1 worker (cache câu hỏi + token nằm trong RAM).
# Tăng tốc: nhiều thread. timeout worker > Gemini (180s) để dang-fill file lớn không bị cắt.
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
workers = 1
worker_class = "gthread"
threads = 8
timeout = 240
graceful_timeout = 30
keepalive = 5
max_requests = 0
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info").lower()
