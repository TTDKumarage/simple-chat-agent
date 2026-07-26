const state = { siteTypes: [] };

function $(sel, root = document) {
  return root.querySelector(sel);
}

function showBanner(el, kind, html) {
  el.className = `result-banner show ${kind}`;
  el.innerHTML = html;
}

function hideBanner(el) {
  el.className = "result-banner";
  el.innerHTML = "";
}

// ---------- Tabs ----------
function initTabs() {
  const buttons = document.querySelectorAll(".tab-switch button");
  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(btn.dataset.panel).classList.add("active");
    });
  });
}

// ---------- Site type dropdowns ----------
async function loadSiteTypes() {
  const res = await fetch("/api/admin/site-types");
  state.siteTypes = await res.json();

  const kbSelect = $("#kb-type");
  const feSelect = $("#fe-type");
  for (const select of [kbSelect, feSelect]) {
    select.innerHTML = state.siteTypes
      .map((t) => `<option value="${t.value}">${t.label}</option>`)
      .join("");
  }
}

// ---------- Knowledge base tab ----------
let selectedFiles = [];
const ACCEPTED_EXT = [".md", ".markdown", ".txt", ".json"];

function isAccepted(file) {
  return ACCEPTED_EXT.some((ext) => file.name.toLowerCase().endsWith(ext));
}

function renderFileList() {
  const list = $("#file-list");
  list.innerHTML = selectedFiles
    .map(
      (f, i) => `
      <div class="file-item">
        <span><span class="name">${f.name}</span><span class="size">${(f.size / 1024).toFixed(1)} KB</span></span>
        <button type="button" data-remove="${i}" title="Remove">&times;</button>
      </div>`
    )
    .join("");
  list.querySelectorAll("[data-remove]").forEach((btn) => {
    btn.addEventListener("click", () => {
      selectedFiles.splice(Number(btn.dataset.remove), 1);
      renderFileList();
    });
  });
}

function addFiles(fileList) {
  for (const file of fileList) {
    if (!isAccepted(file)) continue;
    if (selectedFiles.some((f) => f.name === file.name && f.size === file.size)) continue;
    selectedFiles.push(file);
  }
  renderFileList();
}

function fillKbForm(cfg) {
  $("#kb-api-key").value = cfg.pinecone_api_key;
  $("#kb-index").value = cfg.pinecone_index_name;
  $("#kb-host").value = cfg.pinecone_host;
  $("#kb-namespace").value = cfg.pinecone_namespace;
  $("#kb-cloud").value = cfg.pinecone_cloud;
  $("#kb-region").value = cfg.pinecone_region;
  $("#kb-create-if-missing").checked = cfg.pinecone_create_if_missing;
  $("#kb-embedding-model").value = cfg.embedding_model;
  $("#kb-embedding-dim").value = cfg.embedding_dimension;
  $("#kb-embedding-key").value = cfg.embedding_api_key;
}

function readKbForm(type) {
  return {
    type,
    pinecone_api_key: $("#kb-api-key").value.trim(),
    pinecone_index_name: $("#kb-index").value.trim(),
    pinecone_host: $("#kb-host").value.trim(),
    pinecone_namespace: $("#kb-namespace").value.trim(),
    pinecone_cloud: $("#kb-cloud").value.trim() || "aws",
    pinecone_region: $("#kb-region").value.trim() || "us-east-1",
    pinecone_create_if_missing: $("#kb-create-if-missing").checked,
    embedding_model: $("#kb-embedding-model").value.trim() || "text-embedding-3-small",
    embedding_dimension: Number($("#kb-embedding-dim").value) || 1536,
    embedding_api_key: $("#kb-embedding-key").value.trim(),
  };
}

