// UI test feature functions.
// UI pages should describe the workflow; parsing, saving, deleting, and run creation live here.

export function buildUiCasePayload(values) {
  return {
    project_id: Number(values.project_id),
    name: values.name,
    steps: JSON.parse(values.steps),
  };
}

export function buildUiCaseFormValues(item) {
  return {
    project_id: item.project_id,
    name: item.name,
    steps: JSON.stringify(item.steps || [], null, 2),
  };
}

export async function saveUiCase(client, editingId, values) {
  const payload = buildUiCasePayload(values);
  if (editingId) {
    await client.put(`/ui-cases/${editingId}`, payload);
    return 'updated';
  }
  await client.post('/ui-cases', payload);
  return 'created';
}

export async function deleteUiCase(client, caseId) {
  await client.delete(`/ui-cases/${caseId}`);
}

export async function createUiCaseRun(client, caseId) {
  return client.post('/runs', { case_type: 'ui', case_id: caseId });
}

export function openLiveRunWindow() {
  const detailWindow = window.open('', `ui-run-${Date.now()}`, 'width=1200,height=860');
  if (detailWindow) {
    detailWindow.document.write('<!doctype html><title>UI 自动化执行窗口</title><body style="font-family:system-ui;padding:24px;background:#101820;color:#fff;">正在启动 UI 自动化执行窗口，请稍候...</body>');
  }
  return detailWindow;
}

export function navigateLiveRunWindow(detailWindow, runId) {
  if (!detailWindow) return;
  detailWindow.location.href = `${window.location.origin}${window.location.pathname}?liveRunId=${runId}`;
}
