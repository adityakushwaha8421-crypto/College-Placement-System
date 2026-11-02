# PlacementOS — College Placement Management System

A working local Django application built from the supplied static placement-system mockups and project guide. The original mockups, SQL reference, screenshots, and video are preserved in the parent package. The application uses its own Django-managed SQLite database; do not import the reference SQL into it.

## Run on this Mac

Double-click `start.command`, or run:

```sh
cd /Users/adity/Downloads/College_Placement_System_Package/placement_app
./start.command
```

Open http://127.0.0.1:3001/. Stop the server with Ctrl+C. An alternate port is supported with `./start.command 3003`. The existing running app already has its dependencies installed.

On another computer, install Python 3.12 or newer and run the following from this folder (tested here with Python 3.14.5 and Django 5.2.18):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver 127.0.0.1:3001 --noreload
```

On Windows, use `py` to create the environment and `.venv\Scripts\python.exe` in place of `.venv/bin/python`.

## Local demo accounts

All sample people, companies, openings, and recruitment records are fictional. Select a role on the login screen to fill its credentials.

| Role | Email | Password |
| --- | --- | --- |
| Placement officer | admin@college.edu | Campus@2027! |
| Student | student@college.edu | Campus@2027! |
| Recruiter | hr@northstar.example | Campus@2027! |

`seed_demo` creates missing sample records without resetting existing passwords, approvals, applications, or interview times. The starter includes eight approved students, one pending student, four approved recruiters, eight open opportunities, one pending opportunity, and a mix of applications and selections. Deadlines are set relative to the initial seed date. Existing expired openings remain expired when reseeding; edit them explicitly if needed.

## What works

- **Accounts:** student/recruiter registration, password hashing and validation, email sign-in, POST logout, password changes, session authentication, CSRF protection, and role-based access.
- **Placement officers:** approve or decline student/recruiter accounts; review, approve, edit, or close openings; oversee candidates and interviews; export filtered placement reports as CSV or PDF.
- **Students:** maintain an academic profile, upload a private PDF resume, search openings by role/company/location/branch, filter by eligibility, apply with a cover note, track outcomes, withdraw active applications, view interviews, and download selection confirmations.
- **Recruiters:** maintain their company profile, submit/edit openings for review, see only their own candidate pipeline, access resumes from students who applied to them, shortlist/reject/select candidates, and schedule/reschedule interviews.
- **Reporting:** actual database totals, per-branch placement rates, placed/seeking register, company selections, highest package, and average best package per placed student. A student with multiple selections counts once in the placement rate.
- **Interface:** responsive desktop/mobile views, searchable and paginated tables, empty states, feedback messages, confirmation dialogs, keyboard focus states, and bundled CSS/icons with no CDN requirements.

## Workflow rules

1. New accounts start pending. Only officers can approve accounts.
2. Recruiter-created or recruiter-edited openings return to review. A company must be approved and the deadline current before the officer opens a role.
3. Applications require an approved student, matching branch, sufficient CGPA, acceptable backlogs, an approved recruiter, an open role, and a current deadline.
4. Each student can apply to an opening once. A withdrawn application cannot be resubmitted to the same opening.
5. Candidates progress from Applied → Shortlisted → Selected or Rejected. Applied candidates may also be rejected. Selected, rejected, and withdrawn decisions are final through the application interface.
6. Only shortlisted candidates can be scheduled. Future times, a 15–240 minute duration, an HTTP(S) online meeting URL, and no overlapping active interviews are required. Withdrawn interviews disappear from the schedule; decided interviews remain as history.
7. Changes to student identity/academic details or company identity trigger renewed approval. Contact/resume-only edits do not.
8. Selection company name, job title, package, and date are saved at selection time. Later opening edits do not rewrite these confirmation facts or package statistics.

## Files and persistence

- `db.sqlite3`: live accounts, sessions, jobs, applications, interviews, activity, and selections.
- `private_uploads/`: resumes with generated filenames; there is no public media route. Downloads require a permitted account and are sent as attachments.
- `.local-secret`: generated local session-signing key, created with owner-only permissions.
- `portal/migrations/`: versioned schema migrations, including preserved selection facts, case-insensitive email uniqueness, and the resume cleanup queue.
- Superseded resume deletions that fail are kept in the database for retry; `manage.py cleanup_resumes` retries them without deleting a currently referenced resume. The startup script also retries this queue. Failed database saves clean up newly written uploads.
- `templates/` and `static/`: server-rendered pages and local assets.
- `qa/`: repeatable browser checks; generated evidence belongs in `qa/artifacts/`.

Keep the database, uploads, and local secret together when backing up an existing installation. The portable source ZIP excludes live databases, signing keys, uploads, and the virtual environment; a fresh install generates its own state.

## Validation

```sh
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test
.venv/bin/python -m pip check
```

Browser QA uses an optional installed Playwright module and Chromium; neither is required to run the app. `qa/smoke.cjs` checks the three demo roles, pages, export routes, empty search results, and mobile overflow/navigation. It accepts `PLACEMENT_PLAYWRIGHT` (module location), `PLACEMENT_CHROMIUM` (browser executable), and optional `PLACEMENT_BASE`.

`qa/e2e.cjs` creates records and must run against an isolated test database/server. Configure the server with `PLACEMENT_DB_PATH=qa/qa.sqlite3` and `PLACEMENT_UPLOAD_DIR=qa/artifacts/uploads`. Run migrations and seed that database, then start it on a spare port. Set `PLACEMENT_BASE` and `PLACEMENT_QA_ISOLATED=1` for the E2E runner. It exercises registration, approvals, posting, applying, uploading, shortlisting, scheduling, selection, report exports, and persistence across sign-in.

See `QA-REPORT.md` for checks executed on this build.

## Scope and limits

This is a local college-project application served on loopback with Django's development server. It is not configured as a publicly hosted production service. It has no external email/SMS delivery, calendar-provider integration, AI resume parser, automated aptitude platform, or real employer connection. Interview updates appear inside the portal. Online meeting URLs are entered by the recruiter; meetings are not provisioned automatically.

Selection PDFs confirm what is recorded in the campus portal; they are not signed employer offer letters. Reports export PDF and CSV; printable pages can also be saved with the browser. Resume uploads validate PDF signature/extension and size, but do not provide malware scanning or content verification. No forgotten-password email flow is provided; users can change a known password, and a local operator can use `manage.py changepassword EMAIL` to reset one.

Before any public deployment, replace the demo accounts, configure a production WSGI/ASGI server and static serving, HTTPS/cookie settings, allowed hosts, secret management, backups, authentication throttling, upload scanning, and an appropriate production database. SQLite write workflows use IMMEDIATE transactions. Simultaneous duplicate application and overlapping interview requests were checked against the local server; this does not establish behavior under production-scale load or on another database. The local development server has not been load-tested.

## Review fixes — 31 October 2026

See `REVIEW-FIXES.md` for reproduced defects, fixes, and verification. The review adds `portal/test_review.py` and `qa/review.cjs`. Registration ignores fields from the other role on both client and server; malformed meeting links and record IDs return validation feedback or 404 rather than exceptions. Email login uniqueness is enforced case-insensitively in SQLite. Existing applicants can still read an opening after it closes or goes back into review. Application search/job filters survive status chips and decision actions. Selection names/packages shown in applications and interview history use their saved facts.

Authenticated pages and exports use `private, no-store` cache control. Unknown workspace roles fail closed but can still sign out. Mobile navigation removes the collapsed sidebar from keyboard focus, focuses it when opened, and returns focus on Escape. Officer profiles use personal labels, and `createsuperuser` creates an approved placement officer. Students no longer see already-applied roles counted as new eligible openings. Inactive recruitment accounts cannot accept applications.