function initKnowledgeBaseTab() {
  const typeSelect = $("#kb-type");
  const namespaceInput = $("#kb-namespace");
  const settingsBanner = $("#kb-settings-result");
  const saveBtn = $("#kb-save");
  const resetBtn = $("#kb-reset");
  const clearBtn = $("#kb-clear");

  async function loadKbConfig() {
    hideBanner(settingsBanner);
    const res = await fetch(`/api/admin/kb-config/${typeSelect.value}`);
    const data = await res.json();
    fillKbForm(data);
  }

  typeSelect.addEventListener("change", loadKbConfig);

  saveBtn.addEventListener("click", async () => {
    hideBanner(settingsBanner);
    saveBtn.disabled = true;
    saveBtn.textContent = "Saving…";
    try {
      const res = await fetch("/api/admin/kb-config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(readKbForm(typeSelect.value)),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
      fillKbForm(data);
      showBanner(settingsBanner, "ok", "Settings saved. They'll be pre-filled next time you open this tab.");
    } catch (err) {
      showBanner(settingsBanner, "err", `<strong>Save failed.</strong> ${err.message}`);
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = "Save settings";
    }
  });

  resetBtn.addEventListener("click", async () => {
    await loadKbConfig();
    showBanner(settingsBanner, "ok", "Unsaved changes discarded — reverted to the last saved settings.");
  });

  clearBtn.addEventListener("click", async () => {
    if (!confirm("Clear all saved connection settings for this site type? This can't be undone.")) return;
    hideBanner(settingsBanner);
    clearBtn.disabled = true;
    try {
      const res = await fetch(`/api/admin/kb-config/${typeSelect.value}/clear`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
      fillKbForm(data);
      showBanner(settingsBanner, "ok", "Saved settings cleared for this site type.");
    } catch (err) {
      showBanner(settingsBanner, "err", `<strong>Clear failed.</strong> ${err.message}`);
    } finally {
      clearBtn.disabled = false;
    }
  });

  loadKbConfig();

  const dropzone = $("#dropzone");
  const fileInput = $("#file-input");

  dropzone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    addFiles(fileInput.files);
    fileInput.value = "";
  });

  ["dragenter", "dragover"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("drag-over");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("drag-over");
    })
  );
  dropzone.addEventListener("drop", (e) => {
    addFiles(e.dataTransfer.files);
  });

  const form = $("#kb-form");
  const banner = $("#kb-result");
  const submitBtn = $("#kb-submit");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideBanner(banner);

    if (!selectedFiles.length) {
      showBanner(banner, "err", "Add at least one file to embed.");
      return;
    }

    const indexName = $("#kb-index").value.trim();
    const host = $("#kb-host").value.trim();
    if (!indexName && !host) {
      showBanner(banner, "err", "Enter either an index name or a Pinecone host.");
      return;
    }

    const fd = new FormData();
    fd.append("site_type", typeSelect.value);
    fd.append("pinecone_api_key", $("#kb-api-key").value.trim());
    fd.append("pinecone_index_name", indexName);
    fd.append("pinecone_host", host);
    fd.append("pinecone_namespace", namespaceInput.value.trim());
    fd.append("pinecone_cloud", $("#kb-cloud").value.trim() || "aws");
    fd.append("pinecone_region", $("#kb-region").value.trim() || "us-east-1");
    fd.append("pinecone_create_if_missing", $("#kb-create-if-missing").checked ? "true" : "false");
    fd.append("embedding_model", $("#kb-embedding-model").value.trim() || "text-embedding-3-small");
    fd.append("embedding_dimension", $("#kb-embedding-dim").value.trim() || "1536");
    fd.append("embedding_api_key", $("#kb-embedding-key").value.trim());
    selectedFiles.forEach((f) => fd.append("files", f));

    submitBtn.disabled = true;
    submitBtn.textContent = "Embedding…";

    try {
      const res = await fetch("/api/admin/embeddings", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);

      const fileRows = data.files.map((f) => `<li>${f.filename} — ${f.chunks} chunk(s)</li>`).join("");
      showBanner(
        banner,
        "ok",
        `<strong>Embedded successfully.</strong> ${data.chunks_embedded} chunk(s) from ${data.files_processed} file(s) into index "${data.index_name}" (namespace: ${data.namespace}).<ul>${fileRows}</ul>`
      );
      selectedFiles = [];
      renderFileList();
    } catch (err) {
      showBanner(banner, "err", `<strong>Embedding failed.</strong> ${err.message}`);
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Embed files";
    }
  });
}

