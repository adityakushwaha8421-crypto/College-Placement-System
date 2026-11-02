# PlacementOS verification

Latest project review: **31 October 2026**. Tested locally with Python 3.14.5, Django 5.2.18, SQLite, and existing Chromium.

| Check | Latest result |
| --- | --- |
| Django test suite | 46 passed; final run 4.836 seconds |
| Browser smoke suite | 49 passed |
| Full recruitment browser suite | 14 passed against isolated review data |
| Focused review browser/API suite | 22 passed, including simultaneous applications and conflicting interviews |
| Django system check | No issues |
| Migration drift check | No changes detected |
| Dependency consistency | No broken requirements |
| First-party Python parsing | Passed |
| `start.command` shell syntax | Passed |
| Resume cleanup queue | 0 pending in live database |

See `REVIEW-FIXES.md` for the defects, root causes, structural fixes, evidence, and verification limits. The original build's 26 backend tests remain, with 20 additional review regressions. Current browser results are retained under `qa/artifacts/` as `smoke-results.json`, `e2e-results.json`, and `review-browser-results.json`. Screenshots and a test selection PDF are also retained locally.

Browser mutations used a separate SQLite database and upload directory on a temporary test server. The user's live placement records were not seeded or reset during review. The live app received schema migrations after a consistent database/source backup. The temporary QA server was stopped when verification finished.

This verifies the local development app, not public hosting, sustained load, all concurrency interleavings, external integrations, malware scanning, full screen-reader conformance, or signed employer offers. See `README.md` for the supported scope and startup instructions.
