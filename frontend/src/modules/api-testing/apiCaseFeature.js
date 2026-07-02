// Interface test feature functions.
// Keep request payload shaping and backend calls here so the UI stays easy to edit.

// Convert API case form values into the backend request payload.
export function buildApiCasePayload(values) {
  return {
    ...values,
    project_id: Number(values.project_id),
    headers: JSON.parse(values.headers || '{}'),
    assert_status: Number(values.assert_status) || null,
    body: values.body || null,
    assert_text: values.assert_text || null,
    assert_json_path: values.assert_json_path || null,
    assert_json_value: values.assert_json_value || null,
  };
}

// Convert an API case record into form values for editing.
export function buildApiCaseFormValues(item) {
  return {
    project_id: item.project_id,
    name: item.name,
    method: item.method,
    url: item.url,
    headers: JSON.stringify(item.headers || {}, null, 2),
    body: item.body || '',
    assert_status: item.assert_status || '',
    assert_text: item.assert_text || '',
    assert_json_path: item.assert_json_path || '',
    assert_json_value: item.assert_json_value || '',
  };
}

// Create or update an API test case depending on edit state.
export async function saveApiCase(client, editingId, values) {
  const payload = buildApiCasePayload(values);
  if (editingId) {
    await client.put(`/api-cases/${editingId}`, payload);
    return 'updated';
  }
  await client.post('/api-cases', payload);
  return 'created';
}

// Delete one API test case.
export async function deleteApiCase(client, caseId) {
  await client.delete(`/api-cases/${caseId}`);
}

// Create an execution run for one API test case.
export async function createApiCaseRun(client, caseId) {
  return client.post('/runs', { case_type: 'api', case_id: caseId });
}
