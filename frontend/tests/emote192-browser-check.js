// Run against tests/emote192-smoke.html with playwright-cli run-code --filename.
async page => {
  await page.getByRole('button',{name:'experiment 1.9.2 专项',exact:true}).click();
  const box=page.getByRole('checkbox',{name:'本次允许专用账号 B 申请注销并取消（仅测试环境）'});
  if(await box.isChecked()) throw new Error('unsafe default');
  await box.check();
  await page.getByRole('button',{name:'确认并开始执行',exact:true}).click();
  await page.waitForTimeout(500);
  const request=await page.evaluate(()=>window.smokeRequests.at(-1));
  if(request.body.mode!=='emote192'||request.body.allow_sensitive!==true||request.body.data_set_id!==3) throw new Error('wrong payload');
  await page.getByRole('button',{name:'Cancel',exact:true}).click();
  await page.getByRole('button',{name:'experiment 1.9.2 专项',exact:true}).click();
  if(await box.isChecked()) throw new Error('consent leaked between runs');
  await page.waitForTimeout(400);
  await page.screenshot({path:'output/emote-192/catalog-consent.png'});
  await page.getByRole('button',{name:'Cancel',exact:true}).click();
  await page.getByRole('button',{name:'1.9.2 · 昵称可用 已启用 2 步 ·',exact:true}).click();
  await page.getByRole('dialog').getByText('昵称可用',{exact:true}).waitFor();
  await page.waitForTimeout(400);
  await page.screenshot({path:'output/emote-192/catalog-editor.png'});
  console.log('PASS: suite request, selected dataset, explicit consent, fresh consent, editable scenario');
}
