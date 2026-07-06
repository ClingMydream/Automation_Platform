// File purpose: Test dataset feature helpers. Keep payload shaping and API calls separate from UI.

export const DATASET_TYPES = [
  { value: 'variables', label: '变量集' },
  { value: 'accounts', label: '测试账号' },
  { value: 'data_pool', label: '数据池' },
];

export function buildDatasetFormValues(item) {
  return {
    name: item.name,
    project_id: item.project_id || undefined,
    dataset_type: item.dataset_type || 'variables',
    variablesText: JSON.stringify(item.variables || {}, null, 2),
    rowsText: JSON.stringify(item.rows || [], null, 2),
    is_active: item.is_active,
    description: item.description || '',
  };
}

export function buildDatasetPayload(values) {
  return {
    name: values.name?.trim(),
    project_id: values.project_id || null,
    dataset_type: values.dataset_type || 'variables',
    variables: values.variablesText ? JSON.parse(values.variablesText) : {},
    rows: values.rowsText ? JSON.parse(values.rowsText) : [],
    is_active: values.is_active ?? true,
    description: values.description?.trim() || null,
  };
}

export async function saveDataset(client, editingId, values) {
  const payload = buildDatasetPayload(values);
  if (editingId) {
    await client.put(`/v1/test-datasets/${editingId}`, payload);
    return 'updated';
  }
  await client.post('/v1/test-datasets', payload);
  return 'created';
}

export async function deleteDataset(client, datasetId) {
  await client.delete(`/v1/test-datasets/${datasetId}`);
}
