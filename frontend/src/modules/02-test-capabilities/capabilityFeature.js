// File purpose: Test capability feature helpers. Keep API calls and JSON parsing out of the page component.

export const CAPABILITY_TABS = [
  { key: 'apiScenarios', label: 'API 场景' },
  { key: 'mockRules', label: 'Mock' },
  { key: 'performanceScenarios', label: '性能场景' },
  { key: 'runners', label: 'Runner' },
];

// Build the public mock response URL from the current browser origin and rule path.
export function publicMockUrl(rule) {
  const rawPath = rule?.path || '';
  const normalizedPath = rawPath.startsWith('/') ? rawPath : `/${rawPath}`;
  return `${window.location.origin}/api/mock${normalizedPath}`;
}

export async function loadCapabilities(client) {
  const [apiScenarios, mockRules, performanceScenarios, runners] = await Promise.all([
    client.get('/v1/api-scenarios'),
    client.get('/v1/mock-rules'),
    client.get('/v1/performance-scenarios'),
    client.get('/v1/runners'),
  ]);
  return { apiScenarios, mockRules, performanceScenarios, runners };
}

function parseJson(text, fallback) {
  if (!text || !text.trim()) return fallback;
  return JSON.parse(text);
}

export function payloadFor(type, values) {
  if (type === 'apiScenarios') {
    return {
      code: values.code?.trim(),
      name: values.name?.trim(),
      project_id: values.project_id || null,
      environment_id: values.environment_id || null,
      variables: parseJson(values.variablesText, {}),
      api_case_ids: parseJson(values.apiCaseIdsText, []),
      assertions: parseJson(values.assertionsText, []),
      pre_script: values.pre_script || null,
      post_script: values.post_script || null,
      is_active: values.is_active ?? true,
      description: values.description || null,
    };
  }
  if (type === 'mockRules') {
    return {
      name: values.name?.trim(),
      project_id: values.project_id || null,
      method: values.method || 'GET',
      path: values.path?.trim(),
      status_code: Number(values.status_code || 200),
      response_headers: parseJson(values.responseHeadersText, {}),
      response_body: values.response_body || '',
      delay_ms: Number(values.delay_ms || 0),
      is_active: values.is_active ?? true,
      description: values.description || null,
    };
  }
  if (type === 'performanceScenarios') {
    return {
      code: values.code?.trim(),
      name: values.name?.trim(),
      project_id: values.project_id || null,
      target_url: values.target_url?.trim(),
      method: values.method || 'GET',
      headers: parseJson(values.headersText, {}),
      body: values.body || null,
      concurrency: Number(values.concurrency || 10),
      duration_seconds: Number(values.duration_seconds || 60),
      ramp_up_seconds: Number(values.ramp_up_seconds || 10),
      threshold_p95_ms: values.threshold_p95_ms ? Number(values.threshold_p95_ms) : null,
      threshold_error_rate: values.threshold_error_rate ? Number(values.threshold_error_rate) : null,
      tags: values.tags || [],
      is_active: values.is_active ?? true,
      description: values.description || null,
    };
  }
  return {
    code: values.code?.trim(),
    name: values.name?.trim(),
    runner_type: values.runner_type || 'platform',
    status: values.status || 'offline',
    base_url: values.base_url || null,
    capabilities: values.capabilities || [],
    is_active: values.is_active ?? true,
    description: values.description || null,
  };
}

export function formValuesFor(type, item) {
  if (type === 'apiScenarios') {
    return {
      ...item,
      variablesText: JSON.stringify(item.variables || {}, null, 2),
      apiCaseIdsText: JSON.stringify(item.api_case_ids || [], null, 2),
      assertionsText: JSON.stringify(item.assertions || [], null, 2),
    };
  }
  if (type === 'mockRules') {
    return {
      ...item,
      responseHeadersText: JSON.stringify(item.response_headers || {}, null, 2),
    };
  }
  if (type === 'performanceScenarios') {
    return {
      ...item,
      headersText: JSON.stringify(item.headers || {}, null, 2),
    };
  }
  return item;
}

const endpoints = {
  apiScenarios: '/v1/api-scenarios',
  mockRules: '/v1/mock-rules',
  performanceScenarios: '/v1/performance-scenarios',
  runners: '/v1/runners',
};

export async function saveCapability(client, type, editingId, values) {
  const payload = payloadFor(type, values);
  const base = endpoints[type];
  if (editingId) {
    await client.put(`${base}/${editingId}`, payload);
    return 'updated';
  }
  await client.post(base, payload);
  return 'created';
}

export async function deleteCapability(client, type, id) {
  await client.delete(`${endpoints[type]}/${id}`);
}

export async function runnerHeartbeat(client, id) {
  return client.post(`/v1/runners/${id}/heartbeat`, {});
}
