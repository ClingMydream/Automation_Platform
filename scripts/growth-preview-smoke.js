async page => {
  await page.getByLabel('自测模块').selectOption('report');
  await page.getByLabel('自测模块').selectOption('preview');
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: '比对线上版本' }).click();
  await page.getByRole('combobox').nth(1).click();
  await page.getByText('feature-smoke', { exact: true }).last().click();
  await page.getByText('版本:feature-smoke', { exact: true }).waitFor();
  await page.waitForTimeout(1500);
  if (await page.getByText('版本:dev-20260811-1.9.1', { exact: true }).count()) throw new Error('旧请求覆盖新分支');
  for (const width of [1440, 1280, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) throw new Error(`在线预览${width}px横向溢出`);
  }
  return { passed: ['慢请求不覆盖新分支', '多分辨率预览布局'] };
}
