// File purpose: Integration feature helpers. Keep webhook payload and API calls out of UI.

export const WEBHOOK_EVENT_OPTIONS = [
  { value: 'batch_finished', label: '批次完成' },
  { value: 'task_failed', label: '任务失败' },
  { value: 'quality_risk', label: '质量风险' },
];

export function buildWebhookFormValues(item) {
  return {
    name: item.name,
    integration_type: item.integration_type || 'webhook',
    webhook_url: item.webhook_url,
    events: item.events || [],
    secret_name: item.secret_name || '',
    is_active: item.is_active,
    description: item.description || '',
  };
}

export function buildWebhookPayload(values) {
  return {
    name: values.name?.trim(),
    integration_type: values.integration_type?.trim() || 'webhook',
    webhook_url: values.webhook_url?.trim(),
    events: values.events || [],
    secret_name: values.secret_name?.trim() || null,
    is_active: values.is_active ?? true,
    description: values.description?.trim() || null,
  };
}

export async function saveWebhook(client, editingId, values) {
  const payload = buildWebhookPayload(values);
  if (editingId) {
    await client.put(`/v1/integrations/webhooks/${editingId}`, payload);
    return 'updated';
  }
  await client.post('/v1/integrations/webhooks', payload);
  return 'created';
}

export async function deleteWebhook(client, webhookId) {
  await client.delete(`/v1/integrations/webhooks/${webhookId}`);
}

export async function testWebhook(client, webhookId) {
  return client.post(`/v1/integrations/webhooks/${webhookId}/test`, {});
}
