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
