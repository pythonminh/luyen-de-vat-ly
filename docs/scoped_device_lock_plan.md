# Scoped device lock rollout notes

Goal: enforce one approved student account per browser device, and one approved
browser device per student, ONLY when opening HTML practice or starting exams.
Browsing the member catalog and ordinary login must remain unrestricted.

## Mandatory integration points
- GET /member/html-practice and its HTML/data endpoints
- POST /member/start, /member/answer and all exam submit/result APIs
- Any other exam entry and save endpoints in dang_routes.py and exam_paper.py
- ADMIN device review/reset UI

## Security requirements
- Use a persistent, transactional database shared by all Gunicorn workers.
  In-memory dictionaries or Render's ephemeral filesystem are insufficient.
- Bind a random, HttpOnly Secure SameSite cookie to a student account.
  Store only a hash of the device token server-side; do not use IP address as ID.
- Atomically enforce UNIQUE(student_id) and UNIQUE(device_hash).
- A new student-device pair requires approval when either side is already bound.
- Authenticate every protected API on the server; never trust client JavaScript.
- Keep an audit trail and admin-controlled revocation; exempt ADMIN.
- Support existing sessions, reloads and network reconnection.
- Do not bind on login, registration, catalog browsing or logout.
- Browser cookies are not hardware identity: this deters casual sharing but
  cannot absolutely prevent private browsing or cookie deletion.

## Existing code to replace carefully
app.py currently has _DEVICE_SID and _one_device_per_member() which check
nearly all member routes, and server_clean.py calls bind_member_device() on
login. These must be migrated together, not independently.

This branch is a design checkpoint, NOT an active security feature.
Do not deploy it as if device restrictions were enforced.
