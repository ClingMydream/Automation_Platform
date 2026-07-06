// File purpose: Project feature helpers. Keep project payload and API operations separate from UI.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

// Project feature functions.
// The UI owns the form layout; this file owns backend calls and form value mapping.

// Convert a project record into form values for editing.
// Feature block: exported helpers below are used by the page component and can be tested independently.
export function buildProjectFormValues(project) {
  return {
    name: project.name,
    description: project.description || '',
  };
}

// Convert an environment record into form values for editing.
export function buildEnvironmentFormValues(environment) {
  return {
    project_id: environment.project_id,
    name: environment.name,
    base_url: environment.base_url,
    variablesText: JSON.stringify(environment.variables || {}, null, 2),
  };
}

// Parse the environment variables textarea and require a JSON object.
export function parseEnvironmentVariables(text) {
  const trimmed = (text || '').trim();
  if (!trimmed) return {};
  const parsed = JSON.parse(trimmed);
  if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
    throw new Error('环境变量必须是 JSON 对象，例如 {"token":"xxx"}');
  }
  return parsed;
}

// Create or update a project depending on edit state.
// API operation block: async helpers below call the backend and return normalized results.
export async function saveProject(client, editingId, values) {
  if (editingId) {
    await client.put(`/projects/${editingId}`, values);
    return 'updated';
  }
  await client.post('/projects', values);
  return 'created';
}

// Delete one project and related backend data.
export async function deleteProject(client, projectId) {
  await client.delete(`/projects/${projectId}`);
}

// Create or update an environment config depending on edit state.
export async function saveEnvironment(client, editingId, values) {
  const payload = {
    project_id: values.project_id,
    name: values.name,
    base_url: values.base_url,
    variables: parseEnvironmentVariables(values.variablesText),
  };
  if (editingId) {
    await client.put(`/environments/${editingId}`, payload);
    return 'updated';
  }
  await client.post('/environments', payload);
  return 'created';
}

// Delete one unused environment config.
export async function deleteEnvironment(client, environmentId) {
  await client.delete(`/environments/${environmentId}`);
}

// Trigger a safe backend health check for one environment base URL.
export async function checkEnvironmentHealth(client, environmentId) {
  return client.post(`/v1/environments/${environmentId}/health-check`, {});
}
