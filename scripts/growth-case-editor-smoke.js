async page => {
  if (await page.getByRole('dialog').count()) await page.getByRole('button', { name: /取\s*消/ }).click();
  await page.getByLabel('自测模块').selectOption('ui');
  await page.getByRole('button', { name: '新建结构化用例' }).click();
  await page.getByRole('dialog').waitFor();
  if (await page.getByPlaceholder('元素名称 / 选择器').isVisible()) throw new Error('打开页面动作仍展示无关定位字段');
  if (!await page.getByPlaceholder('输入值 / 页面地址').isVisible()) throw new Error('打开页面缺少地址字段');
  await page.locator('.ui-auto-step .ant-select').first().click();
  await page.getByText('点击', { exact: true }).last().click();
  if (!await page.getByPlaceholder('元素名称 / 选择器').isVisible()) throw new Error('点击动作未显示定位字段');
  if (await page.getByPlaceholder('输入值 / 页面地址').isVisible()) throw new Error('点击动作显示无关输入值');
  await page.locator('.ui-auto-step .ant-select').first().click();
  await page.getByText('打开页面', { exact: true }).last().click();
  if (await page.getByPlaceholder('输入值 / 页面地址').inputValue() !== '/') throw new Error('切换动作丢失隐藏字段值');
  await page.getByRole('button', { name: /取\s*消/ }).click();
  return { passed: ['按动作显示必需字段', '隐藏字段保留已有值', '编辑弹窗可取消'] };
}
