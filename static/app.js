"use strict";
const page = document.body.dataset.page;
const attemptId = document.body.dataset.attemptId;
async function request(url, options = {}) {
    const response = await fetch(url, {
        headers: { "Content-Type": "application/json", ...options.headers },
        ...options,
    });
    if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.error?.message ?? "Không thể hoàn tất yêu cầu.");
    }
    return response.json();
}
function setText(selector, value) {
    const element = document.querySelector(selector);
    if (element)
        element.textContent = value;
}
function formatDateInputValue(date = new Date()) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}
async function startAttempt(payload = {}, button) {
    const status = document.querySelector("#home-status");
    if (button)
        button.disabled = true;
    setText("#home-status", "Đang tạo đề…");
    try {
        const attempt = await request("/api/attempts", { method: "POST", body: JSON.stringify(payload) });
        window.location.assign(`/exam/${attempt.attemptId}`);
    }
    catch (error) {
        setText("#home-status", error instanceof Error ? error.message : "Có lỗi xảy ra.");
        if (button)
            button.disabled = false;
    }
}
function publishedExamButton(exam) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "published-exam";
    const title = document.createElement("strong");
    title.textContent = exam.title;
    const detail = document.createElement("span");
    detail.textContent = `${exam.questionCount} câu · 30 phút`;
    button.append(title, detail);
    button.addEventListener("click", () => void startAttempt({ examInstanceId: exam.id }, button));
    return button;
}
async function setupRecentAttempt(filters = {}) {
    const list = document.querySelector("#recent-attempt-list");
    if (!list)
        return;
    list.setAttribute("aria-busy", "true");
    try {
        const params = new URLSearchParams({ days: "7" });
        if (filters.subjectSlug)
            params.set("subjectSlug", filters.subjectSlug);
        if (filters.submittedDate)
            params.set("submittedDate", filters.submittedDate);
        const response = await request(`/api/attempts/recent?${params.toString()}`);
        if (!response.data.length) {
            const empty = document.createElement("p");
            empty.className = "history-empty";
            empty.textContent = filters.subjectSlug || filters.submittedDate ? "Không có bài đã nộp khớp bộ lọc." : "Chưa có bài đã nộp trong 7 ngày gần đây.";
            list.replaceChildren(empty);
            return;
        }
        list.replaceChildren(...response.data.map((attempt) => {
            const link = document.createElement("a");
            link.className = "history-item";
            link.href = attempt.resultUrl;
            const tag = document.createElement("span");
            tag.className = `history-tag ${attempt.tag === "Đề có sẵn" ? "is-published" : "is-random"}`;
            tag.textContent = attempt.tag;
            const title = document.createElement("strong");
            title.textContent = `${attempt.title} · ${attempt.subject.title}`;
            const meta = document.createElement("span");
            const submittedAt = attempt.submittedAt ? new Date(attempt.submittedAt).toLocaleString("vi-VN") : "gần đây";
            const completedLabel = attempt.completedCountForExam ? ` · Đã làm ${attempt.completedCountForExam} lần` : "";
            meta.textContent = `${submittedAt}${completedLabel}`;
            const score = document.createElement("span");
            score.className = "history-score";
            score.textContent = `${attempt.score}/${attempt.totalQuestions}`;
            link.append(tag, title, meta, score);
            return link;
        }));
    }
    catch {
        const error = document.createElement("p");
        error.className = "history-empty";
        error.textContent = "Không thể tải lịch sử làm bài.";
        list.replaceChildren(error);
    }
    finally {
        list.setAttribute("aria-busy", "false");
    }
}
async function setupHome() {
    const form = document.querySelector("#exam-setup");
    const startButton = document.querySelector("#start-exam");
    const subjectSelect = document.querySelector("#subject-select");
    const publishedSubjectSelect = document.querySelector("#published-subject-select");
    const historySubjectSelect = document.querySelector("#history-subject-select");
    const historyDateInput = document.querySelector("#history-date-input");
    const clearHistoryFilters = document.querySelector("#clear-history-filters");
    const modeSelect = document.querySelector("#mode-select");
    const questionCountInput = document.querySelector("#question-count");
    const timeLimitSelect = document.querySelector("#time-limit");
    const chapterSelect = document.querySelector("#chapter-select");
    const difficultySelect = document.querySelector("#difficulty-select");
    const questionTypeSelect = document.querySelector("#question-type-select");
    if (historyDateInput && !historyDateInput.value)
        historyDateInput.value = formatDateInputValue();
    const refreshHistory = () => void setupRecentAttempt({
        subjectSlug: historySubjectSelect?.value || undefined,
        submittedDate: historyDateInput?.value || undefined,
    });
    const resetSelect = (select, label, items) => {
        if (!select)
            return;
        select.replaceChildren(new Option(label, ""), ...items.map((item) => new Option(`${item.value} (${item.count})`, item.value)));
    };
    const setupCatalog = async (slug) => {
        try {
            const catalog = await request(`/api/subjects/${encodeURIComponent(slug)}/catalog`);
            resetSelect(chapterSelect, "Tất cả", catalog.data.chapters);
            resetSelect(difficultySelect, "Tất cả", catalog.data.difficulties);
            resetSelect(questionTypeSelect, "Tất cả", catalog.data.questionTypes);
            setText("#catalog-summary", `${catalog.data.questionCount} câu có thể tạo đề`);
            if (questionCountInput)
                questionCountInput.max = String(Math.max(1, catalog.data.questionCount));
        }
        catch (error) {
            setText("#catalog-summary", error instanceof Error ? error.message : "Không thể tải cấu hình môn học.");
        }
    };
    const setupPublishedExams = async (slug) => {
        const container = document.querySelector("#published-exams");
        const randomPublishedButton = document.querySelector("#random-published-exam");
        if (!container)
            return;
        container.setAttribute("aria-busy", "true");
        try {
            const published = await request(`/api/exams/published?subjectSlug=${encodeURIComponent(slug)}`);
            if (published.data.length) {
                container.replaceChildren(...published.data.map(publishedExamButton));
            }
            else {
                const empty = document.createElement("p");
                empty.className = "published-empty";
                empty.textContent = "Môn này chưa có đề sẵn.";
                container.replaceChildren(empty);
            }
            if (randomPublishedButton) {
                randomPublishedButton.disabled = !published.data.length;
                randomPublishedButton.onclick = () => {
                    const exam = published.data[Math.floor(Math.random() * published.data.length)];
                    if (exam)
                        void startAttempt({ examInstanceId: exam.id }, randomPublishedButton);
                };
            }
        }
        catch (error) {
            setText("#home-status", error instanceof Error ? error.message : "Không thể tải danh sách đề.");
        }
        finally {
            container.setAttribute("aria-busy", "false");
        }
    };
    try {
        const subjects = await request("/api/subjects");
        subjectSelect?.replaceChildren(...subjects.data.map((subject) => new Option(`${subject.title} (${subject.questionCount})`, subject.slug)));
        publishedSubjectSelect?.replaceChildren(...subjects.data.map((subject) => new Option(subject.title, subject.slug)));
        historySubjectSelect?.replaceChildren(new Option("Tất cả môn", ""), ...subjects.data.map((subject) => new Option(subject.title, subject.slug)));
        if (subjects.data[0]) {
            await setupCatalog(subjects.data[0].slug);
            await setupPublishedExams(subjects.data[0].slug);
        }
        else
            setText("#catalog-summary", "Chưa có môn học nào.");
    }
    catch (error) {
        setText("#catalog-summary", error instanceof Error ? error.message : "Không thể tải danh sách môn học.");
    }
    subjectSelect?.addEventListener("change", () => void setupCatalog(subjectSelect.value));
    publishedSubjectSelect?.addEventListener("change", () => void setupPublishedExams(publishedSubjectSelect.value));
    historySubjectSelect?.addEventListener("change", refreshHistory);
    historyDateInput?.addEventListener("change", refreshHistory);
    clearHistoryFilters?.addEventListener("click", () => {
        if (historySubjectSelect)
            historySubjectSelect.value = "";
        if (historyDateInput)
            historyDateInput.value = "";
        refreshHistory();
    });
    refreshHistory();
    form?.addEventListener("submit", (event) => {
        event.preventDefault();
        const payload = {
            subjectSlug: subjectSelect?.value || undefined,
            mode: modeSelect?.value || "exam",
            questionCount: Number(questionCountInput?.value || 40),
            timeLimitSeconds: Number(timeLimitSelect?.value || 1800),
        };
        if (chapterSelect?.value)
            payload.chapters = [chapterSelect.value];
        if (difficultySelect?.value)
            payload.difficulties = [difficultySelect.value];
        if (questionTypeSelect?.value)
            payload.questionTypes = [questionTypeSelect.value];
        void startAttempt(payload, startButton ?? undefined);
    });
}
function renderNavigation(attempt, activeIndex, choose) {
    const navigation = document.querySelector("#question-nav");
    if (!navigation)
        return;
    navigation.replaceChildren();
    attempt.questions.forEach((question, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = String(index + 1);
        button.className = `question-link${index === activeIndex ? " is-active" : ""}${question.selectedAnswer ? " is-answered" : ""}${question.markedForReview ? " is-marked" : ""}`;
        button.setAttribute("aria-label", `Câu ${index + 1}`);
        button.addEventListener("click", () => choose(index));
        navigation.append(button);
    });
}
function renderQuestion(attempt, activeIndex, save, choose) {
    const question = attempt.questions[activeIndex];
    setText("#progress-text", `Câu ${activeIndex + 1} / ${attempt.questions.length}`);
    setText("#question-topic", [question.chapter || question.topic, question.questionType, question.difficulty].filter(Boolean).join(" · "));
    setText("#question-title", question.question);
    const assumptions = document.querySelector("#question-assumptions");
    if (assumptions) {
        assumptions.hidden = !question.assumptions;
        assumptions.textContent = question.assumptions ? `Giả định: ${question.assumptions}` : "";
    }
    const choices = document.querySelector("#choices");
    if (choices) {
        choices.disabled = false;
        choices.replaceChildren();
        question.choices.forEach((choice, choiceIndex) => {
            const label = document.createElement("label");
            label.className = "choice";
            const input = document.createElement("input");
            input.type = "radio";
            input.name = "choice";
            input.value = "ABCD"[choiceIndex];
            input.checked = question.selectedAnswer === input.value;
            input.addEventListener("change", () => {
                question.selectedAnswer = input.value;
                save(question);
                renderNavigation(attempt, activeIndex, choose);
            });
            const key = document.createElement("span");
            key.className = "choice-key";
            key.textContent = input.value;
            const copy = document.createElement("span");
            copy.textContent = choice;
            label.append(input, key, copy);
            choices.append(label);
        });
    }
    const feedback = document.querySelector("#study-feedback");
    if (feedback) {
        const canShowFeedback = attempt.mode === "study" && question.selectedAnswer && question.correctAnswer;
        feedback.hidden = !canShowFeedback;
        feedback.className = `study-feedback${question.isCorrect ? " is-correct" : " is-wrong"}`;
        feedback.replaceChildren();
        if (canShowFeedback) {
            const title = document.createElement("strong");
            title.textContent = question.isCorrect ? "Chính xác." : `Chưa chính xác. Đáp án đúng là ${question.correctAnswer}.`;
            const explanation = document.createElement("p");
            explanation.textContent = question.explanation ?? "";
            feedback.append(title, explanation);
        }
    }
    document.querySelector("#question-title")?.focus();
}
function formatRemainingTime(deadlineAt) {
    const milliseconds = deadlineAt ? Math.max(0, Date.parse(deadlineAt) - Date.now()) : 0;
    const seconds = Math.ceil(milliseconds / 1000);
    return { label: `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`, expired: seconds === 0 };
}
async function setupExam() {
    if (!attemptId)
        return;
    const content = document.querySelector(".exam-content");
    const saveStatus = document.querySelector("#save-status");
    try {
        const attempt = await request(`/api/attempts/${attemptId}`);
        if (attempt.status === "submitted") {
            window.location.replace(`/result/${attemptId}`);
            return;
        }
        let activeIndex = 0;
        let saveTimer;
        let submitting = false;
        let countdownTimer;
        const choose = (nextIndex) => {
            activeIndex = Math.max(0, Math.min(nextIndex, attempt.questions.length - 1));
            renderQuestion(attempt, activeIndex, save, choose);
            renderNavigation(attempt, activeIndex, choose);
        };
        const persist = async (question) => {
            try {
                const response = await request(`/api/attempts/${attemptId}/answers/${question.position}`, {
                    method: "PUT",
                    body: JSON.stringify({ selectedAnswer: question.selectedAnswer, markedForReview: question.markedForReview }),
                });
                if (response.correctAnswer) {
                    question.correctAnswer = response.correctAnswer;
                    question.explanation = response.explanation;
                    question.isCorrect = response.isCorrect;
                    renderQuestion(attempt, activeIndex, save, choose);
                }
                setText("#save-status", `Đã lưu ${new Date().toLocaleTimeString("vi-VN")}`);
            }
            catch {
                setText("#save-status", "Chưa lưu — thử chọn lại");
            }
        };
        const save = (question) => {
            window.clearTimeout(saveTimer);
            setText("#save-status", "Đang lưu…");
            saveTimer = window.setTimeout(() => void persist(question), 400);
        };
        const flushCurrentAnswer = async () => {
            window.clearTimeout(saveTimer);
            await persist(attempt.questions[activeIndex]);
        };
        const submit = async () => {
            if (submitting)
                return;
            submitting = true;
            window.clearInterval(countdownTimer);
            await flushCurrentAnswer();
            await request(`/api/attempts/${attemptId}/submit`, { method: "POST" });
            window.location.assign(`/result/${attemptId}`);
        };
        const updateCountdown = () => {
            const timer = document.querySelector("#exam-timer");
            const remaining = formatRemainingTime(attempt.deadlineAt);
            if (timer)
                timer.textContent = remaining.label;
            if (remaining.expired && attempt.mode !== "study")
                void submit();
        };
        document.querySelector("#previous-question")?.addEventListener("click", () => choose(activeIndex - 1));
        document.querySelector("#next-question")?.addEventListener("click", () => choose(activeIndex + 1));
        document.querySelector("#mark-review")?.addEventListener("click", () => {
            const question = attempt.questions[activeIndex];
            question.markedForReview = !question.markedForReview;
            save(question);
            renderNavigation(attempt, activeIndex, choose);
        });
        document.addEventListener("keydown", (event) => {
            if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement)
                return;
            if (/^[1-4]$/.test(event.key))
                document.querySelector(`input[value="${event.key}"]`)?.click();
            if (event.key === "ArrowLeft")
                choose(activeIndex - 1);
            if (event.key === "ArrowRight")
                choose(activeIndex + 1);
            if (event.key.toLowerCase() === "r")
                document.querySelector("#mark-review")?.click();
        });
        const dialog = document.querySelector("#submit-dialog");
        const submitButton = document.querySelector("#submit-exam");
        if (submitButton && attempt.mode === "study")
            submitButton.hidden = true;
        document.querySelector("#submit-exam")?.addEventListener("click", () => {
            const unanswered = attempt.questions.filter((question) => !question.selectedAnswer).length;
            setText("#submit-summary", unanswered ? `Bạn còn ${unanswered} câu chưa trả lời.` : `Bạn đã trả lời đủ ${attempt.questions.length} câu.`);
            dialog?.showModal();
        });
        document.querySelector("#confirm-submit")?.addEventListener("click", (event) => {
            event.preventDefault();
            void submit();
        });
        content?.setAttribute("aria-busy", "false");
        choose(0);
        updateCountdown();
        countdownTimer = window.setInterval(updateCountdown, 1000);
    }
    catch (error) {
        setText("#question-title", error instanceof Error ? error.message : "Không thể tải đề.");
        setText("#save-status", "Tải lỗi");
    }
}
function resultQuestionState(question) {
    if (!question.selectedAnswer)
        return "unanswered";
    return question.isCorrect ? "correct" : "wrong";
}
function resultStateLabel(state) {
    if (state === "correct")
        return "Đúng";
    if (state === "wrong")
        return "Sai";
    return "Chưa trả lời";
}
function renderResultQuestion(result, activeIndex, choose) {
    const question = result.questions[activeIndex];
    const state = resultQuestionState(question);
    setText("#result-question-topic", [question.chapter || question.topic, question.questionType, question.difficulty].filter(Boolean).join(" · "));
    setText("#result-question-status", resultStateLabel(state));
    const statusBadge = document.querySelector("#result-question-status");
    if (statusBadge)
        statusBadge.className = `result-question-status is-${state}`;
    setText("#result-question-heading", `Câu ${question.position}`);
    setText("#result-question-text", question.question);
    const choices = document.querySelector("#result-question-choices");
    if (choices) {
        choices.replaceChildren();
        question.choices.forEach((choice, choiceIndex) => {
            const choiceKey = "ABCD"[choiceIndex];
            const item = document.createElement("li");
            item.className = "review-choice";
            const selected = question.selectedAnswer === choiceKey;
            const correct = question.correctAnswer === choiceKey;
            if (selected)
                item.classList.add("is-selected");
            if (correct)
                item.classList.add("is-correct");
            if (selected && !correct)
                item.classList.add("is-wrong");
            const key = document.createElement("span");
            key.className = "review-choice-key";
            key.textContent = choiceKey;
            const copy = document.createElement("span");
            copy.textContent = choice;
            item.append(key, copy);
            const markers = [];
            if (selected)
                markers.push("Bạn chọn");
            if (correct)
                markers.push("Đáp án đúng");
            if (markers.length) {
                const marker = document.createElement("span");
                marker.className = "review-choice-marker";
                marker.textContent = markers.join(" · ");
                item.append(marker);
            }
            choices.append(item);
        });
    }
    const explanationPane = document.querySelector("#result-explanation");
    if (explanationPane) {
        explanationPane.replaceChildren();
        const status = document.createElement("p");
        status.className = `review-status is-${state}`;
        status.textContent = state === "correct" ? "Bạn trả lời đúng" : state === "wrong" ? "Bạn trả lời sai" : "Bạn chưa trả lời câu này";
        const answerSummary = document.createElement("dl");
        answerSummary.className = "review-answer-summary";
        [["Bạn chọn", question.selectedAnswer ?? "Chưa trả lời"], ["Đáp án đúng", question.correctAnswer ?? "—"]].forEach(([term, value]) => {
            const label = document.createElement("dt");
            label.textContent = term;
            const content = document.createElement("dd");
            content.textContent = value;
            answerSummary.append(label, content);
        });
        const explanationTitle = document.createElement("h3");
        explanationTitle.textContent = "Giải thích";
        const explanation = document.createElement("p");
        explanation.textContent = question.explanation ?? "Chưa có lời giải thích cho câu này.";
        explanationPane.append(status, answerSummary, explanationTitle, explanation);
    }
    document.querySelector("#result-question-heading")?.focus();
    renderResultNavigation(result, activeIndex, choose);
}
function renderResultNavigation(result, activeIndex, choose) {
    const navigation = document.querySelector("#result-question-nav");
    if (!navigation)
        return;
    navigation.replaceChildren();
    result.questions.forEach((question, index) => {
        const state = resultQuestionState(question);
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = String(index + 1);
        button.className = `question-link${index === activeIndex ? " is-active" : ""} is-${state}`;
        button.setAttribute("aria-label", `Xem câu ${index + 1}: ${resultStateLabel(state).toLowerCase()}`);
        button.addEventListener("click", () => choose(index));
        navigation.append(button);
    });
}
async function setupResults() {
    if (!attemptId)
        return;
    try {
        const result = await request(`/api/attempts/${attemptId}`);
        if (result.status !== "submitted") {
            window.location.replace(`/exam/${attemptId}`);
            return;
        }
        const totalQuestions = result.totalQuestions ?? result.questions.length;
        const correctCount = result.correctCount ?? result.questions.filter((question) => resultQuestionState(question) === "correct").length;
        const wrongCount = result.wrongCount ?? result.questions.filter((question) => resultQuestionState(question) === "wrong").length;
        const unansweredCount = result.unansweredCount ?? result.questions.filter((question) => resultQuestionState(question) === "unanswered").length;
        setText("#result-title", `${correctCount} / ${totalQuestions} câu đúng`);
        setText("#result-summary", "Xem lại đề vừa thi, đáp án đúng và lời giải cho từng câu.");
        setText("#result-correct-count", String(correctCount));
        setText("#result-wrong-count", String(wrongCount));
        setText("#result-unanswered-count", String(unansweredCount));
        let activeIndex = 0;
        const choose = (nextIndex) => {
            activeIndex = Math.max(0, Math.min(nextIndex, result.questions.length - 1));
            renderResultQuestion(result, activeIndex, choose);
        };
        choose(0);
    }
    catch (error) {
        setText("#result-title", error instanceof Error ? error.message : "Không thể tải kết quả.");
    }
}
async function setupAdmin() {
    const button = document.querySelector("#load-admin");
    const input = document.querySelector("#admin-token");
    const status = document.querySelector("#admin-status");
    const table = document.querySelector("#admin-table");
    const headers = () => ({ "X-Admin-Token": input?.value ?? "" });
    button?.addEventListener("click", async () => {
        try {
            const payload = await request("/api/admin/questions", { headers: headers() });
            if (status)
                status.textContent = `${payload.data.length} câu trên trang này`;
            if (!table)
                return;
            table.replaceChildren();
            const grid = document.createElement("table");
            const head = grid.createTHead().insertRow();
            ["ID", "Câu hỏi", "Chủ đề", "Độ khó"].forEach((label) => { const cell = document.createElement("th"); cell.textContent = label; head.append(cell); });
            const rows = grid.createTBody();
            payload.data.forEach((item) => { const row = rows.insertRow(); [String(item.id), item.question, item.topic, item.difficulty].forEach((value) => { const cell = row.insertCell(); cell.textContent = value; }); });
            table.append(grid);
        }
        catch (error) {
            if (status)
                status.textContent = error instanceof Error ? error.message : "Không thể tải dữ liệu.";
        }
    });
    document.querySelector("#publish-exams")?.addEventListener("click", async () => {
        try {
            const payload = await request("/api/admin/exams/publish", {
                method: "POST",
                body: "{}",
                headers: headers(),
            });
            if (status)
                status.textContent = `Đã publish ${payload.count} đề chuẩn.`;
        }
        catch (error) {
            if (status)
                status.textContent = error instanceof Error ? error.message : "Không thể publish đề.";
        }
    });
}
if (page === "home")
    void setupHome();
if (page === "exam")
    void setupExam();
if (page === "result")
    void setupResults();
if (page === "admin")
    void setupAdmin();
