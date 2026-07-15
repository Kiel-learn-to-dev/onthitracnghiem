# Task List: Multi-Subject Exam Review App

## Task 1: Add Subject-Aware Schema and Backfill CSLT

**Status:** Completed

**Description:** Add an explicit subject layer to the SQLite schema while preserving existing CSLT data and attempts. Existing questions should become part of a default CSLT subject without changing their current behavior.

**Acceptance criteria:**
- [ ] A `subjects` table exists with stable slug/title fields.
- [ ] `canonical_questions` can be associated with a subject.
- [ ] Existing CSLT questions are backfilled to the CSLT subject.
- [ ] Existing tests that create questions without a subject are updated or supported through a clear default.

**Verification:**
- [ ] Run `py -m unittest tests.test_storage tests.test_exams tests.test_api -v`.
- [ ] Query SQLite and confirm every canonical question has a subject.

**Dependencies:** None

**Files likely touched:**
- `scripts/storage.py`
- `scripts/build_database.py`
- `tests/test_storage.py`
- `tests/test_exams.py`
- `tests/test_api.py`

**Estimated scope:** Medium

## Task 2: Add Subject and Catalog Read APIs

**Status:** Completed

**Description:** Expose the data needed by the setup screen: available subjects, question counts by subject, chapters/topics, difficulties, and question types.

**Acceptance criteria:**
- [ ] `GET /api/subjects` returns subject slug/title and total approved/publishable counts.
- [ ] `GET /api/subjects/{slug}/catalog` returns available chapters/topics, difficulties, and types with counts.
- [ ] Empty subjects or subjects without approved questions return a useful empty state, not a server error.

**Verification:**
- [ ] Add API tests for CSLT subject catalog.
- [ ] Confirm response payloads contain no answers or explanations.

**Dependencies:** Task 1

**Files likely touched:**
- `app.py`
- `tests/test_api.py`

**Estimated scope:** Small

## Task 3: Import HTTTQL HTML Into Canonical Questions

**Status:** Completed

**Description:** Create an importer for the downloaded HTML file that extracts `SOURCE_QUESTIONS`, validates the dataset, creates the HTTTQL subject, and stores questions with chapter, difficulty, question type, answer, explanation, and source provenance.

**Acceptance criteria:**
- [ ] Importer reads `SOURCE_QUESTIONS` from an HTML file and parses the latest 1,200-question HTML export.
- [ ] Each imported question has 4 choices, one A-D answer, explanation, subject, chapter, difficulty, and type.
- [ ] Re-running the importer is idempotent or safely reports existing records.
- [ ] Invalid/missing rows are reported with source IDs.

**Verification:**
- [ ] Add importer unit test using a tiny fixture HTML.
- [ ] Run importer against `F:\Downloads\HTTTQL_30_BO_DE_40_CAU_NANG_CAP.html` on a copy of the database.
- [ ] Generate a count report by difficulty, chapter, and type.

**Dependencies:** Task 1

**Files likely touched:**
- `scripts/import_htttql_html.py`
- `scripts/storage.py`
- `tests/test_import_htttql_html.py`

**Estimated scope:** Medium

## Checkpoint: Multi-Subject Data Exists

- [ ] CSLT remains usable.
- [ ] HTTTQL appears as a separate subject.
- [ ] Data reports show expected HTTTQL distribution: 1,292 canonical questions after importing 296 new questions from the latest 1,200-question HTML file, with no missing core fields.

## Task 4: Generalize Exam Configuration Model

**Status:** Completed

**Description:** Define a reusable exam configuration contract for subject, question count, time limit, chapters/topics, difficulties, and question types. Keep the current fixed CSLT defaults as a compatibility path.

**Acceptance criteria:**
- [ ] Attempt creation input accepts optional `subjectSlug`, `questionCount`, `timeLimitSeconds`, `chapters`, `topics`, `difficulties`, and `questionTypes`.
- [ ] Input validation rejects impossible or unsafe values, such as zero questions or negative time.
- [ ] Existing `examInstanceId` flow for published exams still works unchanged.

**Verification:**
- [ ] API tests cover valid custom config, invalid config, and existing published exam flow.

**Dependencies:** Task 2

**Files likely touched:**
- `app.py`
- `scripts/exams.py`
- `tests/test_api.py`

**Estimated scope:** Medium

