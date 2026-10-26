async page => {
 const base='http://127.0.0.1:3104';
 const cases=Array.from({length:32},(_,i)=>({id:9000+i,feature_id:1,name:`历史长链路用例 ${i+1}`,enabled:true,steps:[{action:'screenshot'}],tags:[],priority:'P1'}));
 const run={id:9000,status:'passed',case_ids:cases.slice(0,8).map(x=>x.id),branch:'dev-20260930-1.9.2/'+('long-branch-'.repeat(9)),target_url:'https://example.invalid/'+('long-target-'.repeat(12)),commit_sha:'a'.repeat(40),random_seed:12345678,viewport:'desktop',current_step:'测试结束',progress:100,artifacts:[],result_summary:{timeline:[]},started_at:'2026-10-26T00:00:00Z',finished_at:'2026-10-26T00:00:01Z'};
 await page.route('**/api/v1/ui-automation/overview',r=>r.fulfill({json:{features:[{id:1,name:'历史数据回归'}],cases,runs:[run],requirements:[],smoke_catalog:[]}}));
 await page.route('**/api/v1/ui-automation/runs/9000',r=>r.fulfill({json:run}));
 await page.goto(base+'/?module=emote_ui_automation',{waitUntil:'domcontentloaded'});await page.getByText('测试结束',{exact:true}).waitFor();
 const results=[];
 for(const width of [1440,1280,768,390,320]){
  await page.setViewportSize({width,height:900});await page.waitForTimeout(100);
  const row=await page.evaluate(()=>({width:innerWidth,document:document.documentElement.scrollWidth}));results.push(row);
  if(row.document>width+2)throw new Error('populated history overflow '+JSON.stringify(row));
 }
 await page.setViewportSize({width:1280,height:900});
 const fixed=await page.locator('.ui-auto-case-scroll').evaluate(n=>({height:n.clientHeight,content:n.scrollHeight}));if(fixed.content<=fixed.height)throw new Error('case list no longer scrolls inside its fixed area');
 await page.unroute('**/api/v1/ui-automation/overview');await page.unroute('**/api/v1/ui-automation/runs/9000');
 return {status:'passed',layouts:results,fixedCaseList:fixed};
}
