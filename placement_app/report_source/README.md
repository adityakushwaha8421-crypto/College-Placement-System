# Project report source

This creates the 41-page College Placement Management System report for Tushar Lallu Kharwar using the supplied college report as the layout reference. It preserves the college/department, guide Mrs. M. D. Hindurao, logo, degree, academic year 2026-27, front matter and chapter order. Personal signatures and dates are left blank.

- `content.py`: report prose and institutional details.
- `build_report.py`: PDF layout, vector diagrams and excerpts from the actual application source.
- `assets/`: college logo extracted from the supplied reference and six screenshots captured from the working placement app using fictional demo records.

Rebuild from the application folder using Python with ReportLab installed:

```sh
.venv/bin/python report_source/build_report.py
```

The output is `output/pdf/COLLEGE_PLACEMENT_TUSHAR_LALLU_KHARWAR.pdf`. Application code excerpts are read from the local project at build time. The generation step does not change the placement database or accounts.

The report documents the local app and recorded test results; proposed enhancements are explicitly separated from implemented features. College signature/seal sections are unsigned template areas for completion by the appropriate people.
