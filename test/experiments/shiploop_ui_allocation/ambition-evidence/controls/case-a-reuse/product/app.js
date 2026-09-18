(() => {
  "use strict";

  const state = {
    account: "alpha",
    notes: [],
    record: null,
    selectedId: null,
    editing: false,
    requestGeneration: 0,
    listController: null,
    detailController: null,
    saveController: null,
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
    saveStatus: document.querySelector("#save-status"),
  };

  function noteUrl(account, id) {
    return `/api/accounts/${encodeURIComponent(account)}/notes/${encodeURIComponent(id)}`;
  }

  function operationId() {
    if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function") {
      return globalThis.crypto.randomUUID();
    }

    return `field-note-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function setMessage(element, message, tone = "normal") {
    element.textContent = message;
    if (tone === "error") {
      element.dataset.tone = "error";
    } else {
      delete element.dataset.tone;
    }
  }

  function setSaving(isSaving) {
    elements.save.disabled = isSaving;
    elements.cancel.disabled = isSaving;
    elements.back.disabled = isSaving;
    elements.edit.disabled = isSaving;
  }

  function setEditing(editing) {
    state.editing = editing;
    elements.noteInput.readOnly = !editing;
    elements.noteInput.setAttribute("aria-readonly", String(!editing));
    elements.edit.hidden = editing;
    elements.cancel.hidden = !editing;
    elements.save.hidden = !editing;
  }

  function showList() {
    state.selectedId = null;
    state.record = null;
    setEditing(false);
    elements.detail.hidden = true;
    elements.notesView.hidden = false;
    setMessage(elements.saveStatus, "");
  }

  function showDetail() {
    elements.notesView.hidden = true;
    elements.detail.hidden = false;
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

  function renderRecord() {
    const record = state.record;
    if (!record) {
      return;
    }

    elements.noteTitle.textContent = record.title;
    elements.confirmedNote.textContent = record.note;
    elements.revision.textContent = String(record.revision);
    elements.noteInput.value = record.note;
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
    state.listController = controller;
    const generation = ++state.requestGeneration;

    setMessage(elements.listMessage, "Loading notes…");
    elements.noteList.replaceChildren();

    try {
      const response = await fetch(
        `/api/accounts/${encodeURIComponent(state.account)}/notes`,
        { signal: controller.signal, headers: { Accept: "application/json" } },
      );
      const notes = await responseJson(response);
      if (controller.signal.aborted || generation !== state.requestGeneration) {
        return;
      }

      state.notes = Array.isArray(notes) ? notes : [];
      renderList();
      setMessage(
        elements.listMessage,
        state.notes.length === 0 ? "No notes are available for this account." : "",
      );
    } catch (error) {
      if (controller.signal.aborted) {
        return;
      }
      setMessage(elements.listMessage, "Notes could not be loaded. Choose the account again to try again.", "error");
    }
  }

  async function openNote(noteId) {
    state.detailController?.abort();
    const controller = new AbortController();
    state.detailController = controller;
    const account = state.account;
    const generation = ++state.requestGeneration;

    showDetail();
    setEditing(false);
    elements.noteTitle.textContent = "Loading note";
    elements.confirmedNote.textContent = "";
    elements.revision.textContent = "—";
    elements.noteInput.value = "";
    setMessage(elements.saveStatus, "Loading note…");

    try {
      const response = await fetch(noteUrl(account, noteId), {
        signal: controller.signal,
        headers: { Accept: "application/json" },
      });
      const record = await responseJson(response);
      if (controller.signal.aborted || generation !== state.requestGeneration || account !== state.account) {
        return;
      }

      state.selectedId = noteId;
      state.record = record;
      renderRecord();
      setMessage(elements.saveStatus, "");
    } catch (error) {
      if (controller.signal.aborted) {
        return;
      }
      setMessage(elements.saveStatus, "This note could not be loaded. Return to notes and try again.", "error");
    }
  }

  function beginEditing() {
    if (!state.record) {
      return;
    }
    setMessage(elements.saveStatus, "");
    setEditing(true);
    elements.noteInput.focus();
    elements.noteInput.setSelectionRange(elements.noteInput.value.length, elements.noteInput.value.length);
  }

  function cancelEditing() {
    if (!state.record) {
      return;
    }
    elements.noteInput.value = state.record.note;
    setEditing(false);
    setMessage(elements.saveStatus, "Changes discarded.");
    elements.edit.focus();
  }

  async function saveEditing() {
    if (!state.record || !state.selectedId || !state.editing) {
      return;
    }

    const recordAtSave = state.record;
    const accountAtSave = state.account;
    const noteIdAtSave = state.selectedId;
    const draft = elements.noteInput.value;
    const requestId = operationId();
    const controller = new AbortController();
    state.saveController?.abort();
    state.saveController = controller;

    setSaving(true);
    setMessage(elements.saveStatus, "Saving changes…");

    try {
      const response = await fetch(noteUrl(accountAtSave, noteIdAtSave), {
        method: "POST",
        signal: controller.signal,
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          note: draft,
          baseRevision: recordAtSave.revision,
          operationId: requestId,
        }),
      });
      const payload = await responseJson(response);
      const saved = payload && payload.record;

      if (!saved || controller.signal.aborted || accountAtSave !== state.account || noteIdAtSave !== state.selectedId) {
        return;
      }

      state.record = saved;
      renderRecord();
      setEditing(false);
      setMessage(elements.saveStatus, "Changes saved.");
      await loadList();
    } catch (error) {
      if (!controller.signal.aborted && accountAtSave === state.account && noteIdAtSave === state.selectedId) {
        setMessage(elements.saveStatus, "Changes could not be saved. Your working text is still here.", "error");
      }
    } finally {
      if (state.saveController === controller) {
        state.saveController = null;
        setSaving(false);
      }
    }
  }

  function switchAccount() {
    state.account = elements.account.value;
    state.detailController?.abort();
    state.saveController?.abort();
    showList();
    loadList();
  }

  elements.account.addEventListener("change", switchAccount);
  elements.noteList.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-note-id]");
    if (button) {
      openNote(button.dataset.noteId);
    }
  });
  elements.back.addEventListener("click", () => {
    state.detailController?.abort();
    showList();
    elements.noteList.querySelector("button")?.focus();
  });
  elements.edit.addEventListener("click", beginEditing);
  elements.cancel.addEventListener("click", cancelEditing);
  elements.save.addEventListener("click", saveEditing);

  loadList();
})();