// ---------- Manage embedded files ----------
function initEmbeddedFilesManager() {
  const loadBtn = $("#kb-load-files");
  const listEl = $("#embedded-file-list");
  const banner = $("#kb-files-result");

  function connectionPayload() {
    return {
      pinecone_api_key: $("#kb-api-key").value.trim(),
      pinecone_index_name: $("#kb-index").value.trim(),
      pinecone_host: $("#kb-host").value.trim(),
      pinecone_namespace: $("#kb-namespace").value.trim(),
    };
  }

  function renderFiles(files, payload) {
    if (!files.length) {
      listEl.innerHTML = `<div class="file-item"><span>No embedded files found in this namespace.</span></div>`;
      return;
    }
    listEl.innerHTML = files
      .map(
        (f) => `
        <div class="file-item">
          <span><span class="name">${f.filename}</span><span class="size">${f.chunks} chunk(s)</span></span>
          <button type="button" data-delete="${encodeURIComponent(f.filename)}" title="Delete">&times;</button>
        </div>`
      )
      .join("");

    listEl.querySelectorAll("[data-delete]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const filename = decodeURIComponent(btn.dataset.delete);
        if (!confirm(`Delete all embedded chunks for "${filename}"? This can't be undone.`)) return;
        btn.disabled = true;
        try {
          const res = await fetch("/api/admin/embedded-files/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(Object.assign({}, payload, { filename })),
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
          showBanner(banner, "ok", `Deleted ${data.chunks_deleted} chunk(s) for "${filename}".`);
          loadFiles();
        } catch (err) {
          showBanner(banner, "err", `<strong>Delete failed.</strong> ${err.message}`);
          btn.disabled = false;
        }
      });
    });
  }

  async function loadFiles() {
    hideBanner(banner);
    const payload = connectionPayload();

    if (!payload.pinecone_api_key) {
      showBanner(banner, "err", "Enter your Pinecone API key above first.");
      return;
    }
    if (!payload.pinecone_index_name && !payload.pinecone_host) {
      showBanner(banner, "err", "Enter an index name or host above first.");
      return;
    }

    loadBtn.disabled = true;
    loadBtn.textContent = "Loading…";
    listEl.innerHTML = "";

    try {
      const res = await fetch("/api/admin/embedded-files", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
      renderFiles(data.files, payload);
    } catch (err) {
      showBanner(banner, "err", `<strong>Couldn't load files.</strong> ${err.message}`);
    } finally {
      loadBtn.disabled = false;
      loadBtn.textContent = "Load embedded files";
    }
  }

  loadBtn.addEventListener("click", loadFiles);
}

// ---------- Frontend config tab ----------
function initFrontendTab() {
  const typeSelect = $("#fe-type");
  const brandField = $("#fe-brand");
  const apiBaseField = $("#fe-api-base");
  const greetingField = $("#fe-greeting");
  const useGatewayKeyField = $("#fe-use-gateway-key");
  const apiKeyField = $("#fe-api-key");
  const apiKeyFieldWrap = $("#fe-api-key-field");
  const viewLink = $("#fe-view-link");
  const banner = $("#fe-result");
  const form = $("#fe-form");
  const submitBtn = $("#fe-submit");

  function syncApiKeyVisibility() {
    apiKeyFieldWrap.style.display = useGatewayKeyField.checked ? "block" : "none";
  }
  useGatewayKeyField.addEventListener("change", syncApiKeyVisibility);

  async function loadConfig() {
    hideBanner(banner);
    const type = typeSelect.value;
    const res = await fetch(`/api/admin/frontend-config/${type}`);
    const data = await res.json();
    brandField.value = data.brand;
    apiBaseField.value = data.api_base;
    greetingField.value = data.greeting;
    useGatewayKeyField.checked = data.use_gateway_key;
    apiKeyField.value = data.api_key;
    syncApiKeyVisibility();
    viewLink.href = `/${type}`;
  }

  typeSelect.addEventListener("change", loadConfig);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideBanner(banner);

    if (useGatewayKeyField.checked && !apiKeyField.value.trim()) {
      showBanner(banner, "err", "Enter a gateway API key, or uncheck the gateway option.");
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Saving…";

    try {
      const res = await fetch("/api/admin/frontend-config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: typeSelect.value,
          api_base: apiBaseField.value.trim(),
          greeting: greetingField.value.trim(),
          use_gateway_key: useGatewayKeyField.checked,
          api_key: apiKeyField.value.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
      showBanner(banner, "ok", "Saved. The chat widget on the live site now uses this config — no rebuild needed.");
    } catch (err) {
      showBanner(banner, "err", `<strong>Save failed.</strong> ${err.message}`);
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Save changes";
    }
  });

  loadConfig();
}

async function init() {
  initTabs();
  await loadSiteTypes();
  initKnowledgeBaseTab();
  initEmbeddedFilesManager();
  initFrontendTab();
}

document.addEventListener("DOMContentLoaded", init);
