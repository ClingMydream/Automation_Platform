const LABELS={test_authentication_and_role:'鉴权与角色权限',test_order_cancel_and_idempotency:'下单、幂等、取消与库存恢复',test_validation_and_stock_version:'参数校验与库存版本冲突',test_concurrent_inventory_never_negative:'并发库存不超卖',test_integer_amount:'整数金额计算',test_invalid_quantity:'非法数量必须拒绝',test_shop_order_cancel:'页面下单、取消与库存恢复'};
export function testLabel(name=''){const base=name.split('[')[0];return LABELS[base]?(LABELS[base]+(name.includes('[')?' '+name.slice(name.indexOf('[')):'')):name;}
export function reportSummary(run){
 const tests=run.result?.tests||[],passed=tests.filter(row=>row.status==='passed').length,failed=tests.filter(row=>row.status==='failed'),metrics=run.result?.performance;
 if(['queued','running'].includes(run.status))return {title:'执行尚未结束',detail:'请等待完整结果，当前不能判断是否通过。'};
 if(['blocked','interrupted','stopped'].includes(run.status))return {title:'本次执行未完整完成',detail:'先确认执行器状态或停止原因，再决定是否重新运行。已有片段不作为通过依据。'};
 if(run.suite==='performance')return {title:run.status==='passed'?'性能参考验证完成':'性能参考验证未通过',detail:metrics?`请求 ${metrics['Request Count']??'未提供'} 次，失败 ${metrics['Failure Count']??'未提供'} 次，P95 ${metrics['95%']??'未提供'}ms。小规模只读样本不代表生产容量。`:'缺少性能明细，请检查执行输出。'};
 if(!tests.length)return {title:'尚无可核对的检查明细',detail:'不能仅根据状态字段推断场景覆盖，请查看原始输出。'};
 return {title:`参考工程：${passed} 项通过，${failed.length} 项失败`,detail:failed.length?'优先排查：'+failed.map(row=>testLabel(row.name)).join('、')+'。结合日志或截图复现，不要用强制点击或重复重试掩盖问题。':'检查明细见下方；这验证固定参考工程，不代表你的本地改写代码已经通过。'};
}