## Task 5: Generate Exams From Subject, Filters, and Question Count

**Status:** Completed

**Description:** Extend the exam generator so it selects questions from a requested subject and optional filters. The generator should support variable question counts while keeping deterministic seed behavior.

**Acceptance criteria:**
- [ ] Generated exam contains no duplicate canonical IDs.
- [ ] Same seed and same config produce the same selected canonical IDs.
- [ ] If filters cannot satisfy the request, the error reports which filter/bucket is short.
- [ ] The old 40-question CSLT blueprint remains available as the default.

**Verification:**
- [ ] Unit tests generate custom 10, 20, and 40-question exams.
- [ ] Unit tests cover insufficient pool cases.
- [ ] Existing exam generator tests still pass.

**Dependencies:** Task 4

**Files likely touched:**
- `scripts/exams.py`
- `tests/test_exams.py`

**Estimated scope:** Medium

## Task 6: Create Attempts With Custom Time Limits

**Status:** Completed

**Description:** Wire custom exam configuration into attempt creation and store the requested time limit/deadline on the attempt.

**Acceptance criteria:**
- [ ] A custom attempt stores the requested `total_questions`, `time_limit_seconds`, and `deadline_at`.
- [ ] Published exams use their configured/default time limit.
- [ ] API payload returns the actual question count and timer values.

**Verification:**
- [ ] API test creates a 20-question, 15-minute HTTTQL attempt.
- [ ] API test confirms result scoring uses the custom total.

**Dependencies:** Task 5

**Files likely touched:**
- `app.py`
- `tests/test_api.py`

**Estimated scope:** Small

## Checkpoint: Configurable Attempt Works

- [ ] `POST /api/attempts` can start CSLT and HTTTQL attempts.
- [ ] Timer and total question count in the response match the requested config.
- [ ] Answers/explanations are still hidden before submit.

## Task 7: Build Subject and Exam Setup UI

**Status:** Completed

**Description:** Replace the single-subject home screen with a compact setup screen where users choose subject, mode, question count, time limit, and available filters.

**Acceptance criteria:**
- [ ] Home screen loads subjects and catalog data from the API.
- [ ] User can select subject and configure question count/time limit.
- [ ] Chapter/topic, difficulty, and type filters update based on selected subject.
- [ ] Start button sends the selected config to `POST /api/attempts`.

**Verification:**
- [ ] Run `npm.cmd run build`.
- [ ] Manual check starts one CSLT default attempt and one HTTTQL custom attempt.

**Dependencies:** Task 6

**Files likely touched:**
- `templates/home.html`
- `frontend/app.ts`
- `static/app.js`
- `static/styles.css`

**Estimated scope:** Medium

## Task 8: Update Exam and Result Views for Variable Metadata

**Status:** Completed

**Description:** Make the exam and result screens display subject, question count, selected time, and variable progress text instead of assuming a fixed 40-question CSLT exam.

**Acceptance criteria:**
- [ ] Sidebar/header displays subject name and real question count.
- [ ] Submit dialog uses the actual unanswered count and total, not hardcoded 40.
- [ ] Result title and review navigation work for any question count.
- [ ] Published exam buttons display their real question count/time limit when available.

**Verification:**
- [ ] Manual smoke test with 10, 20, and 40-question attempts.
- [ ] Run `npm.cmd run build`.

**Dependencies:** Task 7

**Files likely touched:**
- `templates/exam.html`
- `templates/result.html`
- `frontend/app.ts`
- `static/styles.css`

**Estimated scope:** Small

## Task 9: Add Study Mode as a Separate Flow

**Status:** Completed

**Description:** Add an "ôn tập" mode that allows immediate feedback after answering, separate from timed mock exams where answers stay hidden until submit.

**Acceptance criteria:**
- [x] Setup screen offers `Thi thử` and `Ôn tập` modes.
- [x] Exam mode does not reveal answers before submit.
- [x] Study mode can reveal correctness and explanation after each answer.
- [x] Study mode progress can be restarted without affecting exam attempts.

**Verification:**
- [x] API/UI tests or manual checks prove answer secrecy differs by mode.
- [x] Manual check answers one study question and sees explanation immediately.

**Dependencies:** Task 8

**Files likely touched:**
- `app.py`
- `frontend/app.ts`
- `templates/exam.html`
- `static/styles.css`
- `tests/test_api.py`

