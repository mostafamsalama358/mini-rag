const copy = {
  en: {
    workspace: "Workspace",
    userId: "User ID",
    projects: "Projects",
    projectNamePlaceholder: "New project name",
    create: "Create",
    activeProject: "Active Project",
    apiDocs: "API Docs",
    askPlaceholder: "Ask me anything about this project...",
    ask: "Ask",
    upload: "Upload",
    selectProject: "Create or select a project first.",
    chooseFile: "Choose a file first.",
    enterQuestion: "Write a question first.",
    noProjects: "No projects yet.",
    indexingInProgress: "Files are still being indexed. Wait for processing to finish.",
    uploadInProgress: "Uploading files...",
    processingInProgress: "Processing and indexing...",
    statusUploadingTitle: "Uploading files",
    statusUploadingDetail: "Files are being uploaded. You cannot ask questions yet.",
    statusProcessingTitle: "Processing and indexing",
    statusProcessingDetail: "OCR and indexing are running. You can ask when this step finishes.",
    statusReadyTitle: "Ready to ask",
    statusReadyDetail: "{records} chunks indexed. You can ask your question below.",
    statusPartialTitle: "Some files are not indexed",
    statusPartialDetail: "{pending} of {count} files still need processing. Re-upload or run process-and-push.",
    statusIdleTitle: "No documents indexed",
    statusIdleDetail: "Upload PDF or TXT files. You can ask only after processing finishes.",
    readyToAsk: "All files are processed and indexed. You can ask your question now.",
    error: "Error",
    noIndex: "No indexed documents yet. Upload a file and wait for processing.",
    indexingTimeout: "Indexing is still running (OCR may take several minutes). Please wait and try again.",
    ragNoContext: "Documents are not indexed yet. Upload a file or wait for processing to finish.",
    you: "You",
    assistant: "AlgoRAG",
    langButton: "عربي",
    welcome: "Select a project, upload files, then ask questions.",
  },
  ar: {
    workspace: "مساحة العمل",
    userId: "معرف المستخدم",
    projects: "المشاريع",
    projectNamePlaceholder: "اسم مشروع جديد",
    create: "إنشاء",
    activeProject: "المشروع الحالي",
    apiDocs: "توثيق API",
    askPlaceholder: "اسأل أي شيء عن هذا المشروع...",
    ask: "اسأل",
    upload: "رفع",
    selectProject: "أنشئ أو اختر مشروعا أولا.",
    chooseFile: "اختر ملفا أولا.",
    enterQuestion: "اكتب السؤال أولا.",
    noProjects: "لا توجد مشاريع بعد.",
    indexingInProgress: "ما زالت الملفات قيد الفهرسة. انتظر حتى تنتهي المعالجة.",
    uploadInProgress: "جاري رفع الملفات...",
    processingInProgress: "جاري المعالجة والفهرسة...",
    statusUploadingTitle: "جاري رفع الملفات",
    statusUploadingDetail: "يتم رفع الملفات الآن. لا يمكنك السؤال حتى ينتهي الرفع.",
    statusProcessingTitle: "جاري المعالجة والفهرسة",
    statusProcessingDetail: "يتم استخراج النص (OCR) وفهرسة المستندات. ستتمكن من السؤال بعد انتهاء هذه الخطوة.",
    statusReadyTitle: "جاهز للأسئلة",
    statusReadyDetail: "تم فهرسة {records} جزء. يمكنك كتابة سؤالك في الأسفل.",
    statusPartialTitle: "بعض الملفات غير مفهرسة",
    statusPartialDetail: "{pending} من {count} ملفات لم تُعالَج بعد. ارفع الملفات مجدداً أو شغّل process-and-push.",
    statusIdleTitle: "لا توجد مستندات مفهرسة",
    statusIdleDetail: "ارفع ملفات PDF أو TXT. يمكنك السؤال فقط بعد انتهاء المعالجة والفهرسة.",
    readyToAsk: "اكتملت معالجة وفهرسة كل الملفات. يمكنك طرح سؤالك الآن.",
    error: "خطأ",
    noIndex: "لا توجد مستندات مفهرسة بعد. ارفع ملفا وانتظر المعالجة.",
    indexingTimeout: "الفهرسة ما زالت جارية (قد تستغرق OCR عدة دقائق). انتظر ثم حاول مرة أخرى.",
    ragNoContext: "المستندات غير مفهرسة بعد. ارفع ملفا أو انتظر انتهاء المعالجة.",
    you: "أنت",
    assistant: "AlgoRAG",
    langButton: "English",
    welcome: "اختر مشروعا وارفع الملفات ثم اسأل.",
  },
};

