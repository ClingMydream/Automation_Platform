async page => {
 page.setDefaultTimeout(8000);page.setDefaultNavigationTimeout(30000);
 await page.goto('http://127.0.0.1:3104/?module=data_generator',{waitUntil:'domcontentloaded'});
 const suffix=Date.now().toString(),results=[],errors=[];page.on('pageerror',e=>errors.push(e.message));
 const nav=async name=>{await page.getByRole('menuitem',{name,exact:true}).click();await page.waitForTimeout(350);};
 const test=async(name,fn)=>{try{await fn();results.push({name,status:'passed'});}catch(e){results.push({name,status:'failed',reason:e.message.slice(0,1000)});await page.goto('http://127.0.0.1:3104/?module=data_generator',{waitUntil:'domcontentloaded'});}finally{await page.evaluate(v=>sessionStorage.setItem('platform-audit-extended',JSON.stringify(v)),{results,errors});}};
 await test('学习空间：笔记新增、修改、保存、目录折叠和删除',async()=>{
  await nav('学习空间');await page.getByRole('button',{name:/查看关卡笔记$/}).click();
  await page.getByRole('button',{name:/新建笔记$/}).click();await page.getByPlaceholder('笔记标题').fill('隔离学习笔记'+suffix);await page.getByPlaceholder('记录你的学习笔记').fill('使用自己的话解释输入、处理与输出，并保留代码示例。');
  await page.locator('.mastery-note-actions').getByRole('button',{name:/保\s*存$/}).click();await page.getByText('笔记已保存',{exact:true}).waitFor();
  await page.getByRole('button',{name:/收起目录$/}).click();await page.getByRole('button',{name:/展开目录$/}).click();
  await page.locator('.mastery-note-actions').getByRole('button',{name:/删\s*除$/}).click();await page.getByRole('dialog').last().getByRole('button',{name:/删\s*除$/}).click();
  await page.locator('.ant-drawer').getByRole('button',{name:/^Close$|^关闭$/}).click();
 });
 await test('工作手记：日志保存、日报汇总及周报 P/R/O 生成',async()=>{
  const openReport=async(name)=>{const [response]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/v1/work-journal/reports')&&r.request().method()==='POST'),page.getByRole('button',{name}).click()]);if(response.status()===409){const dialog=page.getByRole('dialog').last();await dialog.getByRole('button',{name:/打\s*开$/}).click();await dialog.waitFor({state:'hidden'});}const edit=page.getByRole('button',{name:/重新编辑$/});if(await edit.isVisible()){await edit.click();await page.getByRole('button',{name:/保存草稿$/}).waitFor();}};
  await nav('工作手记');await page.getByRole('button',{name:/记一笔$/}).click();await page.getByPlaceholder('今天做了什么，一句话说清').fill('隔离工作日志'+suffix);await page.getByPlaceholder('记录具体做了什么、怎么做的').fill('完成平台隔离自测，记录功能检查结果。');await page.getByRole('button',{name:/保存草稿$|保存修改$/}).click();await page.getByText(/已保存/).first().waitFor();
  await openReport(/写日报$/);await page.getByRole('button',{name:/从当日日志整理$/}).click();await page.getByRole('dialog').getByRole('button',{name:/采纳为草稿$|追加到当前内容$/}).click();
  await page.getByRole('button',{name:/保存草稿$|保存修改$/}).click();if(await page.getByRole('button',{name:/^.*完成$/}).count())await page.getByRole('button',{name:/^.*完成$/}).last().click();
  await openReport(/写周报$/);await page.getByRole('button',{name:/根据日报生成周报$/}).click();
  const modal=page.getByRole('dialog');await modal.getByText('# P-核心进展与结果:',{exact:true}).waitFor();await modal.getByRole('button',{name:/采纳为草稿$|追加到当前内容$/}).click();await page.getByRole('button',{name:/保存草稿$|保存修改$/}).click();
 });
 await test('自动化用例：断开 Codeup 仍可查看、新增编辑、复制与删除',async()=>{
  await nav('Emote UI 自动化');await page.getByRole('button',{name:/新建结构化用例$/}).click();let modal=page.getByRole('dialog');await modal.getByLabel(/用例名称/).fill('隔离自动化用例'+suffix);await modal.getByRole('button',{name:/保\s*存$/}).click();
  const row=page.locator('.ui-auto-case').filter({hasText:'隔离自动化用例'+suffix});await row.getByRole('button').filter({hasText:'隔离自动化用例'+suffix}).click();await modal.getByLabel(/用例名称/).fill('隔离用例修改'+suffix);await modal.getByRole('button',{name:/保\s*存$/}).click();
  const edited=page.locator('.ui-auto-case').filter({hasText:'隔离用例修改'+suffix});await edited.getByRole('button',{name:'复制用例 隔离用例修改'+suffix,exact:true}).click();
  await page.locator('.ui-auto-case').getByRole('button').filter({hasText:'隔离用例修改'+suffix+'（副本）'}).click();await modal.getByRole('button',{name:/删除此用例$/}).click();await page.getByRole('dialog').last().getByRole('button',{name:/删\s*除$/}).click();
  await page.locator('.ui-auto-case').getByRole('button').filter({hasText:'隔离用例修改'+suffix}).first().click();await modal.getByRole('button',{name:/删除此用例$/}).click();await page.getByRole('dialog').last().getByRole('button',{name:/删\s*除$/}).click();
 });
 await test('数据集：加密保存、掩码展示、删除二次确认',async()=>{
  await nav('Emote UI 自动化');await page.getByRole('button',{name:'更多管理操作',exact:true}).click();await page.getByRole('menuitem',{name:/测试数据集$/}).click();let modal=page.getByRole('dialog');await modal.getByPlaceholder('例如：Emote 测试环境账号').fill('隔离数据集'+suffix);await modal.getByRole('button',{name:/加密保存$/}).click();
  await page.getByRole('button',{name:'更多管理操作',exact:true}).click();await page.getByRole('menuitem',{name:/测试数据集$/}).click();modal=page.getByRole('dialog');await modal.getByRole('button',{name:'删除数据集 隔离数据集'+suffix,exact:true}).click();await page.getByRole('dialog').last().getByRole('button',{name:/删\s*除$/}).click();await modal.getByRole('button',{name:/^Close$|^关闭$/}).click();
 });
 await test('测试包：ZIP 上传、固定链接复制与下载资源校验',async()=>{
  await nav('测试包安装');await page.locator('#main-content input[type=file]').setInputFiles('output/platform-audit-20261026/audit-package.zip');await page.getByText('audit-package.zip',{exact:true}).waitFor();await page.getByRole('button',{name:/复制固定链接$/}).click();
  const data=await page.evaluate(async()=>{const t=sessionStorage.getItem('token')||localStorage.getItem('token');return (await fetch('/api/test-packages/latest',{headers:{Authorization:'Bearer '+t}})).json();});
  const response=await page.request.get(data.download_url);if(!response.ok()||(await response.body()).length===0)throw new Error('package download failed');
 });
 await test('临时效果：上传 ZIP、平台预览及只删除本轮效果',async()=>{
  await nav('临时效果');await page.locator('#main-content input[type=file]').setInputFiles('output/platform-audit-20261026/audit-effect.zip');
  const row=page.locator('.effect-row').filter({hasText:'audit-effect'}).first();await row.getByRole('button',{name:/平台内预览$/}).click();await page.frameLocator('.ant-modal iframe').getByRole('heading',{name:'isolated-preview-verified',exact:true}).waitFor();await page.getByRole('dialog').getByRole('button',{name:/^Close$|^关闭$/}).click();await row.getByRole('button',{name:/删\s*除$/}).click();await page.getByRole('tooltip').getByRole('button',{name:/确\s*定$|OK$/}).click();
 });
 await test('集成配置：新增修改删除及模拟发送的重复点击保护',async()=>{
  await nav('集成配置');await page.getByPlaceholder('团队通知机器人').fill('隔离集成'+suffix);await page.getByPlaceholder('https://example.com/webhook').fill('https://example.com/audit-webhook');await page.getByRole('button',{name:/保存配置$/}).click();
  const row=page.getByRole('row').filter({hasText:'隔离集成'+suffix});await row.getByRole('button',{name:/修改$/}).click();await page.getByPlaceholder('团队通知机器人').fill('隔离集成已修改'+suffix);await page.getByRole('button',{name:/更新配置$/}).click();
  let posts=0;await page.route('**/api/v1/integrations/webhooks/*/test',async route=>{posts++;await new Promise(r=>setTimeout(r,500));await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({message:'模拟投递成功'})});});
  const edited=page.getByRole('row').filter({hasText:'隔离集成已修改'+suffix});await edited.getByRole('button',{name:/测\s*试$/}).click();if(!await edited.getByRole('button',{name:/测\s*试$/}).isDisabled())throw new Error('duplicate send not blocked');await page.waitForTimeout(650);if(posts!==1)throw new Error('duplicate webhook');await page.unroute('**/api/v1/integrations/webhooks/*/test');
  await edited.getByRole('button',{name:/删\s*除$/}).click();await page.getByRole('dialog').last().getByRole('button',{name:/删\s*除$/}).click();
 });
 await test('OA 人员：新增、编辑、禁用和删除',async()=>{
  await nav('小程序 OA 管理');await page.getByPlaceholder('例如：baby_a').fill('audit_oa_'+suffix);await page.getByPlaceholder('例如：小美').fill('隔离OA人员'+suffix);await page.getByPlaceholder('至少 6 位').fill('isolated-oa-pass');await page.getByRole('button',{name:/新增人员$/}).click();
  let row=page.getByRole('row').filter({hasText:'隔离OA人员'+suffix});await row.getByRole('button',{name:/编\s*辑$/}).click();await page.getByPlaceholder('例如：小美').fill('隔离OA修改'+suffix);await page.getByRole('button',{name:/保存修改$/}).click();row=page.getByRole('row').filter({hasText:'隔离OA修改'+suffix});await row.getByRole('switch').click();await row.getByRole('button',{name:/删\s*除$/}).click();await page.getByRole('tooltip').getByRole('button',{name:/删\s*除$/}).click();
 });
 return {results,errors};
}
