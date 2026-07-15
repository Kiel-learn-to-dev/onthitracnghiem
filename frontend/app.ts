type Question = {
  position: number;
  question: string;
  choices: string[];
  topic: string;
  chapter?: string | null;
  questionType?: string | null;
  difficulty: string;
  assumptions?: string | null;
  selectedAnswer: string | null;
  markedForReview: boolean;
  correctAnswer?: string;
  explanation?: string;
  isCorrect?: boolean;
};

type Attempt = {
  attemptId: string;
  examInstanceId: string;
  mode: "exam" | "study";
  status: string;
  startedAt: string;
  deadlineAt: string | null;
  timeLimitSeconds: number;
  score?: number;
  correctCount?: number;
  wrongCount?: number;
  unansweredCount?: number;
  totalQuestions?: number;
  questions: Question[];
};

type PublishedExam = { id: string; title: string; questionCount: number; subject: { slug: string; title: string } };
type RecentAttempt = {
  attemptId: string;
  examInstanceId: string;
  title: string;
  tag: "Đề có sẵn" | "Đề ngẫu nhiên";
  completedCountForExam: number | null;
  subject: { slug: string; title: string };
  score: number;
  totalQuestions: number;
  submittedAt: string | null;
  resultUrl: string;
};
type SaveAnswerResponse = {
  position: number;
  saved: boolean;
  correctAnswer?: string;
  explanation?: string;
  isCorrect?: boolean;
};
type Subject = { slug: string; title: string; questionCount: number };
type CatalogItem = { value: string; count: number };
type SubjectCatalog = {
  subject: { slug: string; title: string };
  questionCount: number;
  chapters: CatalogItem[];
  topics: CatalogItem[];
  difficulties: CatalogItem[];
  questionTypes: CatalogItem[];
};

const page = document.body.dataset.page;
const attemptId = document.body.dataset.attemptId;

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { error?: { message?: string } } | null;
    throw new Error(payload?.error?.message ?? "Không thể hoàn tất yêu cầu.");
  }
  return response.json() as Promise<T>;
}

function setText(selector: string, value: string): void {
  const element = document.querySelector(selector);
  if (element) element.textContent = value;
}

function formatDateInputValue(date = new Date()): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

async function startAttempt(payload: Record<string, unknown> = {}, button?: HTMLButtonElement): Promise<void> {
  const status = document.querySelector("#home-status");
  if (button) button.disabled = true;
  setText("#home-status", "Đang tạo đề…");
  try {
    const attempt = await request<Attempt>("/api/attempts", { method: "POST", body: JSON.stringify(payload) });
    window.location.assign(`/exam/${attempt.attemptId}`);
  } catch (error) {
    setText("#home-status", error instanceof Error ? error.message : "Có lỗi xảy ra.");
    if (button) button.disabled = false;
  }
}

