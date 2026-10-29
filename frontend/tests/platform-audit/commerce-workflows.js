async page => {
  const results = [], layouts = [], errors = [], base = new URL(page.url()).origin;
  page.on('pageerror', e => errors.push(e.message));
  page.setDefaultTimeout(15000);
  const platformToken = await page.evaluate(() => sessionStorage.getItem('token') || localStorage.getItem('token'));
  const name = 'commerce-audit-' + Date.now(), password = 'Local-audit-' + Date.now();
  const user = await page.request.post(base + '/api/users', { headers: { Authorization: 'Bearer ' + platformToken }, data: { username: name, password, display_name: '商城隔离验收', menu_permissions: ['practice_lab'] } });
  if (!user.ok()) throw Error('Cannot prepare isolated user: ' + user.status());
  const login = await page.request.post(base + '/api/auth/login', { data: { username: name, password } });
  if (!login.ok()) throw Error('Platform test login failed');
  const qaToken = (await login.json()).access_token;
  await page.evaluate(token => { sessionStorage.setItem('token', token); sessionStorage.removeItem('cling:practice:session'); }, qaToken);
  await page.goto(base + '/practice-app');
  await page.getByRole('textbox', { name: '练习密码', exact: true }).fill('wrong-password');
  await page.getByRole('button', { name: '登录练习系统', exact: true }).click();
  await page.getByText('练习账号或密码错误', { exact: true }).waitFor();
  if (!await page.evaluate(() => !!sessionStorage.getItem('token'))) throw Error('Demo login expired platform session');
  results.push('错误练习密码保留平台登录');
  async function role(username) {
    if (await page.getByRole('button', { name: '退出练习账号', exact: true }).count()) await page.getByRole('button', { name: '退出练习账号', exact: true }).click();
    await page.getByRole('textbox', { name: '练习用户名', exact: true }).fill(username);
    await page.getByRole('textbox', { name: '练习密码', exact: true }).fill('Practice123!');
    await page.getByRole('button', { name: '登录练习系统', exact: true }).click();
    await page.getByRole('navigation', { name: '练习项目导航' }).waitFor();
    await page.locator('.commerce-page-stack').waitFor();
  }
  async function layout(roleName, route) {
    for (const width of [1440, 1280, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 960 });
      await page.waitForTimeout(60);
      const size = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }));
      layouts.push({ role: roleName, route, ...size });
      if (size.document > width + 2) throw Error(`Overflow: ${roleName}/${route}/${width}: ${size.document}`);
    }
    await page.setViewportSize({ width: 1440, height: 1000 });
  }
  await layout('login', 'login');
  await role('learner');
  await page.screenshot({ path: 'output/commerce-v2-20261029/shop-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: 'output/commerce-v2-20261029/shop-mobile.png', fullPage: true });
  await page.setViewportSize({ width: 1440, height: 1000 });
  const search = page.getByLabel('搜索商城商品', { exact: true });
  await search.fill('NOTE-001'); await search.press('Enter');
  const card = page.getByTestId('product-NOTE-001');
  await card.getByRole('button', { name: '查看商品：练习手账本', exact: true }).click();
  await page.getByRole('spinbutton', { name: '商品详情购买数量', exact: true }).fill('2');
  await page.getByRole('dialog').getByRole('button', { name: '加入购物车', exact: true }).click();
  await page.getByText('已加入购物车', { exact: true }).waitFor();
  await page.getByRole('button', { name: '购物车', exact: true }).click();
  await page.getByRole('spinbutton', { name: '购物车数量：NOTE-001', exact: true }).fill('3');
  if (!await page.getByRole('button', { name: '去结算', exact: true }).isDisabled()) throw Error('Unsaved quantity checkout enabled');
  await page.getByRole('button', { name: '更新数量', exact: true }).click();
  await page.getByText('购物车已更新', { exact: true }).waitFor();
  results.push('详情加购、数量暂存与更新');
  await page.getByRole('button', { name: '地址管理', exact: true }).click();
  await page.getByRole('button', { name: '新增地址', exact: true }).click();
  await page.getByRole('textbox', { name: '收件人', exact: true }).fill('浏览器验收');
  await page.getByRole('textbox', { name: '联系电话', exact: true }).fill('123');
  await page.getByRole('button', { name: '保存地址', exact: true }).click();
  await page.getByText('请输入11位手机号格式', { exact: true }).waitFor();
  await page.getByRole('textbox', { name: '联系电话', exact: true }).fill('19900000000');
  await page.getByRole('textbox', { name: '所在地区', exact: true }).fill('测试省 / 测试市');
  await page.getByRole('textbox', { name: '详细地址', exact: true }).fill('浏览器自动化练习路2号');
  await page.getByRole('checkbox', { name: '设为默认地址', exact: true }).check();
  await page.getByRole('button', { name: '保存地址', exact: true }).click();
  await page.getByText('地址已保存', { exact: true }).waitFor();
  results.push('地址校验、新增与默认切换');
  await page.getByRole('button', { name: '购物车', exact: true }).click();
  await page.getByRole('button', { name: '去结算', exact: true }).click();
  await page.getByRole('checkbox', { name: '已确认商品和收货信息', exact: true }).check();
  await page.getByRole('button', { name: '提交订单', exact: true }).click();
  await page.getByRole('button', { name: '模拟付款', exact: true }).waitFor();
  const orderRoute = page.url().split('#')[1];
  await layout('learner', orderRoute);
  await page.getByRole('button', { name: '取消订单', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: '确认取消订单', exact: true }).click();
  await page.getByRole('heading', { name: '已取消', exact: true }).waitFor();
  for (const route of ['overview', 'store', 'cart', 'checkout', 'orders', 'addresses']) {
    await page.goto(base + '/practice-app#' + route); await page.locator('.commerce-page-stack').waitFor(); await layout('learner', route);
  }
  await page.goto(base + '/practice-app#catalog'); await page.getByText('当前练习角色不能访问此页面', { exact: true }).waitFor();
  results.push('客户结算取消、直接越权路由拦截');
  await role('warehouse');
  for (const route of ['overview', 'inventory', 'fulfillment']) { await page.goto(base + '/practice-app#' + route); await page.locator('.commerce-page-stack').waitFor(); await layout('warehouse', route); }
  await role('lab_admin');
  for (const route of ['overview', 'catalog', 'inventory', 'fulfillment', 'audit']) { await page.goto(base + '/practice-app#' + route); await page.locator('.commerce-page-stack').waitFor(); await layout('lab_admin', route); }
  await page.goto(base + '/practice-app#overview'); await page.locator('.commerce-stat-grid').waitFor();
  await page.screenshot({ path: 'output/commerce-v2-20261029/operations-desktop.png', fullPage: true });
  await page.goto(base + '/practice-app#catalog');
  await page.getByRole('button', { name: '新增商品', exact: true }).click();
  await layout('lab_admin', 'product-modal');
  await page.getByRole('button', { name: 'Close', exact: true }).click();
  results.push('四角色真实登录；完整业务页面与商品弹窗多尺寸布局');
  await page.evaluate(token => { sessionStorage.setItem('token', token); sessionStorage.removeItem('cling:practice:session'); }, platformToken);
  await page.goto(base + '/?module=practice_lab');
  return { results, layouts, errors };
}
