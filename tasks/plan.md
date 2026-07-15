# Implementation Plan: Multi-Subject Exam Review App

## Overview

Upgrade the current CSLT exam app into a multi-subject review and mock-exam platform. The app should keep the existing FastAPI + SQLite + TypeScript architecture, add a subject-aware question bank, import the HTTTQL HTML bank, and let users configure subject, number of questions, time limit, chapters/topics, difficulty, and question type before starting an exam.

## Current Baseline

- The workspace app already supports server-side exam attempts, hidden answers before submit, autosave, countdown timer, published exams, and admin review.
- The current data model is single-subject by implication: `canonical_questions` has `topic` and `difficulty`, but no explicit `subject`, `chapter`, or `question_type`.
- Exam generation is fixed to 40 questions with the current `12/8/8/12` difficulty blueprint.
- Attempts are fixed to 30 minutes in the API, even though the schema already stores `time_limit_seconds` and `deadline_at`.
- The downloaded HTTTQL HTML file already has useful labels: `chapter`, `difficulty`, and `type`; the latest `HTTTQL_30_BO_DE_40_CAU_NANG_CAP.html` contains 1,200 questions and added 296 new canonical questions to the existing HTTTQL pool.

## Architecture Decisions

- Keep SQLite as the source of truth and migrate in place. Add subject-aware tables/columns rather than creating a separate database per subject.
- Keep answer secrecy server-side. The frontend should not receive `correctAnswer` or `explanation` until an attempt is submitted.
- Treat "exam configuration" as a first-class input to exam generation. Published exams remain supported, but random/custom attempts should use a configurable blueprint.
- Importers should normalize external data into the existing canonical model with provenance. For the HTTTQL HTML file, map `chapter` to chapter, `type` to question type, and set `subject` to HTTTQL.
- Build vertical slices: first make one imported subject selectable end-to-end, then add richer filters and admin polish.

## Dependency Graph

```text
Subject/question schema
  -> Migration/backfill for existing CSLT data
  -> HTTTQL importer
  -> Subject/catalog API
  -> Configurable exam generator
  -> Attempt creation API
  -> Home setup UI
  -> Exam/result metadata display
  -> Admin import/review UI

Submitted attempt review
  -> Submitted-only result payload and route guard
  -> Result screen answer/explanation states
  -> Latest submitted attempt metadata API
  -> Home "xem lại bài vừa thi" entry point

Subject-aware published exams and history
  -> Published exam metadata with subject/source kind
  -> HTTTQL published blueprint and 10 sample exams
  -> Published exam subject picker
  -> 7-day submitted attempt history API
  -> Home history list with exam tags and completion counts
```

## Task List

### Phase 1: Subject Foundation

- [x] Task 1: Add subject-aware schema and backfill CSLT
- [x] Task 2: Add subject/catalog read APIs
- [x] Task 3: Import HTTTQL HTML into canonical questions

### Checkpoint: Multi-Subject Data Exists

- [x] Existing CSLT attempts/tests still pass
- [x] `subjects` contains CSLT and HTTTQL
- [x] HTTTQL questions import with chapter, difficulty, type, answer, explanation, and provenance

### Phase 2: Configurable Exam Generation

- [x] Task 4: Generalize exam configuration model
- [x] Task 5: Generate exams from subject + filters + question count
- [x] Task 6: Create attempts with custom time limits

### Checkpoint: Configurable Attempt Works

- [x] API can create a 20-question HTTTQL attempt with a 15-minute timer
- [x] API can still create the old 40-question CSLT default attempt
- [x] Missing-pool errors identify the lacking bucket/filter

### Phase 3: Student Experience

- [x] Task 7: Build subject and exam setup UI
- [x] Task 8: Update exam and result views for variable metadata
- [x] Task 9: Add study mode as a separate non-exam flow

### Checkpoint: End-To-End Student Flow

- [x] User selects a subject and starts a custom timed exam
- [x] Timer, progress, navigation, save, submit, and result work for variable question counts
- [x] Answers remain hidden until submit in exam mode

