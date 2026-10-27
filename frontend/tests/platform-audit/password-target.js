async page => {
 const context=await page.context().browser().newContext();const target=await context.newPage();const layouts=[];
 try{await target.goto('http://127.0.0.1:3104/');const field=target.getByLabel('登录密码',{exact:true});await field.fill('isolated-example-only');
 for(const width of [1440,1280,768,390,320]){await target.setViewportSize({width,height:900});const button=target.getByRole('button',{name:'显示',exact:true});const box=await button.boundingBox();if(!box||box.width<24||box.height<24)throw new Error('small password target '+width);await button.click();if(await field.getAttribute('type')!=='text'||await field.inputValue()!=='isolated-example-only')throw new Error('password reveal failed');await target.getByRole('button',{name:'隐藏',exact:true}).click();if(await field.getAttribute('type')!=='password')throw new Error('password hide failed');const size=await target.evaluate(()=>({width:innerWidth,document:document.documentElement.scrollWidth}));if(size.document>width+2)throw new Error('password field overflow');layouts.push({width,targetWidth:box.width,targetHeight:box.height});}
 return {status:'passed',layouts};}finally{await context.close();}
}
