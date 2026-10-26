async page => {
 const base='http://127.0.0.1:3104';page.setDefaultTimeout(8000);
 const login=await page.request.post(base+'/api/auth/login',{data:{username:'audit-admin',password:'isolated-audit-20261026'}});const token=(await login.json()).access_token;
 await page.goto(base);await page.evaluate(t=>{localStorage.setItem('token',t);sessionStorage.setItem('token',t);localStorage.removeItem('cling:self-study:audit-admin:v1')},token);await page.goto(base+'/?module=self_study');
 await page.getByRole('button',{name:'开始随机答题 →',exact:true}).click();
 const paper=await page.evaluate(()=>JSON.parse(localStorage.getItem('cling:self-study:audit-admin:v1')));if(paper.ids.length!==31)throw new Error('paper not scoped to real account');
 const name='student_'+Date.now();const create=await page.request.post(base+'/api/users',{headers:{Authorization:'Bearer '+token},data:{username:name,password:'isolated-only',menu_permissions:['self_study']}});if(create.status()!==200)throw new Error(await create.text());
 const b=await page.request.post(base+'/api/auth/login',{data:{username:name,password:'isolated-only'}});const other=(await b.json()).access_token;
 await page.evaluate(t=>{localStorage.setItem('token',t);sessionStorage.setItem('token',t)},other);await page.reload();await page.getByRole('button',{name:'开始随机答题 →',exact:true}).waitFor();
 if(await page.evaluate(n=>Boolean(localStorage.getItem('cling:self-study:'+n+':v1')),name))throw new Error('other account inherited answers');
 await page.evaluate(({token,paper})=>{localStorage.setItem('token',token);sessionStorage.setItem('token',token);localStorage.setItem('cling:self-study:undefined:v1',JSON.stringify(paper));localStorage.removeItem('cling:self-study:undefined:v1:owner');localStorage.removeItem('cling:self-study:audit-admin:v1')},{token,paper});
 await page.reload();await page.getByRole('button',{name:'导入旧进度',exact:true}).click();await page.getByRole('button',{name:'确认是我的进度',exact:true}).click();await page.locator('.exam-prompt').waitFor();
 const imported=await page.evaluate(()=>({old:localStorage.getItem('cling:self-study:undefined:v1'),current:localStorage.getItem('cling:self-study:audit-admin:v1'),owner:localStorage.getItem('cling:self-study:undefined:v1:owner')}));if(!imported.old||!imported.current||imported.owner!=='audit-admin')throw new Error('migration lost backup');
 await page.evaluate(()=>{localStorage.removeItem('cling:self-study:undefined:v1');localStorage.removeItem('cling:self-study:undefined:v1:owner')});
 await page.setViewportSize({width:1440,height:1000});await page.goto(base+'/?module=emote_ui_automation');await page.waitForTimeout(700);await page.screenshot({path:'output/platform-audit-20261026/test-center-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});await page.goto(base+'/?module=data_generator');await page.waitForTimeout(500);await page.screenshot({path:'output/platform-audit-20261026/tools-mobile.png',fullPage:true});
 await page.setViewportSize({width:1440,height:1000});return {status:'passed',checks:['31题组卷','双账号进度隔离','旧进度本人确认导入','原始副本保留','桌面与手机截图']};
}