const state = {
  lang: localStorage.getItem("algorag.lang") || "en",
  userId: localStorage.getItem("algorag.userId") || "demo-user",
  projects: [],
  activeProjectId: localStorage.getItem("algorag.activeProjectId") || "",
  sessionId: localStorage.getItem("algorag.sessionId") || crypto.randomUUID(),
  uploadedFileNames: [],
  filePipelineBusy: false,
  projectStatus: "idle",
  indexedRecordCount: 0,
};

localStorage.setItem("algorag.sessionId", state.sessionId);

const $ = (id) => document.getElementById(id);

const elements = {
  userId: $("userIdInput"),
  projectForm: $("projectForm"),
  projectName: $("projectNameInput"),
  projectsList: $("projectsList"),
  refreshProjects: $("refreshProjectsBtn"),
  activeProjectName: $("activeProjectName"),
  activeProjectMeta: $("activeProjectMeta"),
  langToggle: $("langToggleBtn"),
  fileInput: $("fileInput"),
  upload: $("uploadBtn"),
  fileHint: $("fileHint"),
  chatLog: $("chatLog"),
  chatForm: $("chatForm"),
  question: $("questionInput"),
  projectStatusBanner: $("projectStatusBanner"),
  projectStatusIcon: $("projectStatusIcon"),
  projectStatusTitle: $("projectStatusTitle"),
  projectStatusDetail: $("projectStatusDetail"),
};

function t(key) {
  return copy[state.lang][key] || copy.en[key] || key;
}

function applyLanguage() {
  document.documentElement.lang = state.lang;
  document.documentElement.dir = state.lang === "ar" ? "rtl" : "ltr";

  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });

  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });

  elements.langToggle.textContent = t("langButton");
  elements.upload.title = t("upload");
  elements.upload.setAttribute("aria-label", t("upload"));
  updateFileHint();
  updateProjectStatus();
  renderProjects();
  renderActiveProject();
}

function headers(json = true) {
  const result = { "X-User-Id": state.userId };
  if (json) result["Content-Type"] = "application/json";
  return result;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? headers(false) : headers(true)),
      ...(options.headers || {}),
    },
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message = typeof payload === "string" ? payload : payload.detail || payload.signal || response.statusText;
    throw new Error(message);
  }

  return payload;
}

function activeProject() {
  return state.projects.find((project) => project.id === state.activeProjectId) || null;
}

function activeProjectNumericId() {
  const project = activeProject();
  return project ? project.project_id : null;
}

function requireProject() {
  const id = activeProjectNumericId();
  if (!id) throw new Error(t("selectProject"));
  return id;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[char]);
}

function renderProjects() {
  elements.projectsList.innerHTML = "";

  if (state.projects.length === 0) {
    const empty = document.createElement("small");
    empty.textContent = t("noProjects");
    elements.projectsList.appendChild(empty);
    return;
  }

  state.projects.forEach((project) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `project-item ${project.id === state.activeProjectId ? "active" : ""}`;
    button.innerHTML = `<strong>${escapeHtml(project.name)}</strong><small>${escapeHtml(project.id)}</small>`;
    button.addEventListener("click", () => {
      state.activeProjectId = project.id;
      state.uploadedFileNames = [];
      state.indexedRecordCount = 0;
      localStorage.setItem("algorag.activeProjectId", project.id);
      setProjectStatus("idle");
      renderProjects();
      renderActiveProject();
      updateFileHint();
      syncProjectReadiness().catch(console.error);
    });
    elements.projectsList.appendChild(button);
  });
}

function renderActiveProject() {
  const project = activeProject();
  elements.activeProjectName.textContent = project ? project.name : "-";
  elements.activeProjectMeta.textContent = project
    ? `UUID: ${project.id} | API ID: ${project.project_id || "-"}`
    : t("selectProject");
}

