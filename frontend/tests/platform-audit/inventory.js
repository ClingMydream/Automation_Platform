async page => {
 const labels=['Emote UI 自动化','全员圈统计','学习空间','自考题库','命令手册','酒店练习项目','接口工作台','临时效果','在线预览','工作手记','持续集成','数据生成','文件快传','测试包安装','图片工具','JSON 工具','转码工具','莓好审批网页版','集成配置','用户管理','小程序 OA 管理'];
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width:1440,height:1000});
 const results=[];
 for(const label of labels){
  const start=errors.length;
  await page.getByRole('menuitem',{name:label,exact:true}).click();
  await page.waitForTimeout(650);
  const row={label,key:new URL(page.url()).searchParams.get('module'),buttons:await page.locator('#main-content button').allTextContents(),errors:errors.slice(start),layouts:[]};
  for(const width of [1440,1280,768,390,320]){
   await page.setViewportSize({width,height:900});await page.waitForTimeout(80);
   const sizing=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth,offenders:[...document.querySelectorAll('#main-content *')].filter(n=>{const r=n.getBoundingClientRect();return r.width>0&&r.right>innerWidth+2&&!n.closest('.ant-table-content,.ant-table-body,.ant-table-container,pre,.ant-select-dropdown');}).slice(0,5).map(n=>({tag:n.tagName,class:n.className,right:Math.round(n.getBoundingClientRect().right)}))}));
   row.layouts.push({width,...sizing});
  }
  await page.setViewportSize({width:1440,height:1000});
  results.push(row);
 }
 await page.evaluate(rows=>window.platformAudit=rows,results);
 return results;
}
