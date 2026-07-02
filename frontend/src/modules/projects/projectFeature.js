// Project feature functions.
// The UI owns the form layout; this file owns backend calls and form value mapping.

export function buildProjectFormValues(project) {
  return {
    name: project.name,
    description: project.description || '',
  };
}

export async function saveProject(client, editingId, values) {
  if (editingId) {
    await client.put(`/projects/${editingId}`, values);
    return 'updated';
  }
  await client.post('/projects', values);
  return 'created';
}

export async function deleteProject(client, projectId) {
  await client.delete(`/projects/${projectId}`);
}