function addMessage(role, text, variant = role) {
  const message = document.createElement("div");
  message.className = `message ${variant}`;
  const label =
    role === "user"
      ? t("you")
      : variant === "clarification"
        ? t("assistant")
        : t("assistant");
  message.textContent = `${label}\n${text}`;
  elements.chatLog.appendChild(message);
  elements.chatLog.scrollTop = elements.chatLog.scrollHeight;
}

function setBusy(button, isBusy) {
  button.disabled = isBusy;
}

function formatStatus(text, vars = {}) {
  return String(text).replace(/\{(\w+)\}/g, (_, key) => String(vars[key] ?? ""));
}

function setProjectStatus(status, details = {}) {
  state.projectStatus = status;
  if (details.recordCount !== undefined) {
    state.indexedRecordCount = details.recordCount;
  }
  updateProjectStatus(details);
}

function updateProjectStatus(details = {}) {
  const banner = elements.projectStatusBanner;
  const submit = elements.chatForm.querySelector("button[type='submit']");
  const fileCount = details.fileCount ?? state.uploadedFileNames.length;
  const recordCount = details.recordCount ?? state.indexedRecordCount;

  banner.hidden = false;
  banner.className = `project-status project-status--${state.projectStatus}`;

  const statusCopy = {
    uploading: ["statusUploadingTitle", "statusUploadingDetail", "↑"],
    processing: ["statusProcessingTitle", "statusProcessingDetail", "…"],
    ready: ["statusReadyTitle", "statusReadyDetail", "✓"],
    partial: ["statusPartialTitle", "statusPartialDetail", "!"],
    idle: ["statusIdleTitle", "statusIdleDetail", "○"],
  }[state.projectStatus] || ["statusIdleTitle", "statusIdleDetail", "○"];

  elements.projectStatusIcon.textContent = statusCopy[2];
  elements.projectStatusTitle.textContent = t(statusCopy[0]);
  elements.projectStatusDetail.textContent =
    state.projectStatus === "ready" || state.projectStatus === "partial"
      ? formatStatus(t(statusCopy[1]), {
          count: fileCount,
          records: recordCount,
          pending: details.pendingAssetCount ?? 0,
        })
      : t(statusCopy[1]);

  const canAsk =
    (state.projectStatus === "ready" || state.projectStatus === "partial") &&
    !state.filePipelineBusy;
  elements.question.disabled = !canAsk;
  submit.disabled = !canAsk;

  if (state.projectStatus === "ready") {
    elements.question.placeholder = t("askPlaceholder");
  } else if (state.projectStatus === "partial") {
    elements.question.placeholder = t("statusPartialDetail");
  } else if (state.filePipelineBusy) {
    elements.question.placeholder =
      state.projectStatus === "uploading" ? t("statusUploadingDetail") : t("statusProcessingDetail");
  } else {
    elements.question.placeholder = t("statusIdleDetail");
  }
}

function updateFileHint() {
  if (state.projectStatus === "uploading") {
    elements.fileHint.hidden = false;
    elements.fileHint.textContent = t("uploadInProgress");
    elements.fileHint.title = t("uploadInProgress");
    return;
  }

  if (state.projectStatus === "processing" || state.filePipelineBusy) {
    elements.fileHint.hidden = false;
    elements.fileHint.textContent = t("processingInProgress");
    elements.fileHint.title = t("processingInProgress");
    return;
  }

  const names = state.uploadedFileNames;
  if (!names.length || state.projectStatus !== "ready") {
    elements.fileHint.hidden = true;
    elements.fileHint.textContent = "";
    elements.fileHint.title = "";
    return;
  }

  const label =
    names.length <= 2 ? names.join(", ") : `${names.slice(0, 2).join(", ")} +${names.length - 2}`;

  elements.fileHint.hidden = false;
  elements.fileHint.textContent = label;
  elements.fileHint.title = names.join(", ");
}

const POLL_INTERVAL_MS = 12000;

async function loadProjects() {
  const payload = await api("/api/v1/projects");
  state.projects = payload.projects || [];

  if (!state.projects.some((project) => project.id === state.activeProjectId)) {
    state.activeProjectId = state.projects[0]?.id || "";
    localStorage.setItem("algorag.activeProjectId", state.activeProjectId);
  }

  renderProjects();
  renderActiveProject();
  await syncProjectReadiness();
}