**Estimated scope:** Medium

## Checkpoint: End-To-End Student Flow

- [x] User can choose CSLT or HTTTQL.
- [x] User can configure question count and timer.
- [x] Timed exam and study mode behave differently and correctly.

## Task 10: Define the Submitted-Review API Contract and Route Guard

**Status:** Completed

**Description:** Make the backend contract for reviewing a submitted attempt explicit. The attempt API should reveal answers only after submit, report enough summary counts for the result page, and keep direct result-page access for in-progress attempts from leaking answer data.

**Acceptance criteria:**
- [x] `GET /api/attempts/{attempt_id}` includes answer/explanation fields only when `status = submitted`.
- [x] Submitted payload includes correct, wrong, unanswered, score, and total question counts derived server-side.
- [x] In-progress attempts keep returning enough metadata for the exam page, but never include `correctAnswer` or `explanation`.

**Verification:**
- [x] API test covers in-progress payload secrecy, submitted payload reveal, unanswered count, and idempotent submit.
- [x] Existing study-mode test still proves immediate feedback is limited to answered study questions.

**Dependencies:** Task 8

**Files likely touched:**
- `app.py`
- `tests/test_api.py`

**Estimated scope:** Small

## Task 11: Polish the Result Page Into a Submitted-Exam Review Screen

**Status:** Completed

**Description:** Turn the existing result page into the clear "xem lại đề vừa thi kèm đáp án" experience. It should show the user's choice, the correct answer, correctness state, explanation, and an accessible navigation state for every question.

**Acceptance criteria:**
- [x] After submit, the app navigates to `/result/{attempt_id}` and labels it clearly as submitted review.
- [x] Each question displays selected answer, correct answer, correctness status, and explanation.
- [x] Unanswered questions are labeled as unanswered, not merely wrong.
- [x] Review navigation remains usable for 10, 20, 40, and 100+ question attempts without relying only on color.

**Verification:**
- [x] `npm.cmd run build` succeeds.
- [x] Template test covers the review summary container and unanswered frontend state.
- [ ] Manual narrow-width browser check confirms answer labels and navigation do not overlap.

**Dependencies:** Task 10

**Files likely touched:**
- `templates/result.html`
- `frontend/app.ts`
- `static/styles.css`

**Estimated scope:** Medium

## Task 12: Add a Recent Submitted Attempt Entry Point

**Status:** Completed

**Description:** Let users reopen the most recent submitted attempt from the home screen so "xem lại đề vừa thi" still works after navigation, refresh, or app restart.

**Acceptance criteria:**
- [x] API exposes latest submitted attempt metadata without answer content in list responses.
- [x] Home screen shows a compact "Xem lại bài vừa thi" action only when a submitted attempt exists.
- [x] The action opens `/result/{attempt_id}` for the latest submitted attempt.
- [x] A newer in-progress attempt does not replace the latest submitted review link.

**Verification:**
- [x] API test covers no submitted attempts, one submitted attempt, and an in-progress newer attempt.
- [x] `npm.cmd run build` succeeds.
- [x] Template test covers the home recent-attempt entry point and frontend endpoint.

**Dependencies:** Task 11

**Files likely touched:**
- `app.py`
- `templates/home.html`
- `frontend/app.ts`
- `static/styles.css`
- `tests/test_api.py`

**Estimated scope:** Medium

## Task 13: Add Subject and Source Metadata for Published Exam Instances

**Status:** Completed

**Description:** Make predefined exams first-class, subject-aware records so the app can tell a published exam from a random/custom exam and filter predefined exams by subject.

**Acceptance criteria:**
- [x] Published exam instances can be associated with a subject such as CSLT or HTTTQL.
- [x] Exam instances expose a stable source kind, at minimum `published` for predefined exams and `random` for generated exams.
- [x] Existing published CSLT exams are backfilled without breaking existing attempts.
- [x] Existing random/custom attempts still open and submit normally after migration.

**Verification:**
- [x] Run storage and exam generator tests that cover migration/backfill.
- [x] Run API tests that distinguish published and random exam metadata.

**Dependencies:** Task 12

**Files likely touched:**
- `scripts/storage.py`
- `scripts/exams.py`
- `tests/test_storage.py`
- `tests/test_exams.py`

