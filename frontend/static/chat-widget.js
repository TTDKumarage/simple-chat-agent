(function () {
  const config = Object.assign(
    {
      apiBase: "",
      apiKey: "",
      brand: "Chat Assistant",
      accent: "#2563eb",
      accentDark: "#111827",
      storageKey: "chat-widget-session",
      greeting: "Hi! Ask me anything about our products.",
    },
    window.CHAT_WIDGET_CONFIG || {}
  );

  const apiUrl = (path) => `${config.apiBase}${path}`;
  const apiHeaders = (extra) =>
    config.apiKey ? Object.assign({ "X-API-Key": config.apiKey }, extra) : extra || {};

  const CHAT_ICON = `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>`;
  const CLOSE_ICON = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;
  const RESET_ICON = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>`;
  const PANEL_CLOSE_ICON = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;

  function getSessionId() {
    let id = localStorage.getItem(config.storageKey);
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem(config.storageKey, id);
    }
    return id;
  }

  function injectStyles() {
    const style = document.createElement("style");
    style.textContent = `
      .cw-launcher {
        position: fixed; right: 24px; bottom: 24px; z-index: 999;
        width: 60px; height: 60px; border-radius: 50%;
        background: ${config.accent}; color: #fff;
        display: flex; align-items: center; justify-content: center;
        font-size: 26px; cursor: pointer; border: none;
        box-shadow: 0 12px 28px rgba(0,0,0,0.22);
        transition: transform 0.15s ease;
      }
      .cw-launcher:hover { transform: translateY(-2px) scale(1.04); }
      .cw-panel {
        position: fixed; right: 24px; bottom: 96px; z-index: 999;
        width: 370px; max-width: calc(100vw - 32px);
        height: 540px; max-height: calc(100vh - 140px);
        background: #fff; border-radius: 16px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.28);
        display: flex; flex-direction: column; overflow: hidden;
        opacity: 0; transform: translateY(16px) scale(0.98);
        pointer-events: none; transition: opacity 0.18s ease, transform 0.18s ease;
        font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      }
      .cw-panel.cw-open { opacity: 1; transform: translateY(0) scale(1); pointer-events: auto; }
      .cw-header {
        background: ${config.accentDark}; color: #fff;
        padding: 14px 16px; display: flex; align-items: center; justify-content: space-between;
        flex-shrink: 0;
      }
      .cw-header-title { display: flex; align-items: center; gap: 8px; font-size: 14.5px; font-weight: 600; }
      .cw-dot { width: 8px; height: 8px; border-radius: 50%; background: #34d399; display: inline-block; }
      .cw-header-actions { display: flex; gap: 6px; }
      .cw-header-actions button {
        background: rgba(255,255,255,0.12); border: none; color: #fff;
        width: 26px; height: 26px; border-radius: 6px; cursor: pointer;
        display: flex; align-items: center; justify-content: center;
      }
      .cw-header-actions button:hover { background: rgba(255,255,255,0.24); }
      .cw-messages {
        flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 10px;
        background: #f7f8fa;
      }
      .cw-msg { max-width: 84%; padding: 9px 13px; border-radius: 12px; font-size: 14px; line-height: 1.45; white-space: pre-wrap; }
      .cw-msg.user { align-self: flex-end; background: ${config.accent}; color: #fff; border-bottom-right-radius: 3px; }
      .cw-msg.assistant { align-self: flex-start; background: #fff; color: #1c2733; border: 1px solid #e3e8ee; border-bottom-left-radius: 3px; }
      .cw-msg.error { align-self: center; background: #fde8e8; color: #a12626; font-size: 13px; }
      .cw-form { display: flex; gap: 8px; padding: 12px; border-top: 1px solid #e3e8ee; flex-shrink: 0; background: #fff; }
      .cw-form textarea {
        flex: 1; resize: none; border: 1px solid #dfe3e8; border-radius: 10px; padding: 9px 11px;
        font-size: 14px; font-family: inherit; max-height: 100px; line-height: 1.4;
      }
      .cw-form textarea:focus { outline: none; border-color: ${config.accent}; }
      .cw-form button {
        background: ${config.accent}; color: #fff; border: none; border-radius: 10px;
        padding: 0 16px; font-weight: 600; font-size: 14px; cursor: pointer;
      }
      .cw-form button:disabled { opacity: 0.6; cursor: default; }
      @media (max-width: 480px) {
        .cw-panel { right: 12px; left: 12px; width: auto; bottom: 88px; }
        .cw-launcher { right: 16px; bottom: 16px; }
      }
    `;
    document.head.appendChild(style);
  }

  function buildDom() {
    const launcher = document.createElement("button");
    launcher.className = "cw-launcher";
    launcher.type = "button";
    launcher.id = "cw-launcher";
    launcher.title = `Chat with ${config.brand}`;
    launcher.innerHTML = CHAT_ICON;

    const panel = document.createElement("div");
    panel.className = "cw-panel";
    panel.id = "cw-panel";
    panel.innerHTML = `
      <div class="cw-header">
        <div class="cw-header-title"><span class="cw-dot"></span> ${config.brand}</div>
        <div class="cw-header-actions">
          <button type="button" id="cw-reset" title="Clear conversation">${RESET_ICON}</button>
          <button type="button" id="cw-close" title="Close">${PANEL_CLOSE_ICON}</button>
        </div>
      </div>
      <div class="cw-messages" id="cw-messages"></div>
      <form class="cw-form" id="cw-form">
        <textarea id="cw-input" rows="1" placeholder="Ask something…"></textarea>
        <button type="submit" id="cw-send">Send</button>
      </form>
    `;

    document.body.appendChild(launcher);
    document.body.appendChild(panel);
    return { launcher, panel };
  }

  function addMessage(container, role, text) {
    const el = document.createElement("div");
    el.className = `cw-msg ${role}`;
    el.textContent = text;
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
    return el;
  }

  async function sendMessage(messages, sendButton, message) {
    const sessionId = getSessionId();
    addMessage(messages, "user", message);
    const assistantEl = addMessage(messages, "assistant", "");
    sendButton.disabled = true;

    try {
      const res = await fetch(apiUrl("/api/chat/stream"), {
        method: "POST",
        headers: apiHeaders({ "Content-Type": "application/json" }),
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
        messages.scrollTop = messages.scrollHeight;
      }

      if (!text) {
        assistantEl.remove();
        addMessage(messages, "error", "The model returned an empty response.");
      }
    } catch (err) {
      assistantEl.remove();
      addMessage(messages, "error", `Something went wrong: ${err.message}`);
    } finally {
      sendButton.disabled = false;
    }
  }

  function init() {
    injectStyles();
    const { launcher, panel } = buildDom();

    const messages = panel.querySelector("#cw-messages");
    const form = panel.querySelector("#cw-form");
    const input = panel.querySelector("#cw-input");
    const sendButton = panel.querySelector("#cw-send");
    const closeButton = panel.querySelector("#cw-close");
    const resetButton = panel.querySelector("#cw-reset");

    let loaded = false;
    function openPanel() {
      panel.classList.add("cw-open");
      launcher.innerHTML = CLOSE_ICON;
      launcher.title = "Close chat";
      if (!loaded) {
        loaded = true;
        if (config.greeting) addMessage(messages, "assistant", config.greeting);
      }
      input.focus();
    }
    function closePanel() {
      panel.classList.remove("cw-open");
      launcher.innerHTML = CHAT_ICON;
      launcher.title = `Chat with ${config.brand}`;
    }
    function togglePanel() {
      panel.classList.contains("cw-open") ? closePanel() : openPanel();
    }

    launcher.addEventListener("click", togglePanel);
    closeButton.addEventListener("click", closePanel);

    document.addEventListener("click", (event) => {
      const trigger = event.target.closest("[data-chat-widget-open]");
      if (!trigger) return;
      event.preventDefault();
      openPanel();
    });

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const message = input.value.trim();
      if (!message) return;
      input.value = "";
      input.style.height = "auto";
      sendMessage(messages, sendButton, message);
    });

    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
      }
    });

    input.addEventListener("input", () => {
      input.style.height = "auto";
      input.style.height = `${Math.min(input.scrollHeight, 100)}px`;
    });

    resetButton.addEventListener("click", async () => {
      const sessionId = getSessionId();
      await fetch(apiUrl("/api/reset"), {
        method: "POST",
        headers: apiHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ session_id: sessionId }),
      });
      messages.innerHTML = "";
      if (config.greeting) addMessage(messages, "assistant", config.greeting);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
