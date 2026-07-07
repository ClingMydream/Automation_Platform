// File purpose: Result center helpers. Keep result-center API calls and table utilities out of the page component.

// Trigger a retry batch that only reruns failed API cases from a previous execution batch.
export async function retryFailedBatch(client, batchId) {
  return client.post(`/v1/execution-batches/${batchId}/retry`, {
    trigger_type: 'manual',
    summary: { source: 'result_center_retry' },
  });
}

// Decide whether the retry action should be visible for a batch row.
export function canRetryBatch(batch) {
  return Boolean(batch?.task_id && batch?.failed_count > 0);
}

// Format normalized performance metrics for compact result-center cards and tables.
export function formatPerformanceMetric(value, unit = '') {
  if (value === null || value === undefined || value === '') return '-';
  const numberValue = Number(value);
  if (Number.isNaN(numberValue)) return String(value);
  const digits = Number.isInteger(numberValue) ? 0 : 2;
  return `${numberValue.toFixed(digits)}${unit}`;
}

// Map performance risk into Ant Design tag colors.
export function performanceRiskColor(risk) {
  return {
    low: 'success',
    medium: 'warning',
    high: 'error',
  }[risk] || 'default';
}

// Attachment types used by result evidence uploads.
export const attachmentTypeOptions = [
  { value: 'log', label: '日志' },
  { value: 'screenshot', label: '截图' },
  { value: 'recording', label: '录屏' },
  { value: 'har', label: 'HAR' },
  { value: 'performance_report', label: '性能报告' },
  { value: 'other', label: '其他' },
];

// Load files attached to one result row.
export async function listResultAttachments(client, resultId) {
  if (!resultId) return [];
  return client.get(`/v1/attachments?result_id=${resultId}`);
}

// Upload one evidence file and bind it to the selected result row.
export async function uploadResultAttachment(client, resultId, attachmentType, file) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('result_id', resultId);
  formData.append('attachment_type', attachmentType);
  return client.post('/v1/attachments', formData);
}

// Download an attachment with the logged-in token and trigger a browser save.
export async function downloadAttachment(client, attachment) {
  const { blob, filename } = await client.download(`/v1/attachments/${attachment.id}/download`);
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename || attachment.original_name || 'attachment';
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}