function publishedExamButton(exam: PublishedExam): HTMLButtonElement {
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

async function setupRecentAttempt(filters: { subjectSlug?: string; submittedDate?: string } = {}): Promise<void> {
  const list = document.querySelector<HTMLElement>("#recent-attempt-list");
  if (!list) return;
  list.setAttribute("aria-busy", "true");
  try {
    const params = new URLSearchParams({ days: "7" });
    if (filters.subjectSlug) params.set("subjectSlug", filters.subjectSlug);
    if (filters.submittedDate) params.set("submittedDate", filters.submittedDate);
    const response = await request<{ data: RecentAttempt[] }>(`/api/attempts/recent?${params.toString()}`);
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
  } catch {
    const error = document.createElement("p");
    error.className = "history-empty";
    error.textContent = "Không thể tải lịch sử làm bài.";
    list.replaceChildren(error);
  } finally {
    list.setAttribute("aria-busy", "false");
  }
}

async function setupHome(): Promise<void> {
  const form = document.querySelector<HTMLFormElement>("#exam-setup");
  const startButton = document.querySelector<HTMLButtonElement>("#start-exam");
  const subjectSelect = document.querySelector<HTMLSelectElement>("#subject-select");
  const publishedSubjectSelect = document.querySelector<HTMLSelectElement>("#published-subject-select");
  const historySubjectSelect = document.querySelector<HTMLSelectElement>("#history-subject-select");
  const historyDateInput = document.querySelector<HTMLInputElement>("#history-date-input");
  const clearHistoryFilters = document.querySelector<HTMLButtonElement>("#clear-history-filters");
  const modeSelect = document.querySelector<HTMLSelectElement>("#mode-select");
  const questionCountInput = document.querySelector<HTMLInputElement>("#question-count");
  const timeLimitSelect = document.querySelector<HTMLSelectElement>("#time-limit");
  const chapterSelect = document.querySelector<HTMLSelectElement>("#chapter-select");
  const difficultySelect = document.querySelector<HTMLSelectElement>("#difficulty-select");
  const questionTypeSelect = document.querySelector<HTMLSelectElement>("#question-type-select");
  if (historyDateInput && !historyDateInput.value) historyDateInput.value = formatDateInputValue();
  const refreshHistory = () => void setupRecentAttempt({
    subjectSlug: historySubjectSelect?.value || undefined,
    submittedDate: historyDateInput?.value || undefined,
  });
  const resetSelect = (select: HTMLSelectElement | null, label: string, items: CatalogItem[]) => {
    if (!select) return;
    select.replaceChildren(new Option(label, ""), ...items.map((item) => new Option(`${item.value} (${item.count})`, item.value)));
  };
  const setupCatalog = async (slug: string) => {
    try {
      const catalog = await request<{ data: SubjectCatalog }>(`/api/subjects/${encodeURIComponent(slug)}/catalog`);
      resetSelect(chapterSelect, "Tất cả", catalog.data.chapters);
      resetSelect(difficultySelect, "Tất cả", catalog.data.difficulties);
      resetSelect(questionTypeSelect, "Tất cả", catalog.data.questionTypes);
      setText("#catalog-summary", `${catalog.data.questionCount} câu có thể tạo đề`);
      if (questionCountInput) questionCountInput.max = String(Math.max(1, catalog.data.questionCount));
    } catch (error) {
      setText("#catalog-summary", error instanceof Error ? error.message : "Không thể tải cấu hình môn học.");
    }
  };
  const setupPublishedExams = async (slug: string) => {
    const container = document.querySelector<HTMLElement>("#published-exams");
    const randomPublishedButton = document.querySelector<HTMLButtonElement>("#random-published-exam");
    if (!container) return;
    container.setAttribute("aria-busy", "true");
    try {
      const published = await request<{ data: PublishedExam[] }>(`/api/exams/published?subjectSlug=${encodeURIComponent(slug)}`);
      if (published.data.length) {
        container.replaceChildren(...published.data.map(publishedExamButton));
      } else {
        const empty = document.createElement("p");
        empty.className = "published-empty";
        empty.textContent = "Môn này chưa có đề sẵn.";
        container.replaceChildren(empty);
      }
      if (randomPublishedButton) {
        randomPublishedButton.disabled = !published.data.length;
        randomPublishedButton.onclick = () => {
          const exam = published.data[Math.floor(Math.random() * published.data.length)];
          if (exam) void startAttempt({ examInstanceId: exam.id }, randomPublishedButton);
        };
      }
    } catch (error) {
      setText("#home-status", error instanceof Error ? error.message : "Không thể tải danh sách đề.");
    } finally {
      container.setAttribute("aria-busy", "false");
    }
  };
  try {
    const subjects = await request<{ data: Subject[] }>("/api/subjects");
    subjectSelect?.replaceChildren(...subjects.data.map((subject) => new Option(`${subject.title} (${subject.questionCount})`, subject.slug)));
    publishedSubjectSelect?.replaceChildren(...subjects.data.map((subject) => new Option(subject.title, subject.slug)));
    historySubjectSelect?.replaceChildren(new Option("Tất cả môn", ""), ...subjects.data.map((subject) => new Option(subject.title, subject.slug)));
    if (subjects.data[0]) {
      await setupCatalog(subjects.data[0].slug);
      await setupPublishedExams(subjects.data[0].slug);
    }
    else setText("#catalog-summary", "Chưa có môn học nào.");
  } catch (error) {
    setText("#catalog-summary", error instanceof Error ? error.message : "Không thể tải danh sách môn học.");
  }
  subjectSelect?.addEventListener("change", () => void setupCatalog(subjectSelect.value));
  publishedSubjectSelect?.addEventListener("change", () => void setupPublishedExams(publishedSubjectSelect.value));
  historySubjectSelect?.addEventListener("change", refreshHistory);
  historyDateInput?.addEventListener("change", refreshHistory);
  clearHistoryFilters?.addEventListener("click", () => {
    if (historySubjectSelect) historySubjectSelect.value = "";
    if (historyDateInput) historyDateInput.value = "";
    refreshHistory();
  });
  refreshHistory();
  form?.addEventListener("submit", (event) => {
    event.preventDefault();
    const payload: Record<string, unknown> = {
      subjectSlug: subjectSelect?.value || undefined,
      mode: modeSelect?.value || "exam",
      questionCount: Number(questionCountInput?.value || 40),
      timeLimitSeconds: Number(timeLimitSelect?.value || 1800),
    };
    if (chapterSelect?.value) payload.chapters = [chapterSelect.value];
    if (difficultySelect?.value) payload.difficulties = [difficultySelect.value];
    if (questionTypeSelect?.value) payload.questionTypes = [questionTypeSelect.value];
    void startAttempt(payload, startButton ?? undefined);
  });
}

function renderNavigation(attempt: Attempt, activeIndex: number, choose: (index: number) => void): void {
  const navigation = document.querySelector("#question-nav");
  if (!navigation) return;
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

function renderQuestion(
  attempt: Attempt,
  activeIndex: number,
  save: (question: Question) => void,
  choose: (index: number) => void,
): void {
  const question = attempt.questions[activeIndex];
  setText("#progress-text", `Câu ${activeIndex + 1} / ${attempt.questions.length}`);
  setText("#question-topic", [question.chapter || question.topic, question.questionType, question.difficulty].filter(Boolean).join(" · "));
  setText("#question-title", question.question);
  const assumptions = document.querySelector<HTMLElement>("#question-assumptions");
  if (assumptions) {
    assumptions.hidden = !question.assumptions;
    assumptions.textContent = question.assumptions ? `Giả định: ${question.assumptions}` : "";
  }
  const choices = document.querySelector<HTMLFieldSetElement>("#choices");
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
  const feedback = document.querySelector<HTMLElement>("#study-feedback");
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
  document.querySelector<HTMLElement>("#question-title")?.focus();
}

function formatRemainingTime(deadlineAt: string | null): { label: string; expired: boolean } {
  const milliseconds = deadlineAt ? Math.max(0, Date.parse(deadlineAt) - Date.now()) : 0;
  const seconds = Math.ceil(milliseconds / 1000);
  return { label: `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`, expired: seconds === 0 };
}

async function setupExam(): Promise<void> {
  if (!attemptId) return;
  const content = document.querySelector<HTMLElement>(".exam-content");
  const saveStatus = document.querySelector("#save-status");
  try {
    const attempt = await request<Attempt>(`/api/attempts/${attemptId}`);
    if (attempt.status === "submitted") {
      window.location.replace(`/result/${attemptId}`);
      return;
    }
    let activeIndex = 0;
    let saveTimer: number | undefined;
    let submitting = false;
    let countdownTimer: number | undefined;
    const choose = (nextIndex: number) => {
      activeIndex = Math.max(0, Math.min(nextIndex, attempt.questions.length - 1));
      renderQuestion(attempt, activeIndex, save, choose);
      renderNavigation(attempt, activeIndex, choose);
    };
    const persist = async (question: Question) => {
      try {
        const response = await request<SaveAnswerResponse>(`/api/attempts/${attemptId}/answers/${question.position}`, {
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
      } catch {
        setText("#save-status", "Chưa lưu — thử chọn lại");
      }
    };
    const save = (question: Question) => {
      window.clearTimeout(saveTimer);
      setText("#save-status", "Đang lưu…");
      saveTimer = window.setTimeout(() => void persist(question), 400);
    };
    const flushCurrentAnswer = async () => {
      window.clearTimeout(saveTimer);
      await persist(attempt.questions[activeIndex]);
    };
    const submit = async () => {
      if (submitting) return;
      submitting = true;
      window.clearInterval(countdownTimer);
      await flushCurrentAnswer();
      await request(`/api/attempts/${attemptId}/submit`, { method: "POST" });
      window.location.assign(`/result/${attemptId}`);
    };
    const updateCountdown = () => {
      const timer = document.querySelector("#exam-timer");
      const remaining = formatRemainingTime(attempt.deadlineAt);
      if (timer) timer.textContent = remaining.label;
      if (remaining.expired && attempt.mode !== "study") void submit();
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
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
      if (/^[1-4]$/.test(event.key)) document.querySelector<HTMLInputElement>(`input[value="${event.key}"]`)?.click();
      if (event.key === "ArrowLeft") choose(activeIndex - 1);
      if (event.key === "ArrowRight") choose(activeIndex + 1);
      if (event.key.toLowerCase() === "r") document.querySelector<HTMLButtonElement>("#mark-review")?.click();
    });
    const dialog = document.querySelector<HTMLDialogElement>("#submit-dialog");
    const submitButton = document.querySelector<HTMLButtonElement>("#submit-exam");
    if (submitButton && attempt.mode === "study") submitButton.hidden = true;
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
  } catch (error) {
    setText("#question-title", error instanceof Error ? error.message : "Không thể tải đề.");
    setText("#save-status", "Tải lỗi");
  }
}

type ResultState = "correct" | "wrong" | "unanswered";

function resultQuestionState(question: Question): ResultState {
  if (!question.selectedAnswer) return "unanswered";
  return question.isCorrect ? "correct" : "wrong";
}

function resultStateLabel(state: ResultState): string {
  if (state === "correct") return "Đúng";
  if (state === "wrong") return "Sai";
  return "Chưa trả lời";
}

function renderResultQuestion(result: Attempt, activeIndex: number, choose: (index: number) => void): void {
  const question = result.questions[activeIndex];
  const state = resultQuestionState(question);
  setText("#result-question-topic", [question.chapter || question.topic, question.questionType, question.difficulty].filter(Boolean).join(" · "));
  setText("#result-question-status", resultStateLabel(state));
  const statusBadge = document.querySelector<HTMLElement>("#result-question-status");
  if (statusBadge) statusBadge.className = `result-question-status is-${state}`;
  setText("#result-question-heading", `Câu ${question.position}`);
  setText("#result-question-text", question.question);
  const choices = document.querySelector<HTMLOListElement>("#result-question-choices");
  if (choices) {
    choices.replaceChildren();
    question.choices.forEach((choice, choiceIndex) => {
      const choiceKey = "ABCD"[choiceIndex];
      const item = document.createElement("li");
      item.className = "review-choice";
      const selected = question.selectedAnswer === choiceKey;
      const correct = question.correctAnswer === choiceKey;
      if (selected) item.classList.add("is-selected");
      if (correct) item.classList.add("is-correct");
      if (selected && !correct) item.classList.add("is-wrong");
      const key = document.createElement("span");
      key.className = "review-choice-key";
      key.textContent = choiceKey;
      const copy = document.createElement("span");
      copy.textContent = choice;
      item.append(key, copy);
      const markers = [];
      if (selected) markers.push("Bạn chọn");
      if (correct) markers.push("Đáp án đúng");
      if (markers.length) {
        const marker = document.createElement("span");
        marker.className = "review-choice-marker";
        marker.textContent = markers.join(" · ");
        item.append(marker);
      }
      choices.append(item);
    });
  }
  const explanationPane = document.querySelector<HTMLElement>("#result-explanation");
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
  document.querySelector<HTMLElement>("#result-question-heading")?.focus();
  renderResultNavigation(result, activeIndex, choose);
}

function renderResultNavigation(result: Attempt, activeIndex: number, choose: (index: number) => void): void {
  const navigation = document.querySelector("#result-question-nav");
  if (!navigation) return;
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

async function setupResults(): Promise<void> {
  if (!attemptId) return;
  try {
    const result = await request<Attempt>(`/api/attempts/${attemptId}`);
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
    const choose = (nextIndex: number) => {
      activeIndex = Math.max(0, Math.min(nextIndex, result.questions.length - 1));
      renderResultQuestion(result, activeIndex, choose);
    };
    choose(0);
  } catch (error) {
    setText("#result-title", error instanceof Error ? error.message : "Không thể tải kết quả.");
  }
}

async function setupAdmin(): Promise<void> {
  const button = document.querySelector<HTMLButtonElement>("#load-admin");
  const input = document.querySelector<HTMLInputElement>("#admin-token");
  const status = document.querySelector("#admin-status");
  const table = document.querySelector("#admin-table");
  const headers = (): HeadersInit => ({ "X-Admin-Token": input?.value ?? "" });
  button?.addEventListener("click", async () => {
    try {
      const payload = await request<{ data: Array<{ id: number; question: string; topic: string; difficulty: string }> }>("/api/admin/questions", { headers: headers() });
      if (status) status.textContent = `${payload.data.length} câu trên trang này`;
      if (!table) return;
      table.replaceChildren();
      const grid = document.createElement("table");
      const head = grid.createTHead().insertRow();
      ["ID", "Câu hỏi", "Chủ đề", "Độ khó"].forEach((label) => { const cell = document.createElement("th"); cell.textContent = label; head.append(cell); });
      const rows = grid.createTBody();
      payload.data.forEach((item) => { const row = rows.insertRow(); [String(item.id), item.question, item.topic, item.difficulty].forEach((value) => { const cell = row.insertCell(); cell.textContent = value; }); });
      table.append(grid);
    } catch (error) {
      if (status) status.textContent = error instanceof Error ? error.message : "Không thể tải dữ liệu.";
    }
  });
  document.querySelector<HTMLButtonElement>("#publish-exams")?.addEventListener("click", async () => {
    try {
      const payload = await request<{ count: number }>("/api/admin/exams/publish", {
        method: "POST",
        body: "{}",
        headers: headers(),
      });
      if (status) status.textContent = `Đã publish ${payload.count} đề chuẩn.`;
    } catch (error) {
      if (status) status.textContent = error instanceof Error ? error.message : "Không thể publish đề.";
    }
  });
}

if (page === "home") void setupHome();
if (page === "exam") void setupExam();
if (page === "result") void setupResults();
if (page === "admin") void setupAdmin();
