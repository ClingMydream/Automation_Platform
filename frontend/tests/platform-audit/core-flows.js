async page => {
 page.setDefaultTimeout(7000); page.setDefaultNavigationTimeout(30000);
 await page.goto('http://127.0.0.1:3104/?module=data_generator',{waitUntil:'domcontentloaded'});await page.getByRole('menuitem',{name:'今日工作台',exact:true}).waitFor();const expand=page.getByRole('button',{name:'显示全部功能',exact:true});if(await expand.count())await expand.click();
 const suffix=Date.now().toString(); const results=[],errors=[];page.on('pageerror',e=>errors.push(e.message));
 const nav=async name=>{const group={ 'JSON 工具':['文本工具','JSON 格式化与对比'],'转码工具':['文本工具','编码与解码'],'测试包安装':['Emote 测试环境','安装包'] }[name];await page.getByRole('menuitem',{name:group?group[0]:name,exact:true}).click();if(group)await page.getByRole('tab',{name:group[1],exact:true}).click();await page.waitForTimeout(350);};
 const test=async(name,fn)=>{try{await fn();results.push({name,status:'passed'});await page.evaluate(value=>sessionStorage.setItem('platform-audit-flows',JSON.stringify(value)),{results,errors});}catch(e){results.push({name,status:'failed',reason:e.message.slice(0,700)});await page.evaluate(value=>sessionStorage.setItem('platform-audit-flows',JSON.stringify(value)),{results,errors});await page.goto('http://127.0.0.1:3104/?module=data_generator',{waitUntil:'domcontentloaded'});await page.getByRole('button',{name:/展开或收起导航$/}).waitFor();}};
 await test('数据生成：生成、保存、备注、读取、修改、删除',async()=>{
  await nav('数据生成');await page.getByRole('button').filter({hasText:'立即生成'}).click();
  await page.getByRole('button',{name:/保存当前批次$/}).click();
  let dialog=page.getByRole('dialog');await dialog.getByRole('textbox',{name:'批次名称',exact:true}).fill(('平台自测账号批次'+suffix));
  await dialog.getByRole('textbox',{name:'批次备注',exact:true}).fill('仅隔离环境');
  await dialog.getByRole('button',{name:/^保\s*存$/}).click();
  let row=page.getByRole('row').filter({hasText:('平台自测账号批次'+suffix)});await row.getByRole('button',{name:/查看\ \/\ 编辑$/}).click();
  await dialog.getByRole('textbox',{name:'批次备注',exact:true}).fill('已修改备注');await dialog.getByRole('button',{name:/^保\s*存$/}).click();
  await row.getByText('已修改备注',{exact:true}).waitFor();await row.getByRole('button',{name:/载入\ \/\ 导出$/}).click();
  await row.getByRole('button',{name:/删\s*除$/}).click();await page.getByRole('tooltip').getByRole('button',{name:/^(?:确\s*定|OK|Yes)$/}).click();
 });
 await test('JSON：格式化、压缩、差异检查、HTTP 复制降级',async()=>{
  await nav('JSON 工具');await page.locator('#main-content textarea').first().fill('{"a":1}');await page.locator('#main-content textarea').nth(1).fill('{"a":2}');
  await page.getByRole('button',{name:/格式化$/}).first().click();if(!(await page.locator('#main-content textarea').first().inputValue()).includes('\n'))throw new Error('format failed');
  await page.getByRole('button',{name:/压\s*缩/}).first().click();await page.getByRole('button',{name:/开始对比$/}).click();await page.getByText('值不同',{exact:true}).waitFor();
  await page.evaluate(()=>{Object.defineProperty(navigator,'clipboard',{configurable:true,value:undefined});});
  await page.getByRole('button',{name:/复制$/}).first().click();await page.getByText('已复制',{exact:true}).last().waitFor();
 });
 await test('转码：执行、复制与输入输出互换',async()=>{
  await nav('转码工具');await page.getByRole('button',{name:/执行转码$/}).click();
  const fields=page.locator('#main-content textarea');if(!(await fields.nth(1).inputValue()).includes('%'))throw new Error('encode failed');
  await page.getByRole('button',{name:/输入\/输出互换$/}).click();if(!(await fields.first().inputValue()).includes('%'))throw new Error('swap failed');
  await page.getByRole('button',{name:/复制$/}).first().click();
 });
 await test('接口工作台：记录及新建表单不继承旧数据',async()=>{
  await nav('接口工作台');await page.getByRole('button',{name:/记录接口$/}).click();let dialog=page.getByRole('dialog');
  await dialog.getByPlaceholder('例如：查询订单详情').fill(('平台自测接口'+suffix));await dialog.getByPlaceholder('https://api.example.com/orders/{id}').fill('https://example.invalid/test');
  await dialog.getByRole('button',{name:/^保\s*存$/}).click();await page.getByText(('平台自测接口'+suffix),{exact:true}).waitFor();
  await page.getByRole('button',{name:/记录接口$/}).click();if(await dialog.getByPlaceholder('https://api.example.com/orders/{id}').inputValue())throw new Error('new form inherited previous URL');await dialog.getByRole('button',{name:/^Close$|^关闭$/}).click();
 });
 await test('用户管理：新增、修改、清空旧密码、删除',async()=>{
  await nav('用户管理');await page.getByPlaceholder('例如：tester01').fill(('audit_member_01'+suffix));await page.getByPlaceholder('例如：测试同事 A').fill('隔离自测成员');await page.getByPlaceholder('至少 6 位').fill('isolated-password');
  await page.getByRole('checkbox',{name:/数据生成/}).check();await page.getByRole('button',{name:/创建用户$/}).click();let row=page.getByRole('row').filter({hasText:('audit_member_01'+suffix)});await row.getByRole('button',{name:/修改$/}).click();
  if(await page.getByPlaceholder('不填则不修改密码').inputValue())throw new Error('password was carried over');await page.getByPlaceholder('例如：测试同事 A').fill('隔离成员已修改');await page.getByRole('button',{name:/更新用户$/}).click();await row.getByText('隔离成员已修改',{exact:true}).waitFor();
  await row.getByRole('button',{name:/删\s*除$/}).click();await page.getByRole('dialog').getByRole('button',{name:/删\s*除$/}).click();
 });
 await test('图片工具：生成下载与上传图片处理下载',async()=>{
  await nav('图片工具');await page.getByLabel(/宽度 px/).fill('128');await page.getByLabel(/高度 px/).fill('128');
  const [download]=await Promise.all([page.waitForEvent('download',{timeout:15000}),page.getByRole('button',{name:/生成并下载$/}).click()]);
  await download.saveAs('output/platform-audit-20261026/generated.png');
  await page.locator('#main-content input[type=file]').setInputFiles('output/platform-audit-20261026/generated.png');
  await Promise.all([page.waitForEvent('download',{timeout:15000}),page.getByRole('button',{name:/处理并下载$/}).click()]);
 });
 await test('文件快传：上传、复制、二维码、下载及删除',async()=>{
  await nav('文件快传');await page.locator('#main-content input[type=file]').setInputFiles({name:'platform-audit-'+suffix+'.txt',mimeType:'text/plain',buffer:Buffer.from('isolated platform smoke test')});
  await page.getByRole('button',{name:/复制扫码链接$/}).click();let row=page.getByRole('row').filter({hasText:'platform-audit-'+suffix+'.txt'});await row.getByRole('button',{name:/二维码$/}).click();
  await row.getByRole('button',{name:/删\s*除$/}).click();await page.getByRole('dialog').getByRole('button',{name:/删\s*除$/}).click();
 });
 await test('命令手册：新增、复制、收藏、编辑与删除',async()=>{
  await nav('命令手册');await page.getByRole('button',{name:/记录命令$/}).click();let dialog=page.getByRole('dialog');await dialog.getByPlaceholder('例如 Linux').fill('Linux');await dialog.getByPlaceholder('例如：查看实时日志').fill(('平台自测命令'+suffix));await dialog.getByPlaceholder('tail -f app.log').fill('printf isolated');await dialog.getByRole('button',{name:/^保\s*存$/}).click();
  const card=page.locator('.command-card').filter({hasText:('平台自测命令'+suffix)});await card.getByRole('button',{name:/复制命令$/}).click();await card.getByRole('button',{name:/收藏$/}).click();await card.getByRole('button',{name:/编辑$/}).click();await dialog.getByPlaceholder('例如：查看实时日志').fill(('平台自测命令已修改'+suffix));await dialog.getByRole('button',{name:/^保\s*存$/}).click();
  const edited=page.locator('.command-card').filter({hasText:('平台自测命令已修改'+suffix)});await edited.getByRole('button',{name:/删\s*除$/}).click();await page.getByRole('tooltip').getByRole('button',{name:/^(?:确\s*定|OK|Yes)$/}).click();
 });
 return {results,errors};
}