**Estimated scope:** Medium

## Task 14: Publish 10 HTTTQL Sample Exams With the Requested Difficulty Mix

**Status:** Completed

**Description:** Add an idempotent data path to create 10 predefined HTTTQL exams. Each exam should contain 40 questions using the requested internal mix: 4 easy, 8 medium, 16 hard, and 12 very hard. This ratio is implementation data only and should not be displayed in the student UI.

**Acceptance criteria:**
- [x] Exactly 10 HTTTQL published sample exams are created or updated idempotently.
- [x] Each sample exam has 40 questions with 4 `Dễ`, 8 `Vừa`, 16 `Khó`, and 12 `Rất khó` questions.
- [x] No question is duplicated inside the same sample exam.
- [x] The public published-exam payload does not reveal the difficulty ratio.

**Verification:**
- [x] Run unit tests for HTTTQL sample-exam generation and idempotency.
- [x] Run a local data check/report proving all 10 exams satisfy the bucket counts.

**Dependencies:** Task 13

**Files likely touched:**
- `scripts/exams.py`
- `scripts/storage.py`
- `tests/test_exams.py`
- `tests/test_api.py`

**Estimated scope:** Medium

## Task 15: Add a Subject Picker for Published Exams on the Home Screen

**Status:** Completed

**Description:** Update the existing "đề có sẵn" flow so students choose a subject before selecting a predefined exam, and only exams for that subject are shown.

**Acceptance criteria:**
- [x] `GET /api/exams/published` supports filtering by subject slug or subject id.
- [x] The home screen includes a subject control for the predefined-exam section.
- [x] Changing the selected subject refreshes the predefined exam list.
- [x] Empty states are clear when a subject has no predefined exams.

**Verification:**
- [x] API tests cover published-exam filtering by subject.
- [x] Template/UI tests cover the published subject selector.
- [ ] Manual smoke test starts one CSLT predefined exam and one HTTTQL predefined exam.

**Dependencies:** Task 13, Task 14

**Files likely touched:**
- `app.py`
- `templates/home.html`
- `frontend/app.ts`
- `frontend/styles.css`
- `tests/test_api.py`

**Estimated scope:** Medium

## Checkpoint: Published Exam Selection Works

- [x] User can choose a subject in the predefined-exam area.
- [x] HTTTQL shows 10 predefined sample exams.
- [x] The UI does not show the internal 10/20/40/30 difficulty ratio.
- [x] `npm.cmd run build` succeeds after frontend changes.

## Task 16: Replace Latest Submitted Attempt Metadata With a 7-Day History API

**Status:** Completed

**Description:** Expand the recent-attempt metadata API from one latest submitted attempt into a metadata-only list of submitted attempts from the last 7 days.

**Acceptance criteria:**
- [x] A recent-history endpoint returns submitted attempts from the last 7 days, newest first.
- [x] The endpoint excludes in-progress attempts and attempts older than 7 days.
- [x] Each row includes attempt id, subject/title metadata, submitted time, score summary, source tag data, and result URL.
- [x] Published exam rows include the number of submitted attempts for that same predefined exam.
- [x] The endpoint does not include questions, correct answers, explanations, or per-question user answers.

**Verification:**
- [x] API tests cover submitted, in-progress, older-than-7-days, published, and random attempts.
- [x] Route guard tests confirm answer data is still only available through submitted result review.

**Dependencies:** Task 13

**Files likely touched:**
- `app.py`
- `scripts/storage.py`
- `tests/test_api.py`
- `tests/test_storage.py`

**Estimated scope:** Medium

## Task 17: Show the 7-Day Review History on the Home Screen

**Status:** Completed

**Description:** Replace the single "xem lại đề gần nhất" entry point with a compact history list for all submitted attempts in the last 7 days.

**Acceptance criteria:**
- [x] The home screen lists submitted attempts from the last 7 days instead of only one latest attempt.
- [x] Published exam attempts show tag `Đề có sẵn`.
- [x] Random/custom attempts show tag `Đề ngẫu nhiên`.
- [x] Published exam attempts show `Đã làm X lần` using the API count.
- [x] Each row links to `/result/{attemptId}` for review with answers and explanations.

**Verification:**
- [x] Frontend build succeeds with `npm.cmd run build`.
- [x] Template/UI tests cover tags, count labels, empty state, and result links.
- [ ] Manual smoke test submits two attempts and confirms both appear in history.

