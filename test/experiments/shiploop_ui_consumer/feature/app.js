(() => {
  "use strict";

  const POLL_INTERVAL_MS = 15_000;

  const state = {
    account: "alpha",
    notes: [],
    record: null,
    selectedId: null,
    editing: false,
    sessionEpoch: 0,
    draftVersion: 0,
    listController: null,
    readControllers: new Set(),
    saveController: null,
    pendingSave: null,
    conflict: null,
    pollTimer: null,
    cue: null,
    hiddenDirty: false,
    hintRefresh: freshRefreshQueue(),
    pollRefresh: freshRefreshQueue(),
  };

  const elements = {
    account: document.querySelector("#account"),
    notesView: document.querySelector("#notes-view"),
    listMessage: document.querySelector("#list-message"),
    noteList: document.querySelector("#note-list"),
    detail: document.querySelector("#detail"),
    noteTitle: document.querySelector("#note-title"),
    confirmedNote: document.querySelector("#confirmed-note"),
    revision: document.querySelector("#revision"),
    noteInput: document.querySelector("#note-input"),
    back: document.querySelector("#back"),
    edit: document.querySelector("#edit"),
    save: document.querySelector("#save"),
    cancel: document.querySelector("#cancel"),
    refresh: document.querySelector("#refresh"),
    retrySave: document.querySelector("#retry-save"),
    reapply: document.querySelector("#reapply"),
    saveStatus: document.querySelector("#save-status"),
    exportStatus: document.querySelector("#export-status"),
  };

  function freshRefreshQueue() {
    return { scheduled: false, inFlight: false, followUp: false, followUpUsed: false };
  }

  function noteUrl(account, id) {
    return `/api/accounts/${encodeURIComponent(account)}/notes/${encodeURIComponent(id)}`;
  }

  function operationUrl(account, id, idempotencyKey) {
    return `${noteUrl(account, id)}/operations/${encodeURIComponent(idempotencyKey)}`;
  }

  function readUrl(scope, source) {
    const url = noteUrl(scope.account, scope.noteId);
    // A manual retry is intentionally an independent read. Chrome can otherwise
    // coalesce two same-URL in-flight GETs before the service sees both.
    return source === "manual" ? `${url}?read=${encodeURIComponent(operationId())}` : url;
  }

  function operationId() {
    if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function") {
      return globalThis.crypto.randomUUID();
    }

    return `field-note-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function setMessage(element, message, tone = "normal") {
    if (element.textContent !== message) {
      element.textContent = message;
    }

    if (tone === "error") {
      if (element.dataset.tone !== "error") element.dataset.tone = "error";
    } else if (element.dataset.tone) {
      delete element.dataset.tone;
    }
  }

  function setSaving(isSaving) {
    for (const control of [elements.save, elements.cancel, elements.back, elements.edit, elements.retrySave, elements.reapply]) {
      control.disabled = isSaving;
    }
  }

  function setEditing(editing) {
    state.editing = editing;
    elements.noteInput.readOnly = !editing;
    elements.noteInput.setAttribute("aria-readonly", String(!editing));
    elements.edit.hidden = editing;
    elements.cancel.hidden = !editing;
    elements.save.hidden = !editing;
  }

  function updateRecoveryActions() {
    elements.retrySave.hidden = !state.pendingSave?.retryable;
    elements.reapply.hidden = !state.conflict;
  }

  function showList() {
    elements.detail.hidden = true;
    elements.notesView.hidden = false;
  }

  function showDetail() {
    elements.notesView.hidden = true;
    elements.detail.hidden = false;
  }

  function currentScope() {
    if (!state.selectedId) return null;
    return {
      epoch: state.sessionEpoch,
      account: state.account,
      noteId: state.selectedId,
    };
  }

  function scopeIsCurrent(scope) {
    return Boolean(
      scope
      && !elements.detail.hidden
      && state.sessionEpoch === scope.epoch
      && state.account === scope.account
      && state.selectedId === scope.noteId,
    );
  }

  function listScopeIsCurrent(scope) {
    return state.sessionEpoch === scope.epoch && state.account === scope.account;
  }

  function isVisibleDetail(scope = currentScope()) {
    return scopeIsCurrent(scope) && document.visibilityState === "visible";
  }

  function stopPolling() {
    if (state.pollTimer !== null) {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
    }
  }

  function startPolling() {
    stopPolling();
    const scope = currentScope();
    if (!isVisibleDetail(scope)) return;

    state.pollTimer = setInterval(() => {
      if (!isVisibleDetail(scope)) {
        stopPolling();
        return;
      }
      enqueueBackgroundRefresh("poll", scope);
    }, POLL_INTERVAL_MS);
  }

  function cancelCue() {
    if (state.cue?.animation) {
      try {
        state.cue.animation.cancel();
      } catch {
        // A finished animation has no domain consequence to recover from.
      }
    }
    state.cue = null;
  }

  function startExportCue(scope) {
    cancelCue();
    if (!scopeIsCurrent(scope) || window.matchMedia("(prefers-reduced-motion: reduce)").matches || typeof elements.exportStatus.animate !== "function") {
      return;
    }

    const animation = elements.exportStatus.animate(
      [
        { backgroundColor: "rgba(192, 135, 34, 0)", color: "rgb(95, 110, 125)" },
        { backgroundColor: "rgba(192, 135, 34, 0.22)", color: "rgb(21, 50, 79)" },
        { backgroundColor: "rgba(192, 135, 34, 0)", color: "rgb(95, 110, 125)" },
      ],
      { duration: 180, easing: "ease-out" },
    );
    animation.finished.catch(() => {});
    state.cue = { scope, animation };
  }

  function abortReadRequests() {
    for (const controller of state.readControllers) controller.abort();
    state.readControllers.clear();
  }

  function resetRefreshQueues() {
    state.hintRefresh = freshRefreshQueue();
    state.pollRefresh = freshRefreshQueue();
    state.hiddenDirty = false;
  }

  function discardDetailSession() {
    state.sessionEpoch += 1;
    stopPolling();
    cancelCue();
    abortReadRequests();
    state.saveController?.abort();
    state.saveController = null;
    state.pendingSave = null;
    state.conflict = null;
    state.record = null;
    state.selectedId = null;
    state.draftVersion += 1;
    resetRefreshQueues();
    setEditing(false);
    setSaving(false);
    updateRecoveryActions();
    setMessage(elements.saveStatus, "");
    setMessage(elements.exportStatus, "");
  }

  function renderList() {
    elements.noteList.replaceChildren();

    for (const note of state.notes) {
      const button = document.createElement("button");
      const copy = document.createElement("span");
      const title = document.createElement("span");
      const preview = document.createElement("span");
      const marker = document.createElement("span");

      button.type = "button";
      button.className = "note-button";
      button.dataset.noteId = note.id;
      button.setAttribute("aria-label", `Open ${note.title}`);

      copy.className = "note-button-copy";
      title.className = "note-button-title";
      title.textContent = note.title;
      preview.className = "note-button-preview";
      preview.textContent = note.note;
      marker.className = "note-button-mark";
      marker.setAttribute("aria-hidden", "true");

      copy.append(title, preview);
      button.append(copy, marker);
      elements.noteList.append(button);
    }
  }

  function renderConfirmedRecord() {
    const record = state.record;
    if (!record) return;

    elements.noteTitle.textContent = record.title;
    elements.confirmedNote.textContent = record.note;
    elements.revision.textContent = String(record.revision);
  }

  function syncInputFromConfirmed() {
    if (state.record && !state.editing) {
      elements.noteInput.value = state.record.note;
    }
  }

  function revision(value) {
    return Number.isInteger(value) ? value : 0;
  }

  function exportMessage(record) {
    return `Export status: ${record.exportStatus || "idle"}.`;
  }

  function mergeRecord(incoming, { source }) {
    if (!incoming || typeof incoming !== "object") {
      throw new Error("The service returned an incomplete note record.");
    }

    const prior = state.record;
    if (!prior) {
      state.record = { ...incoming };
      renderConfirmedRecord();
      syncInputFromConfirmed();
      setMessage(elements.exportStatus, exportMessage(state.record));
      return { resourceChanged: true, exportChanged: true };
    }

    const priorRevision = revision(prior.revision);
    const incomingRevision = revision(incoming.revision);
    const priorExportRevision = revision(prior.exportRevision);
    const incomingExportRevision = revision(incoming.exportRevision);
    const resourceChanged = incomingRevision > priorRevision;
    const exportChanged = incomingExportRevision > priorExportRevision;
    const acceptResource = incomingRevision >= priorRevision;
    const acceptExport = incomingExportRevision >= priorExportRevision;
    const next = { ...prior };

    if (acceptResource) {
      next.id = incoming.id;
      next.title = incoming.title;
      next.note = incoming.note;
      next.revision = incoming.revision;
    }
    if (acceptExport) {
      next.exportStatus = incoming.exportStatus;
      next.exportRevision = incoming.exportRevision;
    }

    state.record = next;
    if (acceptResource) renderConfirmedRecord();
    if (exportChanged) {
      setMessage(elements.exportStatus, exportMessage(next));
      if (source !== "open") startExportCue(currentScope());
    }

    return { resourceChanged, exportChanged };
  }

  async function responseJson(response) {
    let payload;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }

    if (!response.ok) {
      const error = new Error("The service could not complete that request.");
      error.response = response;
      error.payload = payload;
      throw error;
    }

    return payload;
  }

  async function loadList() {
    state.listController?.abort();
    const controller = new AbortController();
    const scope = { epoch: state.sessionEpoch, account: state.account };
    state.listController = controller;

    if (!elements.notesView.hidden) {
      setMessage(elements.listMessage, "Loading notes…");
      elements.noteList.replaceChildren();
    }

    try {
      const response = await fetch(
        `/api/accounts/${encodeURIComponent(scope.account)}/notes`,
        { signal: controller.signal, headers: { Accept: "application/json" } },
      );
      const notes = await responseJson(response);
      if (controller.signal.aborted || !listScopeIsCurrent(scope)) return;

      state.notes = Array.isArray(notes) ? notes : [];
      renderList();
      setMessage(elements.listMessage, state.notes.length === 0 ? "No notes are available for this account." : "");
    } catch (error) {
      if (controller.signal.aborted || !listScopeIsCurrent(scope)) return;
      setMessage(elements.listMessage, "Notes could not be loaded. Choose the account again to try again.", "error");
    } finally {
      if (state.listController === controller) state.listController = null;
    }
  }

  function readFailureMessage(error, source) {
    if (error.response?.status === 404) return "This note is no longer available. Return to notes, then choose another note.";
    if (source === "open") return "This note could not be loaded. Refresh to try again.";
    return "Could not refresh the current export status. Refresh to try again.";
  }

  async function readRecord(scope, { source }) {
    const controller = new AbortController();
    state.readControllers.add(controller);

    try {
      const response = await fetch(readUrl(scope, source), {
        signal: controller.signal,
        headers: { Accept: "application/json" },
      });
      const record = await responseJson(response);
      if (controller.signal.aborted || !scopeIsCurrent(scope)) return false;

      mergeRecord(record, { source });
      state.hiddenDirty = false;
      return true;
    } catch (error) {
      if (!controller.signal.aborted && scopeIsCurrent(scope)) {
        setMessage(elements.exportStatus, readFailureMessage(error, source), "error");
      }
      return false;
    } finally {
      state.readControllers.delete(controller);
    }
  }

  function runBackgroundRefresh(kind, scope) {
    const queue = kind === "hint" ? state.hintRefresh : state.pollRefresh;
    queue.scheduled = false;
    if (!isVisibleDetail(scope)) {
      queue.followUp = false;
      queue.followUpUsed = false;
      return;
    }

    queue.inFlight = true;
    void readRecord(scope, { source: kind }).finally(() => {
      if (!scopeIsCurrent(scope)) {
        queue.inFlight = false;
        queue.followUp = false;
        queue.followUpUsed = false;
        return;
      }

      queue.inFlight = false;
      if (queue.followUp && !queue.followUpUsed && isVisibleDetail(scope)) {
        queue.followUp = false;
        queue.followUpUsed = true;
        queue.scheduled = true;
        queueMicrotask(() => runBackgroundRefresh(kind, scope));
        return;
      }

      queue.followUp = false;
      queue.followUpUsed = false;
    });
  }

  function enqueueBackgroundRefresh(kind, scope = currentScope()) {
    const queue = kind === "hint" ? state.hintRefresh : state.pollRefresh;
    if (!isVisibleDetail(scope)) return;

    if (queue.inFlight) {
      if (!queue.followUpUsed) queue.followUp = true;
      return;
    }
    if (queue.scheduled) return;

    queue.scheduled = true;
    queueMicrotask(() => runBackgroundRefresh(kind, scope));
  }

  async function openNote(noteId) {
    discardDetailSession();
    state.selectedId = noteId;
    const scope = currentScope();

    showDetail();
    setEditing(false);
    elements.noteTitle.textContent = "Loading note";
    elements.confirmedNote.textContent = "";
    elements.revision.textContent = "—";
    elements.noteInput.value = "";
    setMessage(elements.saveStatus, "");
    setMessage(elements.exportStatus, "Loading export status…");

    await readRecord(scope, { source: "open" });
    if (scopeIsCurrent(scope)) startPolling();
  }

  function beginEditing() {
    if (!state.record || state.pendingSave) return;
    state.draftVersion += 1;
    state.conflict = null;
    updateRecoveryActions();
    setMessage(elements.saveStatus, "");
    setEditing(true);
    elements.noteInput.focus();
    elements.noteInput.setSelectionRange(elements.noteInput.value.length, elements.noteInput.value.length);
  }

  function cancelEditing() {
    if (!state.record || state.pendingSave) return;
    state.draftVersion += 1;
    elements.noteInput.value = state.record.note;
    state.conflict = null;
    updateRecoveryActions();
    setEditing(false);
    setMessage(elements.saveStatus, "Changes discarded.");
    elements.edit.focus();
  }

  function intentIsCurrent(intent) {
    return state.pendingSave === intent && scopeIsCurrent(intent.scope);
  }

  function createSaveIntent(baseRevision = state.record?.revision) {
    return {
      scope: currentScope(),
      operationId: operationId(),
      note: elements.noteInput.value,
      baseRevision,
      draftVersion: state.draftVersion,
      retryable: false,
    };
  }

  function acceptSaveSuccess(intent, record) {
    if (!intentIsCurrent(intent)) return;

    mergeRecord(record, { source: "save" });
    state.pendingSave = null;
    state.conflict = null;
    updateRecoveryActions();

    const draftUnchanged = state.draftVersion === intent.draftVersion && elements.noteInput.value === intent.note;
    if (draftUnchanged) {
      setEditing(false);
      syncInputFromConfirmed();
      setMessage(elements.saveStatus, "Changes saved.");
    } else {
      setMessage(elements.saveStatus, "Changes saved. Your newer working text is still here.");
    }
    void loadList();
  }

  function handleSaveFailure(intent, error, phase) {
    if (!intentIsCurrent(intent)) return;

    if ((phase === "save" || phase === "replay") && error.response?.status === 409 && error.payload?.record) {
      mergeRecord(error.payload.record, { source: "save" });
      state.pendingSave = null;
      state.conflict = { scope: intent.scope };
      updateRecoveryActions();
      setMessage(elements.saveStatus, "A newer version is confirmed. Reapply your text to it when ready.", "error");
      return;
    }

    if (error.response?.status === 404) {
      state.pendingSave = null;
      updateRecoveryActions();
      setMessage(elements.saveStatus, "This note is no longer available. Your working text is still here.", "error");
      return;
    }

    intent.retryable = true;
    updateRecoveryActions();
    if (phase === "lookup") {
      setMessage(elements.saveStatus, "Could not check the previous save. Your working text is still here; retry save to try again.", "error");
    } else {
      setMessage(elements.saveStatus, "Changes could not be confirmed. Your working text is still here; retry save to try again.", "error");
    }
  }

  async function postIntent(intent, controller) {
    const response = await fetch(noteUrl(intent.scope.account, intent.scope.noteId), {
      method: "POST",
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        note: intent.note,
        baseRevision: intent.baseRevision,
        operationId: intent.operationId,
      }),
    });
    const payload = await responseJson(response);
    if (!payload?.record) throw new Error("The service did not confirm a note record.");
    if (!controller.signal.aborted) acceptSaveSuccess(intent, payload.record);
  }

  async function sendSaveIntent(intent, phase = "save") {
    if (!intentIsCurrent(intent)) return;
    state.saveController?.abort();
    const controller = new AbortController();
    state.saveController = controller;
    setSaving(true);
    setMessage(elements.saveStatus, phase === "replay" ? "Retrying save…" : "Saving changes…");

    try {
      await postIntent(intent, controller);
    } catch (error) {
      if (!controller.signal.aborted) handleSaveFailure(intent, error, phase);
    } finally {
      if (state.saveController === controller) {
        state.saveController = null;
        setSaving(false);
      }
    }
  }

  function saveEditing() {
    if (!state.record || !state.editing || state.pendingSave || !currentScope()) return;
    const intent = createSaveIntent();
    state.pendingSave = intent;
    state.conflict = null;
    updateRecoveryActions();
    void sendSaveIntent(intent);
  }

  async function retryPendingSave() {
    const intent = state.pendingSave;
    if (!intent || !intent.retryable || !intentIsCurrent(intent)) return;

    const controller = new AbortController();
    state.saveController?.abort();
    state.saveController = controller;
    setSaving(true);
    setMessage(elements.saveStatus, "Checking the previous save…");

    let phase = "lookup";
    try {
      const response = await fetch(operationUrl(intent.scope.account, intent.scope.noteId, intent.operationId), {
        signal: controller.signal,
        headers: { Accept: "application/json" },
      });
      const payload = await responseJson(response);
      if (controller.signal.aborted || !intentIsCurrent(intent)) return;

      if (payload?.state === "committed" && payload.record) {
        acceptSaveSuccess(intent, payload.record);
      } else if (payload?.state === "unknown") {
        phase = "replay";
        setMessage(elements.saveStatus, "Retrying save…");
        await postIntent(intent, controller);
      } else {
        throw new Error("The service returned an unknown save-recovery result.");
      }
    } catch (error) {
      if (!controller.signal.aborted) handleSaveFailure(intent, error, phase);
    } finally {
      if (state.saveController === controller) {
        state.saveController = null;
        setSaving(false);
      }
    }
  }

  function reapplyConflict() {
    if (!state.conflict || !scopeIsCurrent(state.conflict.scope) || !state.record || !state.editing) return;
    state.conflict = null;
    updateRecoveryActions();
    const intent = createSaveIntent(state.record.revision);
    state.pendingSave = intent;
    void sendSaveIntent(intent);
  }

  function refreshCurrent() {
    const scope = currentScope();
    if (!scopeIsCurrent(scope)) return;
    void readRecord(scope, { source: "manual" });
  }

  function switchAccount() {
    const account = elements.account.value;
    discardDetailSession();
    state.listController?.abort();
    state.account = account;
    showList();
    void loadList();
  }

  function returnToList() {
    discardDetailSession();
    showList();
    elements.noteList.querySelector("button")?.focus();
  }

  function handleUpdate(event) {
    const detail = event.detail || {};
    const scope = currentScope();
    if (!scope || detail.account !== scope.account || detail.noteId !== scope.noteId) return;

    if (document.visibilityState !== "visible") {
      state.hiddenDirty = true;
      return;
    }
    enqueueBackgroundRefresh("hint", scope);
  }

  function handleVisibilityChange() {
    const scope = currentScope();
    if (!scopeIsCurrent(scope)) return;

    if (document.visibilityState !== "visible") {
      stopPolling();
      return;
    }

    startPolling();
    enqueueBackgroundRefresh("poll", scope);
  }

  elements.account.addEventListener("change", switchAccount);
  elements.noteList.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-note-id]");
    if (button) void openNote(button.dataset.noteId);
  });
  elements.back.addEventListener("click", returnToList);
  elements.edit.addEventListener("click", beginEditing);
  elements.cancel.addEventListener("click", cancelEditing);
  elements.save.addEventListener("click", saveEditing);
  elements.refresh.addEventListener("click", refreshCurrent);
  elements.retrySave.addEventListener("click", () => { void retryPendingSave(); });
  elements.reapply.addEventListener("click", reapplyConflict);
  elements.noteInput.addEventListener("input", () => {
    if (state.editing) state.draftVersion += 1;
  });
  window.addEventListener("fieldnotes:update", handleUpdate);
  document.addEventListener("visibilitychange", handleVisibilityChange);

  void loadList();
})();