### Phase 4: Review Submitted Attempts

- [x] Task 10: Define the submitted-review API contract and route guard
- [x] Task 11: Polish the result page into a submitted-exam review screen
- [x] Task 12: Add a recent submitted attempt entry point on the home screen

### Checkpoint: Submitted Review Flow

- [x] After submitting, users land on a review page with selected answers, correct answers, unanswered states, and explanations.
- [x] Directly opening a result URL for an in-progress attempt redirects back to the exam page without answer data.
- [x] The home screen can reopen the latest submitted attempt for review after refresh or app restart.

### Phase 5: Subject-Aware Published Exams and 7-Day History

- [x] Task 13: Add subject/source metadata for published exam instances
- [x] Task 14: Publish 10 HTTTQL sample exams with the requested difficulty mix
- [x] Task 15: Add a subject picker for published exams on the home screen
- [x] Task 16: Replace latest submitted attempt metadata with a 7-day history API
- [x] Task 17: Show the 7-day review history on the home screen
- [x] Task 18: Document and verify the HTTTQL published-exam/history upgrade

### Checkpoint: Published Exams and History Work End-to-End

- [x] User can choose a subject before selecting a published exam.
- [x] HTTTQL has 10 published sample exams, each with 40 questions and the requested difficulty mix.
- [x] Home history shows submitted attempts from the last 7 days with "Đề có sẵn" or "Đề ngẫu nhiên" tags.
- [x] Published exam history rows show how many times that exam has been submitted.

### Phase 6: Admin and Release Quality

- [ ] Task 19: Extend admin question list/import controls for subjects
- [ ] Task 20: Add regression tests and data reports
- [ ] Task 21: Update docs, build, and handoff checklist

### Checkpoint: Ready for Review

- [ ] Unit and API tests pass
- [ ] `npm.cmd run build` succeeds
- [ ] Manual smoke test covers CSLT and HTTTQL
- [ ] README documents import, subject setup, and configurable exams

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Existing CSLT flows break during schema migration | High | Add migrations as additive changes and backfill CSLT in tests before changing UI |
| HTTTQL HTML is a large inline JavaScript dataset | Medium | Write a dedicated importer that extracts `SOURCE_QUESTIONS` and validates count/fields |
| Question counts and difficulty filters can request impossible exams | Medium | Return structured insufficient-pool errors before creating attempts |
| Published exams assume fixed 40-question metadata | Medium | Keep published exam compatibility first, then add optional blueprint/config fields |
| Study mode could blur with exam mode and leak answers | High | Separate API/UI mode: study can reveal answer immediately; exam cannot |
| Vietnamese text encoding may regress in scripts/templates | Medium | Keep files UTF-8, add importer tests with Vietnamese chapter/difficulty/type values |
| Published exam history could leak answer data before review | High | Keep the recent-history endpoint metadata-only and link to the existing submitted-only result route |
| HTTTQL sample exams may accidentally reuse or underfill difficulty buckets | Medium | Validate 4 easy, 8 medium, 16 hard, and 12 very-hard questions per 40-question exam before publishing |
| "Đã làm bao nhiêu lần" may be ambiguous | Low | Count submitted attempts for the same published exam instance unless the product decision changes |

## Open Questions

- Should HTTTQL be named "Hệ thống thông tin quản lý" in the UI, or a shorter label like "HTTTQL"?
- Should custom exams preserve the CSLT 12/8/8/12 ratio by default, or simply sample evenly from the selected filters?
- Should teachers/admins be able to create named reusable blueprints, or is per-attempt setup enough for the first version?
- Should the 10 HTTTQL sample exams avoid reusing questions across all 10 exams, or is uniqueness within each exam enough? Recommended: avoid reuse across all 10 because the imported pool is large enough.
- Should "Đã làm X lần" count only submitted attempts, or every started attempt? Recommended: count submitted attempts only.
