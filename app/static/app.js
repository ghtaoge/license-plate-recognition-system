(function () {
  const state = {
    selectedFile: null,
    previewUrl: "",
    requestId: 0,
    isRecognizing: false,
  };

  const elements = {
    providerBadge: document.getElementById("providerBadge"),
    dropZone: document.getElementById("dropZone"),
    fileInput: document.getElementById("fileInput"),
    chooseButton: document.getElementById("chooseButton"),
    recognizeButton: document.getElementById("recognizeButton"),
    clearButton: document.getElementById("clearButton"),
    refreshButton: document.getElementById("refreshButton"),
    message: document.getElementById("message"),
    fileName: document.getElementById("fileName"),
    previewImage: document.getElementById("previewImage"),
    emptyPreview: document.getElementById("emptyPreview"),
    resultStatus: document.getElementById("resultStatus"),
    plateNumber: document.getElementById("plateNumber"),
    confidence: document.getElementById("confidence"),
    provider: document.getElementById("provider"),
    elapsed: document.getElementById("elapsed"),
    historyBody: document.getElementById("historyBody"),
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function showMessage(text, type) {
    elements.message.textContent = text;
    elements.message.className = `message ${type || ""}`.trim();
    elements.message.hidden = false;
  }

  function hideMessage() {
    elements.message.hidden = true;
    elements.message.textContent = "";
    elements.message.className = "message";
  }

  function formatConfidence(value) {
    if (typeof value !== "number") {
      return "--";
    }

    return `${Math.round(value * 1000) / 10}%`;
  }

  function formatElapsed(value) {
    return Number.isFinite(Number(value)) ? `${value} ms` : "--";
  }

  function formatTime(value) {
    if (!value) {
      return "--";
    }

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return date.toLocaleString("zh-CN", { hour12: false });
  }

  function setResultStatus(text, className) {
    elements.resultStatus.textContent = text;
    elements.resultStatus.className = `badge ${className}`;
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, options);
    const contentType = response.headers.get("content-type") || "";
    const body = contentType.includes("application/json") ? await response.json() : null;

    if (!response.ok) {
      const message = body?.message || "请求失败，请稍后重试";
      throw new Error(message);
    }

    return body;
  }

  async function loadConfig() {
    try {
      const config = await fetchJson("/api/config");
      const provider = config?.provider || "--";
      elements.providerBadge.textContent = `当前模式：${provider}`;
      elements.provider.textContent = provider;
    } catch (error) {
      elements.providerBadge.textContent = "模式加载失败";
      elements.providerBadge.className = "badge badge-red";
      showMessage(`配置加载失败：${error.message}`, "error");
    }
  }

  function updateSelectedFile(file) {
    if (state.isRecognizing) {
      showMessage("识别中，请稍候再更换图片", "error");
      return;
    }

    if (!file) {
      clearSelection();
      return;
    }

    revokePreviewUrl();
    state.selectedFile = file;
    elements.fileName.textContent = file.name;
    elements.recognizeButton.disabled = false;
    elements.emptyPreview.hidden = true;
    elements.previewImage.hidden = false;
    state.previewUrl = URL.createObjectURL(file);
    elements.previewImage.src = state.previewUrl;
    hideMessage();
  }

  function clearSelection() {
    if (state.isRecognizing) {
      showMessage("识别中，请稍候再清空选择", "error");
      return;
    }

    revokePreviewUrl();
    state.selectedFile = null;
    elements.fileInput.value = "";
    elements.fileName.textContent = "未选择图片";
    elements.recognizeButton.disabled = true;
    elements.previewImage.removeAttribute("src");
    elements.previewImage.hidden = true;
    elements.emptyPreview.hidden = false;
    hideMessage();
  }

  function revokePreviewUrl() {
    if (state.previewUrl) {
      URL.revokeObjectURL(state.previewUrl);
      state.previewUrl = "";
    }
  }

  function renderResult(record) {
    elements.plateNumber.textContent = record.plate_number || "--";
    elements.confidence.textContent = formatConfidence(record.confidence);
    elements.provider.textContent = record.provider || "--";
    elements.elapsed.textContent = formatElapsed(record.elapsed_ms);

    if (record.status === "success") {
      setResultStatus("识别成功", "badge-green");
      showMessage(record.message || "识别完成", "success");
      return;
    }

    setResultStatus("识别异常", "badge-red");
    showMessage(record.error_message || "识别失败，请检查图片后重试", "error");
  }

  async function recognizeSelectedFile() {
    if (!state.selectedFile) {
      showMessage("请先上传图片", "error");
      return;
    }

    const requestId = state.requestId + 1;
    state.requestId = requestId;
    state.isRecognizing = true;

    const submittedFile = state.selectedFile;
    const formData = new FormData();
    formData.append("file", submittedFile);

    elements.recognizeButton.disabled = true;
    elements.chooseButton.disabled = true;
    elements.clearButton.disabled = true;
    elements.fileInput.disabled = true;
    setResultStatus("识别中", "badge-orange");
    showMessage("正在识别图片，请稍候", "");

    try {
      const result = await fetchJson("/api/recognitions", {
        method: "POST",
        body: formData,
      });
      if (requestId !== state.requestId || state.selectedFile !== submittedFile) {
        return;
      }
      renderResult(result);
      await loadHistory();
    } catch (error) {
      if (requestId !== state.requestId) {
        return;
      }
      setResultStatus("识别失败", "badge-red");
      showMessage(`识别失败：${error.message}`, "error");
    } finally {
      if (requestId === state.requestId) {
        state.isRecognizing = false;
        elements.chooseButton.disabled = false;
        elements.clearButton.disabled = false;
        elements.fileInput.disabled = false;
      }
      elements.recognizeButton.disabled = !state.selectedFile;
    }
  }

  function renderHistory(records) {
    if (!Array.isArray(records) || records.length === 0) {
      elements.historyBody.innerHTML = '<tr><td colspan="6" class="empty-cell">暂无识别记录</td></tr>';
      return;
    }

    elements.historyBody.innerHTML = records
      .map((record) => {
        const statusLabel = record.status === "success" ? "成功" : "异常";
        const statusClass = record.status === "success" ? "badge-green" : "badge-red";

        return `
          <tr>
            <td class="plate-cell">${escapeHtml(record.plate_number || "--")}</td>
            <td>${escapeHtml(formatConfidence(record.confidence))}</td>
            <td>${escapeHtml(record.provider || "--")}</td>
            <td><span class="badge ${statusClass}">${statusLabel}</span></td>
            <td>${escapeHtml(formatElapsed(record.elapsed_ms))}</td>
            <td>${escapeHtml(formatTime(record.created_at))}</td>
          </tr>
        `;
      })
      .join("");
  }

  async function loadHistory() {
    try {
      const records = await fetchJson("/api/recognitions");
      renderHistory(records);
    } catch (error) {
      elements.historyBody.innerHTML = `<tr><td colspan="6" class="empty-cell">${escapeHtml(
        `记录加载失败：${error.message}`,
      )}</td></tr>`;
    }
  }

  elements.chooseButton.addEventListener("click", () => elements.fileInput.click());
  elements.clearButton.addEventListener("click", clearSelection);
  elements.recognizeButton.addEventListener("click", recognizeSelectedFile);
  elements.refreshButton.addEventListener("click", loadHistory);

  elements.fileInput.addEventListener("change", (event) => {
    updateSelectedFile(event.target.files[0]);
  });

  elements.dropZone.addEventListener("dragover", (event) => {
    event.preventDefault();
    elements.dropZone.classList.add("drag-over");
  });

  elements.dropZone.addEventListener("dragleave", () => {
    elements.dropZone.classList.remove("drag-over");
  });

  elements.dropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    elements.dropZone.classList.remove("drag-over");
    updateSelectedFile(event.dataTransfer.files[0]);
  });

  loadConfig();
  loadHistory();
})();
