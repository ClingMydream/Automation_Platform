import React,{useEffect,useState}from'react';
import {App,Alert,Button,Card,Empty,List,Space,Tag,Spin}from'antd';
import {Check,ArrowUpRight,AlarmClock,NotebookPen,FlaskConical,Plus}from'lucide-react';
import {utc}from'./PersonalSpace.jsx';
import './personal-space.css';
const SUITES={api:'接口自动化',ui:'UI 自动化',performance:'性能测试'};
const STATES={passed:'通过',failed:'失败',running:'运行中',queued:'排队中',blocked:'未能启动',stopped:'已停止',interrupted:'已中断'};
export function TodayPanel({client,onNavigate,practiceAllowed}){
 const {message}=App.useApp();const[data,setData]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(null);
 async function load(){try{const next=await client.get('/v1/personal-workspace/summary');setData(next);setError('');}catch(e){setError(e.message);}}
 useEffect(()=>{let active=true;const initial=async()=>{try{const next=await client.get('/v1/personal-workspace/summary');if(active)setData(next);}catch(e){if(active)setError(e.message);}};initial();const timer=setInterval(()=>{if(document.visibilityState==='visible')initial();},60000);return()=>{active=false;clearInterval(timer);};},[client]);
 async function complete(row){if(busy)return;setBusy(row.id);try{await client.put('/v1/personal-workspace/records/'+row.id,{...row,status:'done'});load();}catch(e){message.error(e.message);}finally{setBusy(null);}}
 if(error)return <Alert type="error" title="今日信息暂时无法读取" description={error} action={<Button onClick={load}>重试</Button>}/>;
 if(!data)return <div className="personal-loading"><Spin/><span>正在整理今天的工作…</span></div>;
 return <section className="today-panel" aria-label="今日工作">
  <div className="today-heading"><div><h2>今天，从一件事开始</h2><p>{data.open_tasks?`${data.open_tasks} 件待处理`:'今天的安排，由你决定'}{data.overdue?` · ${data.overdue} 件已到期`:''}</p></div><Space wrap><Button icon={<Plus size={15}/>} onClick={()=>onNavigate('personal_tasks',{new:'task'})}>记待办</Button><Button onClick={()=>onNavigate('personal_tasks',{new:'memo'})}>随手记</Button><Button onClick={()=>onNavigate('knowledge',{new:'note'})}>写笔记</Button></Space></div>
  <div className="today-grid">
   <Card title="接下来要做" extra={<Button type="text" onClick={()=>onNavigate('personal_tasks')}>全部待办<ArrowUpRight size={14}/></Button>}>{data.tasks.length?<List dataSource={data.tasks.slice(0,5)} renderItem={row=><List.Item actions={[<Button key="done" aria-label={'完成待办：'+row.title} loading={busy===row.id} icon={<Check size={16}/>} onClick={()=>complete(row)}/>]}><List.Item.Meta title={<button className="personal-record-title" onClick={()=>onNavigate('personal_tasks',{record:row.id})}>{row.title}</button>} description={row.due_at?<span>{utc(row.due_at).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false})}</span>:'未设置截止时间'}/></List.Item>}/>:<Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂时没有待办，记下今天最重要的一件事"/>}</Card>
   <Card title={<span className="today-card-title"><AlarmClock size={18}/>24 小时内提醒</span>}>{data.reminders.length?<List dataSource={data.reminders.slice(0,5)} renderItem={row=><List.Item><button className="personal-record-title" onClick={()=>onNavigate('personal_tasks',{record:row.id})}>{row.title}</button><Tag color={utc(row.due_at)<new Date()?'orange':undefined}>{utc(row.due_at)<new Date()?'已到期':utc(row.due_at).toLocaleTimeString('zh-CN',{timeZone:'Asia/Shanghai',hour:'2-digit',minute:'2-digit'})}</Tag></List.Item>}/>:<p className="personal-muted">没有即将到期的提醒。给待办或备忘添加时间后，会出现在这里。</p>}</Card>
   <Card title={<span className="today-card-title"><NotebookPen size={18}/>最近笔记</span>} extra={<Button type="text" onClick={()=>onNavigate('knowledge')}>笔记本</Button>}>{data.notes.length?<List dataSource={data.notes} renderItem={row=><List.Item><button className="personal-record-title" onClick={()=>onNavigate('knowledge',{record:row.id})}>{row.title}</button></List.Item>}/>:<p className="personal-muted">把代码、排错过程和经验留下来，下一次更容易找到。</p>}<Button className="today-learning-link" onClick={()=>onNavigate('learning_route',{lesson:data.continue_lesson})}>继续 Python 与测试学习 →</Button></Card>
   <Card title={<span className="today-card-title"><FlaskConical size={18}/>最近实践</span>} extra={practiceAllowed&&<Button type="text" onClick={()=>onNavigate('practice_lab')}>实验室</Button>}>{data.runs.length?<List dataSource={data.runs} renderItem={row=><List.Item><span>{SUITES[row.suite]} #{row.id}</span><Tag color={row.status==='passed'?'green':row.status==='failed'?'red':undefined}>{STATES[row.status]||row.status}</Tag></List.Item>}/>:<p className="personal-muted">先走通一次商品下单，再用自动化验证订单和库存。</p>}<Button onClick={()=>onNavigate('work_journal')}>记录工作 · 整理日报与周报</Button></Card>
  </div>
 </section>;
}
