async page => {
  await page.getByText('0 条确认通过，1 条失败，0 条结果无法确认。', { exact: false }).waitFor();
  const reads = await page.evaluate(() => window.smoke.runReads);
  await page.waitForTimeout(3500);
  if (await page.evaluate(() => window.smoke.runReads) !== reads) throw new Error('终态任务仍持续轮询');
  for (const width of [1440, 1280, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) throw new Error(`UI自动化 ${width}px 横向溢出`);
  }
  await page.screenshot({ path: 'D:/Automation_Platform/output/playwright/growth-ui-mobile.png', fullPage: true });
  await page.getByLabel('自测模块').selectOption('learning');
  return { passed: ['同用例前步骤通过后步骤失败不误判', '终态停止轮询', '1440/1280/768/390/320布局'], next: '学习空间' };
}