**Dependencies:** Task 16

**Files likely touched:**
- `templates/home.html`
- `frontend/app.ts`
- `frontend/styles.css`
- `static/app.js`
- `static/styles.css`

**Estimated scope:** Medium

## Task 18: Document and Verify the HTTTQL Published-Exam/History Upgrade

**Status:** Completed

**Description:** Update the project notes and verification checklist for the new predefined HTTTQL exam set, subject picker, and 7-day attempt history.

**Acceptance criteria:**
- [x] README explains how to create or refresh the 10 HTTTQL predefined exams.
- [x] README documents that the recent-history list covers submitted attempts within 7 days.
- [x] A verification note or report lists the HTTTQL predefined exam count and difficulty bucket totals.
- [x] The handoff checklist includes backup before republishing sample exams.

**Verification:**
- [x] Run `py -m unittest discover -s tests -v`.
- [x] Run `npm.cmd run build`.
- [ ] Start the app and manually verify subject-filtered predefined exams plus 7-day history.

**Dependencies:** Task 15, Task 17

**Files likely touched:**
- `README.md`
- `tasks/plan.md`
- `tasks/todo.md`
- `scripts/report_question_bank.py`

**Estimated scope:** Small

## Checkpoint: Published Exams and History Work End-to-End

- [x] User can choose a subject before selecting a predefined exam.
- [x] HTTTQL has 10 published sample exams with the requested hidden difficulty mix.
- [x] The home screen shows submitted attempts from the last 7 days.
- [x] Published and random attempts have the correct tags and review links.

## Task 19: Extend Admin Question List and Import Controls

**Description:** Update admin tools so question management is subject-aware and the HTTTQL importer can be run or documented through an admin-safe workflow.

**Acceptance criteria:**
- [ ] Admin question list can filter by subject.
- [ ] Admin rows show subject, topic/chapter, difficulty, and type.
- [ ] Import/report workflow clearly shows counts and rejected rows.
- [ ] Admin token protections remain unchanged.

**Verification:**
- [ ] API tests cover admin subject filtering.
- [ ] Manual admin check confirms HTTTQL rows are visible and separated from CSLT.

**Dependencies:** Task 3, Task 6, Task 15

**Files likely touched:**
- `app.py`
- `templates/admin.html`
- `frontend/app.ts`
- `tests/test_api.py`

**Estimated scope:** Medium

## Task 20: Add Regression Tests and Data Reports

**Description:** Add focused test coverage and reporting scripts for the new multi-subject behavior so future imports, predefined exams, history, and exam configs are easy to verify.

**Acceptance criteria:**
- [ ] Tests cover subject migration, catalog API, HTTTQL import, custom exam generation, custom attempt timing, predefined exam filtering, and 7-day history.
- [ ] Report script summarizes counts by subject, chapter/topic, difficulty, type, publishable status, and predefined exam coverage.
- [ ] Test fixtures avoid depending on the large downloaded HTML file.

**Verification:**
- [ ] Run `py -m unittest discover -s tests -v`.
- [ ] Run the report script against the local database.

**Dependencies:** Task 18, Task 19

**Files likely touched:**
- `tests/test_storage.py`
- `tests/test_api.py`
- `tests/test_exams.py`
- `tests/test_import_htttql_html.py`
- `scripts/report_question_bank.py`

**Estimated scope:** Medium

## Task 21: Update Docs, Build, and Handoff Checklist

**Description:** Update project documentation for multi-subject usage, importing HTTTQL, configuring exams, predefined exam subjects, attempt history, and validating a release.

**Acceptance criteria:**
- [ ] README explains subjects, import flow, custom exam setup, predefined exam setup, history behavior, and timer/question-count configuration.
- [ ] Build instructions remain valid for web and desktop packaging.
- [ ] Handoff checklist includes database backup before import/migration/sample-exam refresh.

**Verification:**
- [ ] Run `npm.cmd run build`.
- [ ] Run `py -m unittest discover -s tests -v`.
- [ ] Manually start the app and complete one CSLT or HTTTQL attempt.

**Dependencies:** Task 20

**Files likely touched:**
- `README.md`
- `tasks/plan.md`
- `tasks/todo.md`

**Estimated scope:** Small
