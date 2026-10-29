import {requestId} from '../../shared/requestId.js';
export {requestId};
export const MONEY=cents=>'¥'+(Number(cents||0)/100).toFixed(2);
export const STATUS={pending_payment:'待付款',paid:'待发货',shipped:'待收货',completed:'已完成',cancelled:'已取消',refund_requested:'退款审核中',refunded:'已退款'};
export const ROLES={customer:'练习客户',admin:'运营管理员',warehouse:'仓库专员'};
export const CATEGORIES=['办公文具','桌面数码','出行配件','生活收纳'];
export const COLOR={pending_payment:'gold',paid:'blue',shipped:'cyan',completed:'green',cancelled:'default',refund_requested:'orange',refunded:'purple'};
export function practiceClient(token){
 async function request(path,method='GET',body){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),20000);try{const response=await fetch('/api/practice/v1'+path,{method,headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:controller.signal});const data=await response.json();if(!response.ok){const fields=Array.isArray(data.detail)?[...new Set(data.detail.map(item=>item.loc?.at(-1)))].join('、'):'';const e=new Error(typeof data.detail==='string'?data.detail:'参数不符合要求，请检查 '+fields);e.status=response.status;throw e;}return data;}catch(e){if(e.name==='AbortError')throw new Error('请求超时，请先核对操作结果，再使用同一提交编号重试');throw e;}finally{clearTimeout(timer);}}
 return {get:path=>request(path),post:(path,data)=>request(path,'POST',data),put:(path,data)=>request(path,'PUT',data),delete:path=>request(path,'DELETE')};
}
export function workspaceId(session){try{return session.workspace_id||JSON.parse(atob(session.token.split('.')[1].replace(/-/g,'+').replace(/_/g,'/'))).tenant||'unknown';}catch{return'unknown';}}
export function exportMovements(rows){const cell=v=>'"'+String(v??'').replace(/^[=+@-]/,"'$&").replaceAll('"','""')+'"';const content=[['商品','SKU','变化','可用库存','原因','关联','时间'],...rows.map(r=>[r.name,r.sku,r.delta,r.balance,r.reason,r.reference,r.created_at])].map(row=>row.map(cell).join(',')).join('\r\n');const url=URL.createObjectURL(new Blob(['\ufeff'+content],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='inventory-movements.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
