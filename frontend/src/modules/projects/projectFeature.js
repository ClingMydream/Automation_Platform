// Project feature functions.
// The UI owns the form layout; this file owns backend calls and form value mapping.

// Convert a project record into form values for editing.
export function buildProjectFormValues(project) {
  return {
    name: project.name,
    description: project.description || '',
  };
}

// Create or update a project depending on edit state.
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
