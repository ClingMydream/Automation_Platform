// File purpose: Test object feature helpers. Keep payload shaping and backend calls out of the page component.
// How to change: edit UI text/layout in TestObjectPanel.jsx; edit backend call details in this file.

// Test object type options are shared by the form filter, create form, and table renderer.
export const TEST_OBJECT_TYPES = [
  { value: 'api', label: '接口' },
  { value: 'page', label: '页面' },
  { value: 'app', label: 'App' },
  { value: 'mini_program', label: '小程序' },
  { value: 'script', label: '自动化脚本' },
  { value: 'performance', label: '性能场景' },
  { value: 'device', label: '设备' },
  { value: 'environment', label: '环境' },
];

// Feature block: exported helpers below are used by the page component and can be tested independently.
export function testObjectTypeLabel(type) {
  return TEST_OBJECT_TYPES.find((item) => item.value === type)?.label || type;
}

// Convert table row data into form values when the user clicks edit.
export function buildTestObjectFormValues(item) {
  return {
    code: item.code,
    name: item.name,
    object_type: item.object_type,
    project_id: item.project_id || undefined,
    business_module: item.business_module || '',
    tags: item.tags || [],
    is_active: item.is_active,
    description: item.description || '',
  };
}

// Normalize user input before sending it to the backend.
export function buildTestObjectPayload(values) {
  return {
    code: values.code?.trim(),
    name: values.name?.trim(),
    object_type: values.object_type,
    project_id: values.project_id || null,
    business_module: values.business_module?.trim() || null,
    tags: values.tags || [],
    is_active: values.is_active ?? true,
    description: values.description?.trim() || null,
  };
}

// API operation block: async helpers below call the backend and return normalized results.
export async function saveTestObject(client, editingId, values) {
  const payload = buildTestObjectPayload(values);
  if (editingId) {
    await client.put(`/v1/test-objects/${editingId}`, payload);
    return 'updated';
  }
  await client.post('/v1/test-objects', payload);
  return 'created';
}

// Delete one test object record without touching legacy cases or runs.
export async function deleteTestObject(client, objectId) {
  await client.delete(`/v1/test-objects/${objectId}`);
}
