// Visual groups preserve each feature's original permission and URL.
export const NAVIGATION_GROUPS = [
  { keys: ['online_preview', 'jenkins', 'test_packages'], label: 'Emote 测试环境' },
  { keys: ['json_tools', 'codec'], label: '文本工具' },
];
export function authorizedKeys(user, items) {
  if (!user) return new Set();
  return new Set(['home', ...items.filter(item => (!item.adminOnly || user.is_admin) &&
    (user.is_admin || ['personal_tasks','knowledge','learning_route'].includes(item.key) || user.menu_permissions?.includes(item.key))).map(item=>item.key)]);
}
export function collapseNavigation(sections) {
  return sections.map(section => {
    const children = [];
    for (const item of section.children) {
      const group = NAVIGATION_GROUPS.find(group=>group.keys.includes(item.key));
      if (!group) { children.push(item); continue; }
      if (children.some(child=>group.keys.includes(child.key))) continue;
      const preferred = group.keys.map(key=>section.children.find(child=>child.key===key)).find(Boolean);
      children.push({...preferred, label:group.label});
    }
    return {...section,children};
  });
}
export function groupKey(key, items) {
  const group = NAVIGATION_GROUPS.find(group=>group.keys.includes(key));
  return group ? items.find(item=>group.keys.includes(item.key))?.key || key : key;
}
