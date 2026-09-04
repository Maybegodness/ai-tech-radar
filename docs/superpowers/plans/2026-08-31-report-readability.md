# Report Readability Implementation Plan

> **For agentic workers:** Execute the tasks in this plan in order and verify each slice before continuing.

**Goal:** Separate project updates from ModelScope new models and make generated reports easier to scan.

**Architecture:** Keep fetching functions and their structured fields unchanged. Narrow the change to `build_report` prompts, section labels, and date rendering, with one helper for compact ISO timestamps.

**Tech Stack:** Python 3.13, `datetime`, existing `requests` and TOML configuration.

---

### Task 1: Add compact date formatting

**Files:**
- Modify: `scan.py`

- [x] Add a helper that converts ISO timestamps with `T`/`Z` or offsets to `YYYY-MM-DD HH:MM`, returning the original value only when parsing fails.
- [x] Use it for the report generation timestamp and model `CreatedAt` data passed to prompts.
- [x] Verify with aware and naive timestamp examples.

### Task 2: Restructure report sections and prompts

**Files:**
- Modify: `scan.py`

- [x] Keep watch repository releases under the project section and remove their `发布时间` line.
- [x] Change release prompts to request one concise paragraph focused on what changed and why it matters.
- [x] Keep GitHub search results in their own project section.
- [x] Keep ModelScope models only in the model section; remove standalone learning-value and repeated one-line labels.
- [x] Make model prompts prioritize model purpose/capabilities, then deployment or attention rationale.

### Task 3: Update documentation and verify output

**Files:**
- Modify: `README.md`

- [x] Document the three report sections and compact timestamps.
- [x] Run Python compilation and a mocked report-generation check asserting section separation and absence of legacy labels/timestamps.
- [x] Run `git diff --check`.
