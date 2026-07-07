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
