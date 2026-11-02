import React, {useEffect, useRef, useState} from 'react';
import {App, Alert, Button, Card, Collapse, Input, Select, Space, Spin, Tag} from 'antd';
import {MarkdownView} from './MarkdownView.jsx';
import {requestId} from '../../shared/requestId.js';
import {firstUnit as unit} from './learningUnits.js';

const API='/v1/personal-workspace/records';
const marker='\n\n## 我的学习记录\n';
const tag='learning-unit:'+unit.id;
const title='学习单元｜'+unit.title;
const answerHeading='## 参考答案（练习时先自己回答）';
const [beforeAnswer, tail='']=unit.body.split(answerHeading);
const [answer, ...remaining]=tail.split('## 与测试工作的联系');

export function LearningUnitPanel({client,userKey,onNavigate,onHistory}){
 const {message}=App.useApp();
 const [note,setNote]=useState(null),[text,setText]=useState(''),[status,setStatus]=useState('open');
 const [loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[error,setError]=useState(''),[draftWarning,setDraftWarning]=useState(''),[loadFailed,setLoadFailed]=useState(false);
 const lock=useRef(false),key=useRef(requestId());
 const storage='cling:learning-unit:'+userKey+':'+unit.id;
 useEffect(()=>{
  let alive=true;
  setLoading(true);
  client.get(API+'?kind=note&q='+encodeURIComponent(title)).then(rows=>{
   if(!alive)return;
   const saved=rows.find(row=>row.tags.includes(tag));setNote(saved||null);
   let local;try{local=JSON.parse(localStorage.getItem(storage)||'null');}catch{setDraftWarning('无法读取本机草稿，请留意保存状态。');}
   const valid=local&&typeof local.text==='string'&&['open','doing','done'].includes(local.status);
   setText(valid?local.text:(saved?.content.split(marker).slice(1).join(marker)||''));
   setStatus(valid?local.status:(saved?.status||'open'));
   if(valid)setDraftWarning('已恢复本机未提交的学习记录，请核对后保存。');
   setError('');
  }).catch(e=>{if(alive){setError(e.message);setLoadFailed(true);}}).finally(()=>{if(alive)setLoading(false);});
  return()=>{alive=false;};
 },[userKey]);
 function draft(nextText,nextStatus){setText(nextText);setStatus(nextStatus);try{localStorage.setItem(storage,JSON.stringify({text:nextText,status:nextStatus}));}catch{setDraftWarning('本机草稿保存失败，请及时保存到笔记本。');}}
 async function save(){
  if(lock.current)return;
  if(status==='done'&&text.trim().length<10){message.warning('请至少记录10字的学习过程，再标记完成。');return;}
  lock.current=true;setBusy(true);setError('');
  const body={kind:'note',title,content:unit.body+marker+text,status,tags:[tag,'学习单元',unit.course],due_at:null,client_request_id:note?.client_request_id||key.current};
  try{
   const result=note?await client.put(API+'/'+note.id,{...body,revision:note.revision}):await client.post(API,body);
   setNote(result);try{localStorage.removeItem(storage);}catch{}setDraftWarning('');message.success('学习记录已保存到笔记本');
  }catch(e){setError(e.message+'；输入仍保留。若提示版本冲突，请先在笔记本核对，避免覆盖其他修改。');}
  finally{setBusy(false);lock.current=false;}
 }
 return <div className="link-learning" data-testid="link-learning">
  <header className="link-learning-header"><div><Tag color="blue">按链接学习</Tag><h2>把一节课，真正学会。</h2><p>看原课 → 理解知识点 → 运行示例 → 动手改写 → 记录与复习</p></div><Button onClick={onHistory} disabled={busy}>历史学习记录</Button></header>
  <div className="link-learning-layout">
   <aside aria-label="课程与学习单元"><Card title={unit.course}><p>第一阶段 · 开发环境</p><Button block type="primary" aria-current="page">01 配置 Python 开发环境</Button><p className="personal-footnote">已整理 1 个单元。原课程共124讲，其余尚未整理，未计入完成度。</p><Tag color={note?.status==='done'?'green':'default'}>{note?.status==='done'?'本单元已完成（自己确认）':'本单元待学习'}</Tag></Card><Card title="学习建议"><p>先尝试回答问题，再展开参考答案。学完后，次日不看资料重新运行一次。</p><p>后续提供具体视频链接，按同一结构继续整理归纳。</p></Card></aside>
   <section aria-label="学习单元内容" data-testid="learning-unit-content">
    <Card extra={<Button href={unit.url} target="_blank" rel="noopener noreferrer">打开原视频</Button>} title={unit.title}>
     <Alert type="info" title="个人学习整理" description="依据本节字幕、摘要与课后习题归纳。Windows代码和测试练习为补充设计；原视频仍在极客时间播放。"/>
     <MarkdownView text={beforeAnswer}/>
     <Collapse items={[{key:'answer',label:'查看参考答案',children:<MarkdownView text={answer}/>}]}/>
     <MarkdownView text={'## 与测试工作的联系'+remaining.join('## 与测试工作的联系')}/>
    </Card>
    <Card title="我的学习记录" data-testid="learning-unit-notes">
     {loading?<Spin/>:<>
      {error&&<Alert type="error" title="保存或读取未完成" description={error}/>}
      {draftWarning&&<Alert type="warning" title={draftWarning}/>}
      <Input.TextArea aria-label="本单元学习记录" value={text} onChange={e=>draft(e.target.value,status)} rows={6} maxLength={10000} disabled={busy||loadFailed} placeholder="实际命令和输出、遇到的问题、解决方式，还有哪里不理解。"/>
      {loadFailed&&<Button onClick={()=>location.reload()}>重新读取学习记录</Button>}<Space wrap><Select aria-label="本单元学习状态" value={status} disabled={busy} onChange={value=>draft(text,value)} options={[{value:'open',label:'未开始'},{value:'doing',label:'学习中'},{value:'done',label:'已完成（自己确认）'}]}/><Button type="primary" loading={busy} onClick={save} disabled={loadFailed}>保存学习记录到笔记本</Button>{note&&<Button onClick={()=>onNavigate('knowledge',{record:note.id})}>打开关联笔记</Button>}</Space>
      <p className="personal-footnote">{note?'已建立笔记关联；修改后请保存。':'首次保存会在你的笔记本中创建本单元记录。'}完成状态由你确认，不表示代码已经自动验证。</p>
     </>}
    </Card>
   </section>
  </div>
 </div>;
}
