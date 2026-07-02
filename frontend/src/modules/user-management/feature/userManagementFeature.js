// User management feature functions.
// Keep user loading, payload shaping, and delete calls separate from the table/form UI.

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

export function buildUserFormValues(user, menuOptions) {
  return {
    username: user.username,
    display_name: user.display_name || '',
    password: '',
    is_active: user.is_active,
    menu_permissions: user.is_admin ? menuOptions.map((item) => item.value) : user.menu_permissions || [],
  };
}

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

export async function saveUser(client, editingId, values) {
  const payload = buildUserPayload(values, editingId);
  if (editingId) {
    await client.put(`/users/${editingId}`, payload);
    return 'updated';
  }
  await client.post('/users', payload);
  return 'created';
}

export async function deleteUser(client, userId) {
  await client.delete(`/users/${userId}`);
}
