(function () {
  const state = {
    selectedFile: null,
    previewUrl: "",
    requestId: 0,
    isRecognizing: false,
    historyPage: 1,
    historyLimit: 20,
    historyTotal: 0,
  };

  const elements = {
    providerBadge: document.getElementById("providerBadge"),
    dropZone: document.getElementById("dropZone"),
    fileInput: document.getElementById("fileInput"),
    chooseButton: document.getElementById("chooseButton"),
    recognizeButton: document.getElementById("recognizeButton"),
    clearButton: document.getElementById("clearButton"),
    refreshButton: document.getElementById("refreshButton"),
    clearHistoryButton: document.getElementById("clearHistoryButton"),
    message: document.getElementById("message"),
    fileName: document.getElementById("fileName"),
    previewImage: document.getElementById("previewImage"),
    emptyPreview: document.getElementById("emptyPreview"),
    resultStatus: document.getElementById("resultStatus"),
    plateNumber: document.getElementById("plateNumber"),
    confidence: document.getElementById("confidence"),
    provider: document.getElementById("provider"),
    elapsed: document.getElementById("elapsed"),
    bboxInfo: document.getElementById("bboxInfo"),
    historyBody: document.getElementById("historyBody"),
    paginationInfo: document.getElementById("paginationInfo"),
    prevPageButton: document.getElementById("prevPageButton"),
    nextPageButton: document.getElementById("nextPageButton"),
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

  function formatBbox(bbox) {
    if (!bbox) {
      return "--";
    }
    return `(${bbox.x1}, ${bbox.y1}) → (${bbox.x2}, ${bbox.y2})`;
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
    elements.bboxInfo.textContent = formatBbox(record.bbox);

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
      state.historyPage = 1;
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

  function renderHistory(data) {
    const records = data.records || [];
    state.historyTotal = data.total || 0;
    state.historyPage = data.page;

    if (!Array.isArray(records) || records.length === 0) {
      elements.historyBody.innerHTML = '<tr><td colspan="8" class="empty-cell">暂无识别记录</td></tr>';
      updatePagination();
      return;
    }

    elements.historyBody.innerHTML = records
      .map((record) => {
        const statusLabel = record.status === "success" ? "成功" : "异常";
        const statusClass = record.status === "success" ? "badge-green" : "badge-red";
        const thumbnail = record.image_url
          ? `<img src="${escapeHtml(record.image_url)}" alt="缩略图" class="history-thumb" loading="lazy">`
          : "--";

        return `
          <tr>
            <td class="thumb-cell">${thumbnail}</td>
            <td class="plate-cell">${escapeHtml(record.plate_number || "--")}</td>
            <td>${escapeHtml(formatConfidence(record.confidence))}</td>
            <td>${escapeHtml(record.provider || "--")}</td>
            <td><span class="badge ${statusClass}">${statusLabel}</span></td>
            <td>${escapeHtml(formatElapsed(record.elapsed_ms))}</td>
            <td>${escapeHtml(formatTime(record.created_at))}</td>
            <td class="action-cell"><button class="btn btn-ghost btn-sm delete-btn" data-id="${record.id}" title="删除此记录">删除</button></td>
          </tr>
        `;
      })
      .join("");

    updatePagination();

    // Bind delete buttons
    elements.historyBody.querySelectorAll(".delete-btn").forEach((btn) => {
      btn.addEventListener("click", () => deleteRecord(parseInt(btn.dataset.id, 10)));
    });
  }

  function updatePagination() {
    const totalPages = Math.ceil(state.historyTotal / state.historyLimit) || 1;
    const currentPage = state.historyPage;
    const showingStart = (currentPage - 1) * state.historyLimit + 1;
    const showingEnd = Math.min(currentPage * state.historyLimit, state.historyTotal);

    if (state.historyTotal === 0) {
      elements.paginationInfo.textContent = "暂无记录";
    } else {
      elements.paginationInfo.textContent = `第 ${showingStart}-${showingEnd} 条 / 共 ${state.historyTotal} 条 · 第 ${currentPage}/${totalPages} 页`;
    }

    elements.prevPageButton.disabled = currentPage <= 1;
    elements.nextPageButton.disabled = currentPage >= totalPages;
  }

  async function loadHistory() {
    try {
      const data = await fetchJson(`/api/recognitions?limit=${state.historyLimit}&page=${state.historyPage}`);
      renderHistory(data);
    } catch (error) {
      elements.historyBody.innerHTML = `<tr><td colspan="8" class="empty-cell">${escapeHtml(
        `记录加载失败：${error.message}`,
      )}</td></tr>`;
    }
  }

  async function deleteRecord(recordId) {
    try {
      await fetchJson(`/api/recognitions/${recordId}`, { method: "DELETE" });
      await loadHistory();
    } catch (error) {
      showMessage(`删除失败：${error.message}`, "error");
    }
  }

  async function clearAllHistory() {
    if (!confirm("确定要清空所有识别记录吗？此操作不可恢复。")) {
      return;
    }
    try {
      await fetchJson("/api/recognitions", { method: "DELETE" });
      state.historyPage = 1;
      await loadHistory();
      showMessage("已清空所有记录", "success");
    } catch (error) {
      showMessage(`清空失败：${error.message}`, "error");
    }
  }

  function prevPage() {
    if (state.historyPage > 1) {
      state.historyPage--;
      loadHistory();
    }
  }

  function nextPage() {
    const totalPages = Math.ceil(state.historyTotal / state.historyLimit) || 1;
    if (state.historyPage < totalPages) {
      state.historyPage++;
      loadHistory();
    }
  }

  elements.chooseButton.addEventListener("click", () => elements.fileInput.click());
  elements.clearButton.addEventListener("click", clearSelection);
  elements.recognizeButton.addEventListener("click", recognizeSelectedFile);
  elements.refreshButton.addEventListener("click", () => loadHistory());
  if (elements.clearHistoryButton) {
    elements.clearHistoryButton.addEventListener("click", clearAllHistory);
  }
  if (elements.prevPageButton) {
    elements.prevPageButton.addEventListener("click", prevPage);
  }
  if (elements.nextPageButton) {
    elements.nextPageButton.addEventListener("click", nextPage);
  }

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
