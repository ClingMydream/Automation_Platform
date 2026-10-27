async page => {
 const context=await page.context().browser().newContext();const target=await context.newPage();let calls=0,body;
 try{await target.route('**/api/auth/login',async route=>{calls++;body=route.request().postDataJSON();await new Promise(resolve=>setTimeout(resolve,500));await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'服务暂不可用，请稍后重试'})});});
 await target.goto('http://127.0.0.1:3104/');await target.getByLabel('登录账号',{exact:true}).fill('isolated-user');await target.getByLabel('登录密码',{exact:true}).fill('isolated-example');await target.getByRole('checkbox').check();const button=target.getByRole('button',{name:'进入自动化平台',exact:true});await button.dblclick();await target.getByRole('alert').filter({hasText:'服务暂不可用'}).waitFor();
 if(calls!==1||body.username!=='isolated-user'||body.remember_me!==true)throw new Error('duplicate request or remember option lost');if(await target.getByLabel('登录密码',{exact:true}).inputValue()!=='isolated-example')throw new Error('failed login lost input');if(!await target.getByRole('button',{name:'进入自动化平台',exact:true}).isEnabled())throw new Error('failed login cannot retry');
 return {status:'passed',checks:['503可见错误','失败保留输入和记住选项','重复点击仅一次请求','失败可重试']};
 }finally{await context.close();}
}
