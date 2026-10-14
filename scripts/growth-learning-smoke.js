async page => {
  await page.getByLabel('自测模块').selectOption('report');
  await page.getByLabel('自测模块').selectOption('learning');
  await page.getByRole('heading', { name: '自测第一关', exact: true }).first().waitFor();
  await page.evaluate(() => { window.smoke.failSave = true; });
  const input = page.getByPlaceholder('我认为会输出……，因为……');
  await input.fill('断网时也必须保留的学习输入');
  await page.getByRole('button', { name: '自测第二关', exact: false }).click();
  await page.waitForTimeout(1300);
  if (await input.inputValue() !== '断网时也必须保留的学习输入') throw new Error('保存失败后切关卡丢输入');
  if (await page.getByRole('heading', { name: '自测第二关', exact: true }).count()) throw new Error('失败后仍切换关卡');
  await page.evaluate(() => { window.smoke.failSave = false; });
  await page.getByRole('button', { name: '自测第二关', exact: false }).click();
  await page.getByRole('heading', { name: '自测第二关', exact: true }).first().waitFor();
  for (const width of [1440, 1280, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) throw new Error(`学习空间 ${width}px 横向溢出`);
  }
  await page.screenshot({ path: 'D:/Automation_Platform/output/playwright/growth-learning-mobile.png', fullPage: true });
  await page.getByLabel('自测模块').selectOption('exam');
  return { passed: ['保存失败阻止切关卡', '失败输入保留', '保存成功后可切关卡', '多分辨率学习布局'], next: '自考' };
}
