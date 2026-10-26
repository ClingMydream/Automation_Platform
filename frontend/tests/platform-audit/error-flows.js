async page => {
 page.setDefaultTimeout(7000);page.setDefaultNavigationTimeout(30000);
 const results=[],errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:3104/?module=circle_stats',{waitUntil:'domcontentloaded'});
 const test=async(name,fn)=>{try{await fn();results.push({name,status:'passed'})}catch(e){results.push({name,status:'failed',reason:e.message.slice(0,700)})}};
 await test('全员圈：采集失败可见、刷新恢复、中断任务禁写',async()=>{
  await page.route('**/api/v1/circle-stats/runs',route=>route.fulfill({status:503,json:{detail:'隔离测试：采集服务不可用'}}));
  await page.getByRole('button',{name:'采集并预览',exact:true}).click();await page.getByText('隔离测试：采集服务不可用',{exact:true}).waitFor();
  await page.unroute('**/api/v1/circle-stats/runs');
  const id='c'.repeat(32);let fail=false;
  await page.route('**/api/v1/circle-stats/runs/'+id,route=>route.fulfill(fail?{status:500,json:{detail:'隔离测试：查询失败'}}:{json:{id,status:'interrupted',message:'历史任务执行中断，不能直接写入，请重新采集并核对',preview:[]}}));
  await page.evaluate(id=>localStorage.setItem('cling-circle-task:audit-admin',id),id);await page.reload({waitUntil:'domcontentloaded'});
  await page.getByText('历史任务执行中断，不能直接写入，请重新采集并核对',{exact:true}).waitFor();
  if(!await page.getByRole('button',{name:'确认写入在线表格',exact:true}).isDisabled())throw new Error('interrupted plan can write');
  await page.getByText(/最近成功查询/).waitFor();
  await page.evaluate(()=>localStorage.removeItem('cling-circle-task:audit-admin'));await page.unroute('**/api/v1/circle-stats/runs/'+id);
 });
 await test('文件快传：实际下载内容一致',async()=>{
  await page.goto('http://127.0.0.1:3104/?module=files',{waitUntil:'domcontentloaded'});
  await page.locator('#main-content input[type=file]').setInputFiles({name:'audit-download.txt',mimeType:'text/plain',buffer:Buffer.from('download-content-verified')});
  await page.getByRole('button',{name:/复制扫码链接$/}).waitFor();
  const data=await page.evaluate(async()=>{const t=sessionStorage.getItem('token')||localStorage.getItem('token');return (await fetch('/api/file-transfers',{headers:{Authorization:'Bearer '+t}})).json()});
  const item=data.find(x=>x.original_name==='audit-download.txt');if(!item)throw new Error('uploaded item not found');
  const response=await page.request.get(item.download_url);if(response.status()!==200||await response.text()!=='download-content-verified')throw new Error('download content mismatch');
 });
 await test('受限账号：菜单隔离与管理接口 403',async()=>{
  const created=await page.evaluate(async()=>{const t=sessionStorage.getItem('token')||localStorage.getItem('token');const r=await fetch('/api/users',{method:'POST',headers:{Authorization:'Bearer '+t,'Content-Type':'application/json'},body:JSON.stringify({username:'limited_'+Date.now(),password:'isolated-only',menu_permissions:['data_generator']})});return r.json()});
  const login=await page.request.post('http://127.0.0.1:3104/api/auth/login',{data:{username:created.username,password:'isolated-only'}});const {access_token}=await login.json();
  const denied=await page.request.get('http://127.0.0.1:3104/api/users',{headers:{Authorization:'Bearer '+access_token}});if(denied.status()!==403)throw new Error('admin API not denied');
  const ctx=await page.context().browser().newContext();const limited=await ctx.newPage();await limited.goto('http://127.0.0.1:3104/');await limited.evaluate(t=>{localStorage.setItem('token',t);sessionStorage.setItem('token',t)},access_token);await limited.goto('http://127.0.0.1:3104/?module=users');
  await limited.getByRole('menuitem',{name:'数据生成',exact:true}).waitFor();if(await limited.getByRole('menuitem',{name:'用户管理',exact:true}).count())throw new Error('admin menu leaked');await ctx.close();
 });
 await test('图片工具：401 返回登录页且无未处理异常',async()=>{
  await page.goto('http://127.0.0.1:3104/?module=images',{waitUntil:'domcontentloaded'});await page.route('**/api/image-tools/generate',route=>route.fulfill({status:401,json:{detail:'expired'}}));
  await page.getByRole('button',{name:/生成并下载$/}).click();await page.getByLabel('登录账号',{exact:true}).waitFor();await page.unroute('**/api/image-tools/generate');
 });
 return {results,errors};
}