async function createProject(event) {
  event.preventDefault();
  const name = elements.projectName.value.trim();
  if (!name) return;

  setBusy(elements.projectForm.querySelector("button"), true);
  try {
    const payload = await api("/api/v1/projects", {
      method: "POST",
      body: JSON.stringify({ name }),
    });

    const project = payload.project;
    state.projects = [project, ...state.projects.filter((item) => item.id !== project.id)];
    state.activeProjectId = project.id;
    state.uploadedFileNames = [];
    state.indexedRecordCount = 0;
    localStorage.setItem("algorag.activeProjectId", project.id);
    elements.projectName.value = "";
    setProjectStatus("idle");
    renderProjects();
    renderActiveProject();
  } catch (error) {
    addMessage("assistant", error.message);
  } finally {
    setBusy(elements.projectForm.querySelector("button"), false);
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function uploadFile(projectId, file) {
  const form = new FormData();
  form.append("file", file);

  await api(`/api/v1/data/upload/${projectId}`, {
    method: "POST",
    body: form,
  });

  return file.name;
}

async function syncProjectReadiness() {
  const projectId = activeProjectNumericId();
  if (!projectId) {
    setProjectStatus("idle");
    return;
  }

  try {
    const indexInfo = await getIndexInfo(projectId);
    if (indexInfo.recordCount > 0) {
      const status = indexInfo.isFullyIndexed ? "ready" : "partial";
      setProjectStatus(status, {
        recordCount: indexInfo.recordCount,
        fileCount: indexInfo.assetCount || state.uploadedFileNames.length,
        pendingAssetCount: indexInfo.pendingAssetCount,
      });
      return;
    }
  } catch {
    // keep idle when index is unavailable
  }

  if (!state.filePipelineBusy) {
    setProjectStatus("idle");
  }
}

async function uploadAndProcessFiles(files) {
  const projectId = requireProject();
  if (!files.length) throw new Error(t("chooseFile"));

  setProjectStatus("uploading");

  const processedNames = await Promise.all(
    files.map((file) => uploadFile(projectId, file)),
  );

  setProjectStatus("processing");

  const baselineCount = await getIndexRecordCount(projectId);

  const workflowPayload = await api(`/api/v1/data/process-and-push/${projectId}`, {
    method: "POST",
    body: JSON.stringify({
      do_reset: 0,
    }),
  });

  const taskId = workflowPayload.task_id || workflowPayload.workflow_task_id;
  if (!taskId) throw new Error(t("error"));

  await waitForTask(taskId, projectId, baselineCount);

  const recordCount = await getIndexRecordCount(projectId);
  state.uploadedFileNames = processedNames;
  setProjectStatus("ready", {
    recordCount,
    fileCount: processedNames.length,
  });
  updateFileHint();
  addMessage("assistant", t("readyToAsk"), "assistant");
}

async function handleFilesSelected() {
  const files = Array.from(elements.fileInput.files || []);
  if (!files.length) return;

  state.filePipelineBusy = true;
  setProjectStatus("uploading");
  updateFileHint();
  setBusy(elements.upload, true);

  const submit = elements.chatForm.querySelector("button[type='submit']");
  setBusy(submit, true);

  try {
    await uploadAndProcessFiles(files);
  } catch (error) {
    addMessage("assistant", error.message);
    setProjectStatus("idle");
    await syncProjectReadiness();
  } finally {
    elements.fileInput.value = "";
    state.filePipelineBusy = false;
    setBusy(elements.upload, false);
    setBusy(submit, false);
    updateFileHint();
    updateProjectStatus();
  }
}

async function fetchTaskStatus(taskId) {
  const response = await fetch(`/api/v1/data/tasks/${taskId}`, {
    method: "GET",
    headers: headers(true),
  });

  if (response.status === 404) {
    return null;
  }

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message = typeof payload === "string" ? payload : payload.detail || payload.signal || response.statusText;
    throw new Error(message);
  }

  return payload;
}

async function waitForIndexByRecordCount(projectId, baselineCount) {
  const deadline = Date.now() + 600000;

  while (Date.now() < deadline) {
    const count = await getIndexRecordCount(projectId);
    if (count > baselineCount) {
      return { record_count: count, fallback: true };
    }
    await sleep(POLL_INTERVAL_MS);
  }

  throw new Error(t("indexingTimeout"));
}

async function waitForTask(taskId, projectId, baselineCount = 0) {
  const deadline = Date.now() + 600000;
  let useIndexFallback = false;

  while (Date.now() < deadline) {
    if (!useIndexFallback) {
      try {
        const payload = await fetchTaskStatus(taskId);

        if (payload === null) {
          useIndexFallback = true;
        } else if (payload.ready) {
          if (payload.successful) {
            return payload;
          }
          throw new Error(payload.error || t("error"));
        }
      } catch (error) {
        useIndexFallback = true;
        console.error(error);
      }
    }

    if (useIndexFallback) {
      const count = await getIndexRecordCount(projectId);
      if (count > baselineCount) {
        return { record_count: count, fallback: true };
      }
    }

    await sleep(POLL_INTERVAL_MS);
  }

  throw new Error(t("indexingTimeout"));
}

async function getIndexInfo(projectId) {
  const payload = await api(`/api/v1/nlp/index/info/${projectId}`, { method: "GET" });
  const info = payload.collection_info || {};
  const coverage = info.coverage || payload.coverage || {};
  return {
    recordCount: info.record_count ?? 0,
    assetCount: coverage.asset_count ?? 0,
    indexedAssetCount: coverage.indexed_asset_count ?? 0,
    pendingAssetCount: coverage.pending_asset_count ?? 0,
    isFullyIndexed: coverage.is_fully_indexed ?? false,
  };
}

async function getIndexRecordCount(projectId) {
  const info = await getIndexInfo(projectId);
  return info.recordCount;
}

async function ensureIndexed(projectId) {
  const count = await getIndexRecordCount(projectId);
  if (count > 0) {
    return count;
  }

  if (state.filePipelineBusy) {
    throw new Error(t("indexingInProgress"));
  }

  throw new Error(t("noIndex"));
}

async function askQuestion(event) {
  event.preventDefault();
  const projectId = requireProject();
  const text = elements.question.value.trim();
  if (!text) throw new Error(t("enterQuestion"));

  addMessage("user", text);
  elements.question.value = "";

  const submit = elements.chatForm.querySelector("button[type='submit']");
  setBusy(submit, true);
  setBusy(elements.upload, true);

  try {
    await ensureIndexed(projectId);

    const payload = await api(`/api/v1/nlp/index/answer/${projectId}`, {
      method: "POST",
      body: JSON.stringify({
        text,
        limit: 12,
        session_id: state.sessionId,
      }),
    });

    const isClarification =
      payload.signal === "rag_clarification_needed" || payload.needs_clarification;

    addMessage(
      "assistant",
      payload.answer || "",
      isClarification ? "clarification" : "assistant",
    );
  } catch (error) {
    const message =
      error.message === "rag_no_context" ? t("ragNoContext") : error.message;
    addMessage("assistant", message);
  } finally {
    setBusy(submit, false);
    setBusy(elements.upload, false);
  }
}

function bindEvents() {
  elements.userId.value = state.userId;
  elements.userId.addEventListener("change", () => {
    state.userId = elements.userId.value.trim() || "demo-user";
    localStorage.setItem("algorag.userId", state.userId);
    loadProjects().catch(console.error);
  });

  elements.langToggle.addEventListener("click", () => {
    state.lang = state.lang === "en" ? "ar" : "en";
    localStorage.setItem("algorag.lang", state.lang);
    applyLanguage();
  });

  elements.projectForm.addEventListener("submit", createProject);
  elements.refreshProjects.addEventListener("click", () => {
    loadProjects().catch(console.error);
  });

  elements.upload.addEventListener("click", () => {
    elements.fileInput.click();
  });

  elements.fileInput.addEventListener("change", () => {
    handleFilesSelected().catch(console.error);
  });

  elements.chatForm.addEventListener("submit", (event) => {
    askQuestion(event).catch(console.error);
  });
}

function init() {
  bindEvents();
  applyLanguage();
  setProjectStatus("idle");
  addMessage("assistant", t("welcome"));
  loadProjects().catch(console.error);
}

init();
