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
async function setupHome() {
    const randomButton = document.querySelector("#start-exam");
    randomButton?.addEventListener("click", () => void startAttempt({}, randomButton));
    const container = document.querySelector("#published-exams");
    if (!container)
        return;
    try {
        const published = await request("/api/exams/published");
        container.replaceChildren(...published.data.map(publishedExamButton));
        const randomPublishedButton = document.querySelector("#random-published-exam");
        randomPublishedButton?.addEventListener("click", () => {
            const exam = published.data[Math.floor(Math.random() * published.data.length)];
            if (exam)
                void startAttempt({ examInstanceId: exam.id }, randomPublishedButton);
        });
        if (randomPublishedButton)
            randomPublishedButton.disabled = !published.data.length;
        if (!published.data.length)
            setText("#home-status", "Chưa có đề sẵn; hãy dùng đề ngẫu nhiên.");
    }
    catch (error) {
        setText("#home-status", error instanceof Error ? error.message : "Không thể tải danh sách đề.");
    }
    finally {
        container.setAttribute("aria-busy", "false");
    }
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
    setText("#question-topic", `${question.topic} · ${question.difficulty}`);
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
                await request(`/api/attempts/${attemptId}/answers/${question.position}`, {
                    method: "PUT",
                    body: JSON.stringify({ selectedAnswer: question.selectedAnswer, markedForReview: question.markedForReview }),
                });
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
            if (remaining.expired)
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
        document.querySelector("#submit-exam")?.addEventListener("click", () => {
            const unanswered = attempt.questions.filter((question) => !question.selectedAnswer).length;
            setText("#submit-summary", unanswered ? `Bạn còn ${unanswered} câu chưa trả lời.` : "Bạn đã trả lời đủ 40 câu.");
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
function renderResultQuestion(result, activeIndex, choose) {
    const question = result.questions[activeIndex];
    setText("#result-question-topic", `${question.topic} · ${question.difficulty}`);
    setText("#result-question-status", question.isCorrect ? "Đúng" : "Cần ôn lại");
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
            choices.append(item);
        });
    }
    const explanationPane = document.querySelector("#result-explanation");
    if (explanationPane) {
        explanationPane.replaceChildren();
        const status = document.createElement("p");
        status.className = "review-status";
        status.textContent = question.isCorrect ? "Bạn trả lời đúng" : "Cần ôn lại câu này";
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
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = String(index + 1);
        button.className = `question-link${index === activeIndex ? " is-active" : ""}${question.isCorrect ? " is-correct" : " is-wrong"}`;
        button.setAttribute("aria-label", `Xem câu ${index + 1}: ${question.isCorrect ? "đúng" : "cần ôn lại"}`);
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
        setText("#result-title", `${result.score} / ${result.totalQuestions} câu đúng`);
        setText("#result-summary", "Chọn một câu để xem lại bài làm và lời giải.");
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
