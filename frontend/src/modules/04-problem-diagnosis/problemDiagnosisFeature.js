// File purpose: Small helpers for the problem diagnosis page.
// How to change: update labels or defaults here before changing the visual component.

// Status labels are kept in one place so tables and forms stay consistent.
export const findingStatusOptions = [
  { value: 'open', label: '待定位' },
  { value: 'investigating', label: '定位中' },
  { value: 'fixed', label: '已修复' },
  { value: 'ignored', label: '忽略' },
];

// Severity labels are kept in one place so risk colors can be reused.
export const severityOptions = [
  { value: 'low', label: '低' },
  { value: 'medium', label: '中' },
  { value: 'high', label: '高' },
  { value: 'critical', label: '严重' },
];

// Pick a visual color for the diagnosis status tag.
export function statusColor(status) {
  if (status === 'fixed') return 'green';
  if (status === 'investigating') return 'blue';
  if (status === 'ignored') return 'default';
  return 'orange';
}

// Pick a visual color for the severity tag.
export function severityColor(severity) {
  if (severity === 'critical') return 'red';
  if (severity === 'high') return 'volcano';
  if (severity === 'medium') return 'gold';
  return 'green';
}

// Build the form payload accepted by the backend API.
export function toFindingPayload(values) {
  return {
    result_id: values.result_id || null,
    batch_id: values.batch_id || null,
    test_object_id: values.test_object_id || null,
    title: values.title,
    severity: values.severity || 'medium',
    status: values.status || 'open',
    failure_category: values.failure_category || null,
    root_cause: values.root_cause || null,
    reproduce_steps: values.reproduce_steps || null,
    evidence: values.evidence || {},
    owner: values.owner || null,
    suggestion: values.suggestion || null,
    source: values.source || 'manual',
  };
}
