async page => {
 const context=await page.context().browser().newContext();const target=await context.newPage();const errors=[],checks=[];target.on('pageerror',error=>errors.push(error.message));
 try{
  await target.goto('http://127.0.0.1:3104/?transferToken=isolated-not-found');await target.locator('.public-transfer-screen').waitFor();await target.locator('.public-transfer-screen .ant-alert-error').waitFor();checks.push('公开文件分享与失效反馈保留');
  await target.route('**/api/test-packages/public/latest',route=>route.fulfill({status:404,json:{detail:'隔离检查：暂无测试包'}}));await target.goto('http://127.0.0.1:3104/?testPackage=latest');await target.getByRole('heading',{name:'测试包下载',exact:true}).waitFor();await target.getByText('隔离检查：暂无测试包',{exact:true}).waitFor();checks.push('公开测试包入口与失败反馈保留');
  if(errors.length)throw new Error(errors.join(';'));return {status:'passed',checks,errors};
 }finally{await context.close();}
}
