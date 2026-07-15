const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const sendButton = document.getElementById("send-button");
const resetButton = document.getElementById("reset-button");
const providerBadge = document.getElementById("provider-badge");

const SESSION_KEY = "simple-chat-agent:session-id";

function getSessionId() {
  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

function addMessage(role, text) {
  const el = document.createElement("div");
  el.className = `message ${role}`;
  el.textContent = text;
  chatWindow.appendChild(el);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return el;
}

async function loadConfig() {
  try {
    const res = await fetch("/api/config");
    const data = await res.json();
    providerBadge.textContent = `${data.provider} · ${data.model}${data.rag_enabled ? " · RAG" : ""}`;
  } catch {
    providerBadge.textContent = "offline";
  }
}

async function sendMessage(message) {
  const sessionId = getSessionId();
  addMessage("user", message);

  const assistantEl = addMessage("assistant", "");
  sendButton.disabled = true;

  try {
    const res = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });

    if (!res.ok || !res.body) {
      throw new Error(`Request failed (${res.status})`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let text = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      text += decoder.decode(value, { stream: true });
      assistantEl.textContent = text;
      chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    if (!text) {
      assistantEl.remove();
      addMessage("error", "The model returned an empty response.");
    }
  } catch (err) {
    assistantEl.remove();
    addMessage("error", `Something went wrong: ${err.message}`);
  } finally {
    sendButton.disabled = false;
  }
}

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;
  chatInput.value = "";
  chatInput.style.height = "auto";
  sendMessage(message);
});

chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

chatInput.addEventListener("input", () => {
  chatInput.style.height = "auto";
  chatInput.style.height = `${Math.min(chatInput.scrollHeight, 160)}px`;
});

resetButton.addEventListener("click", async () => {
  const sessionId = getSessionId();
  await fetch("/api/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  chatWindow.innerHTML = "";
});

loadConfig();
