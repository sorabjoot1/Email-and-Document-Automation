const toast = document.getElementById("toast");
const statusEl = document.getElementById("status");
const output = document.getElementById("output");
const outTitle = document.getElementById("outTitle");
const pdfLink = document.getElementById("pdfLink");
const docxLink = document.getElementById("docxLink");

let currentContent = "";
let currentDocumentId = null;

function showToast(msg, ok = false) {
  toast.textContent = msg;
  toast.classList.toggle("ok", ok);
  toast.classList.remove("hidden");
}

function setLoading(btn, loading) {
  btn.disabled = loading;
  btn.querySelector(".label").classList.toggle("hidden", loading);
  btn.querySelector(".spinner").classList.toggle("hidden", !loading);
}

function setOutput(title, content, documentId) {
  outTitle.textContent = title;
  output.textContent = content;
  currentContent = content;
  currentDocumentId = documentId;
  if (documentId) {
    pdfLink.href = `/api/export/${documentId}/pdf`;
    docxLink.href = `/api/export/${documentId}/docx`;
    pdfLink.classList.remove("hidden");
    docxLink.classList.remove("hidden");
  } else {
    pdfLink.classList.add("hidden");
    docxLink.classList.add("hidden");
  }
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`${tab.dataset.tab}Panel`).classList.add("active");
  });
});

async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    const ready = data.llm_configured;
    statusEl.classList.toggle("ok", ready);
    statusEl.classList.toggle("err", !ready);
    statusEl.textContent = ready
      ? `Ready · SMTP ${data.smtp_configured ? "on" : "off"}`
      : "Add OPENROUTER_API_KEY to .env";
  } catch {
    statusEl.classList.add("err");
    statusEl.textContent = "Backend offline";
  }
}

document.getElementById("generateForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  toast.classList.add("hidden");
  const btn = document.getElementById("genBtn");
  setLoading(btn, true);
  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        doc_type: document.getElementById("docType").value,
        tone: document.getElementById("tone").value,
        topic: document.getElementById("topic").value.trim(),
        recipient: document.getElementById("recipient").value.trim(),
        extra_context: document.getElementById("extra").value.trim(),
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Generation failed.");
    setOutput(data.title, data.content, data.document_id);
    showToast("Document generated.", true);
  } catch (err) {
    showToast(err.message || "Generation failed.");
  } finally {
    setLoading(btn, false);
  }
});

document.getElementById("summarizeForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  toast.classList.add("hidden");
  const btn = document.getElementById("sumBtn");
  setLoading(btn, true);
  try {
    const file = document.getElementById("fileInput").files[0];
    if (!file) throw new Error("Choose a PDF or DOCX file.");
    const formData = new FormData();
    formData.append("file", file);
    const mode = document.getElementById("sumMode").value;
    const res = await fetch(`/api/summarize-file?mode=${encodeURIComponent(mode)}`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Summarization failed.");
    setOutput(data.title, data.content, data.document_id);
    showToast("Document analyzed.", true);
  } catch (err) {
    showToast(err.message || "Summarization failed.");
  } finally {
    setLoading(btn, false);
  }
});

document.getElementById("emailForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  toast.classList.add("hidden");
  const btn = document.getElementById("emailBtn");
  setLoading(btn, true);
  try {
    const res = await fetch("/api/send-email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        to_email: document.getElementById("toEmail").value.trim(),
        subject: document.getElementById("emailSubject").value.trim(),
        body: document.getElementById("emailBody").value.trim(),
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Send failed.");
    showToast(`Email sent to ${data.to}.`, true);
  } catch (err) {
    showToast(err.message || "Send failed.");
  } finally {
    setLoading(btn, false);
  }
});

document.getElementById("copyBtn").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(currentContent || output.textContent || "");
    showToast("Copied.", true);
  } catch {
    showToast("Copy failed.");
  }
});

document.getElementById("useEmailBtn").addEventListener("click", () => {
  const text = currentContent || "";
  let subject = "";
  let body = text;
  const match = text.match(/^Subject:\s*(.+)$/im);
  if (match) {
    subject = match[1].trim();
    body = text.replace(match[0], "").trim();
  }
  document.getElementById("emailSubject").value = subject;
  document.getElementById("emailBody").value = body;
  document.querySelector('.tab[data-tab="email"]').click();
  showToast("Loaded into email form.", true);
});

checkHealth();
