async page => {
  await page.reload();
  const input = page.getByPlaceholder('描述具体做了什么');
  await input.fill('先保存的内容');
  await page.getByRole('button', { name: '保存草稿' }).click();
  await input.fill('保存途中继续输入的最新内容');
  await page.waitForTimeout(1250);
  if (await input.inputValue() !== '保存途中继续输入的最新内容') throw new Error('保存响应覆盖了新输入');
  await page.waitForTimeout(1800);
  if (await page.evaluate(() => window.smoke.saved.sections.items[0].content) !== '保存途中继续输入的最新内容') throw new Error('后续输入未保存');
  await page.evaluate(() => { window.smoke.failSave = true; });
  await input.fill('保存失败时的新内容');
  await page.getByRole('button', { name: '完成', exact: false }).click();
  await page.waitForTimeout(1250);
  if (await page.evaluate(() => window.smoke.completes) !== 0) throw new Error('保存失败仍完成报告');
  if (await input.inputValue() !== '保存失败时的新内容') throw new Error('失败后输入丢失');
  for (const width of [1440, 1280, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) throw new Error(`日报${width}px横向溢出`);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: 'D:/Automation_Platform/output/playwright/growth-report-mobile.png', fullPage: true });
  return { passed: ['保存中继续输入不丢字', '新输入随后自动保存', '保存失败不完成报告', '失败输入保留', '390px日报布局'] };
}
