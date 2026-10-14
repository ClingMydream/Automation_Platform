async page => {
  await page.getByLabel('自测模块').selectOption('commands');
  await page.getByRole('button', { name: '复制命令' }).waitFor();
  await page.evaluate(() => Object.defineProperty(window, 'isSecureContext', { configurable: true, value: false }));
  await page.getByRole('button', { name: '复制命令' }).click();
  await page.getByText('命令已复制，请确认环境和参数后再执行', { exact: true }).waitFor();
  for (const width of [1440, 1280, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) throw new Error(`命令手册${width}px横向溢出`);
  }
  return { passed: ['HTTP环境复制兼容', '多分辨率命令手册布局'] };
}
