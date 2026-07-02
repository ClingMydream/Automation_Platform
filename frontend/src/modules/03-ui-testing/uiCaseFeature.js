// File purpose: UI testing feature helpers. Keep payload shaping, backend calls, and live-window logic out of UI.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

// UI test feature functions.
// UI pages should describe the workflow; parsing, saving, deleting, and run creation live here.

// Convert UI case form values into the backend request payload.
// Feature block: exported helpers below are used by the page component and can be tested independently.
export function buildUiCasePayload(values) {
  return {
    project_id: Number(values.project_id),
    name: values.name,
    steps: JSON.parse(values.steps),
  };
}

// Convert a UI case record into form values for editing.
export function buildUiCaseFormValues(item) {
  return {
    project_id: item.project_id,
    name: item.name,
    steps: JSON.stringify(item.steps || [], null, 2),
  };
}

// Create or update a UI test case depending on edit state.
// API operation block: async helpers below call the backend and return normalized results.
export async function saveUiCase(client, editingId, values) {
  const payload = buildUiCasePayload(values);
  if (editingId) {
    await client.put(`/ui-cases/${editingId}`, payload);
    return 'updated';
  }
  await client.post('/ui-cases', payload);
  return 'created';
}

// Delete one UI test case.
export async function deleteUiCase(client, caseId) {
  await client.delete(`/ui-cases/${caseId}`);
}

// Create an execution run for one UI test case.
export async function createUiCaseRun(client, caseId) {
  return client.post('/runs', { case_type: 'ui', case_id: caseId });
}

// Open a live UI automation window with a startup placeholder.
export function openLiveRunWindow() {
  const detailWindow = window.open('', `ui-run-${Date.now()}`, 'width=1200,height=860');
  if (detailWindow) {
    detailWindow.document.write('<!doctype html><title>UI 自动化执行窗口</title><body style="font-family:system-ui;padding:24px;background:#101820;color:#fff;">正在启动 UI 自动化执行窗口，请稍候...</body>');
  }
  return detailWindow;
}

// Navigate the live run window to a specific run ID.
export function navigateLiveRunWindow(detailWindow, runId) {
  if (!detailWindow) return;
  detailWindow.location.href = `${window.location.origin}${window.location.pathname}?liveRunId=${runId}`;
}
