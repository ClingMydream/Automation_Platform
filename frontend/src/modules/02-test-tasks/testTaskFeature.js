// File purpose: Test task feature helpers. Keep API calls and payload shaping out of the page component.

export const TASK_TYPES = [
  { value: 'api', label: '接口' },
  { value: 'ui', label: 'UI' },
  { value: 'performance', label: '性能' },
  { value: 'compatibility', label: '兼容性' },
  { value: 'script', label: '脚本' },
  { value: 'mixed', label: '混合' },
];

export const TRIGGER_TYPES = [
  { value: 'manual', label: '手动' },
  { value: 'schedule', label: '定时' },
  { value: 'ci', label: 'CI' },
  { value: 'api', label: 'API' },
];

export function taskTypeLabel(value) {
  return TASK_TYPES.find((item) => item.value === value)?.label || value;
}

export function buildTaskFormValues(item) {
  return {
    code: item.code,
    name: item.name,
    task_type: item.task_type,
    project_id: item.project_id || undefined,
    environment_id: item.environment_id || undefined,
    test_object_id: item.test_object_id || undefined,
    trigger_type: item.trigger_type || 'manual',
    runner_type: item.runner_type || 'platform',
    retry_count: item.retry_count || 0,
    schedule_cron: item.schedule_cron || '',
    owner: item.owner || '',
    is_active: item.is_active,
    configText: JSON.stringify(item.config || {}, null, 2),
    description: item.description || '',
  };
}

export function buildTaskPayload(values) {
  return {
    code: values.code?.trim(),
    name: values.name?.trim(),
    task_type: values.task_type,
    project_id: values.project_id || null,
    environment_id: values.environment_id || null,
    test_object_id: values.test_object_id || null,
    trigger_type: values.trigger_type || 'manual',
    runner_type: values.runner_type?.trim() || 'platform',
    retry_count: Number(values.retry_count || 0),
    schedule_cron: values.schedule_cron?.trim() || null,
    owner: values.owner?.trim() || null,
    is_active: values.is_active ?? true,
    config: values.configText ? JSON.parse(values.configText) : {},
    description: values.description?.trim() || null,
  };
}

export async function saveTask(client, editingId, values) {
  const payload = buildTaskPayload(values);
  if (editingId) {
    await client.put(`/v1/test-tasks/${editingId}`, payload);
    return 'updated';
  }
  await client.post('/v1/test-tasks', payload);
  return 'created';
}

export async function deleteTask(client, taskId) {
  await client.delete(`/v1/test-tasks/${taskId}`);
}

export async function runTask(client, taskId) {
  return client.post(`/v1/test-tasks/${taskId}/run`, { trigger_type: 'manual', summary: { source: 'web' } });
}
