// File purpose: User management feature helpers. Load data and shape user create/update payloads.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

// User management feature functions.
// Keep user loading, payload shaping, and delete calls separate from the table/form UI.

// Load users and assignable menu options together.
// API operation block: async helpers below call the backend and return normalized results.
export async function fetchUserManagementData(client) {
  const [users, menus] = await Promise.all([
    client.get('/users'),
    client.get('/menu-options'),
  ]);
  return {
    users,
    menuOptions: menus.map((item) => ({ label: item.label, value: item.key })),
  };
}

// Convert a user record into form values for editing.
// Feature block: exported helpers below are used by the page component and can be tested independently.
export function buildUserFormValues(user, menuOptions) {
  return {
    username: user.username,
    display_name: user.display_name || '',
    password: '',
    is_active: user.is_active,
    menu_permissions: user.is_admin ? menuOptions.map((item) => item.value) : user.menu_permissions || [],
  };
}

// Convert user form values into create or update payloads.
export function buildUserPayload(values, editingId) {
  const payload = {
    display_name: values.display_name || null,
    is_active: values.is_active !== false,
    menu_permissions: values.menu_permissions || [],
  };
  if (values.password) payload.password = values.password;
  if (!editingId) {
    payload.username = values.username;
    payload.password = values.password;
  }
  return payload;
}

// Create or update a user depending on edit state.
export async function saveUser(client, editingId, values) {
  const payload = buildUserPayload(values, editingId);
  if (editingId) {
    await client.put(`/users/${editingId}`, payload);
    return 'updated';
  }
  await client.post('/users', payload);
  return 'created';
}

// Delete one non-admin user.
export async function deleteUser(client, userId) {
  await client.delete(`/users/${userId}`);
}
