async page => {
  await page.getByRole('button', { name: '开始随机答题' }).click();
  await page.locator('.exam-option').first().waitFor();
  await page.locator('.exam-option').first().click();
  await page.getByRole('button', { name: '结束本轮', exact: true }).click();
  await page.getByRole('button', { name: '结束并查看结果' }).click();
  await page.getByRole('button', { name: '回看本轮题目' }).waitFor();
  const before = await page.evaluate(() => JSON.parse(localStorage.getItem('cling:self-study:isolated-smoke:v1')).gradeSnapshot);
  await page.getByRole('button', { name: '回看本轮题目' }).click();
  await page.getByRole('button', { name: '下一题' }).click();
  const enabled = await page.locator('.exam-option:not(:disabled)').count();
  if (enabled) throw new Error('只读回看允许补答');
  await page.getByRole('button', { name: '返回成绩', exact: true }).click();
  const after = await page.evaluate(() => JSON.parse(localStorage.getItem('cling:self-study:isolated-smoke:v1')).gradeSnapshot);
  if (JSON.stringify(before) !== JSON.stringify(after)) throw new Error('回看改变成绩');
  await page.getByRole('button', { name: '进入补答 / 补评' }).click();
  if (!await page.locator('.exam-option:not(:disabled)').count()) throw new Error('显式补答模式不能补答');
  for (const width of [1440, 1280, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) throw new Error(`自考${width}px横向溢出`);
  }
  await page.screenshot({ path: 'D:/Automation_Platform/output/playwright/growth-exam-mobile.png', fullPage: true });
  return { passed: ['原卷评分', '只读回看不能补答', '回看成绩快照不变', '明确进入补答', '多分辨率自考布局'] };
}
