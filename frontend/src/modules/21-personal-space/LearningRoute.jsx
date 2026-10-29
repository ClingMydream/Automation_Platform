import React,{useEffect,useRef,useState}from'react';
import {App,Alert,Button,Card,Collapse,Empty,Input,Select,Space,Tag,Spin,Steps,Progress}from'antd';
import {MarkdownView}from'./MarkdownView.jsx';
import {requestId}from'../../shared/requestId.js';
import {useRouteSearch}from'../../shared/useRouteSearch.js';
import './personal-space.css';
const API='/v1/personal-workspace';
const normalize=value=>({status:value?.status||'reading',evidence:value?.evidence||'',note_id:value?.note_id||null,run_id:value?.run_id||null});
function covers(lesson,run){
 if(!lesson?.suite||run?.suite!==lesson.suite||run.status!=='passed')return false;
 if(run.suite==='performance')return Number(run.result?.performance?.['Request Count'])>0&&Number(run.result?.performance?.['Failure Count'])===0;
 return lesson.checks?.length>0&&lesson.checks.every(check=>run.result?.tests?.some(item=>item.name?.split('[')[0]===check.name&&item.status==='passed'));
}
export function LearningRoute({client,userKey,onNavigate,practiceAllowed}){
 const {message,modal}=App.useApp(),params=useRouteSearch();
 const [lessons,setLessons]=useState([]),[notes,setNotes]=useState([]),[runs,setRuns]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[busy,setBusy]=useState(false),[draft,setDraft]=useState(null),[draftError,setDraftError]=useState(false),[runError,setRunError]=useState(''),[outlineOpen,setOutlineOpen]=useState(false);
 const write=useRef(false),noteRequest=useRef({fingerprint:'',key:requestId()}),loadedRun=useRef('');
 const lesson=lessons.find(item=>item.id===(params.get('lesson')||'python-values'))||lessons[0];
 async function load(){setLoading(true);try{const [items,records]=await Promise.all([client.get(API+'/lessons'),client.get(API+'/records?kind=note')]);setLessons(items);setNotes(records);setError('');if(practiceAllowed){try{setRuns(await client.get('/v1/practice-lab/runs'));setRunError('');}catch(e){setRunError(e.message);}}}catch(e){setError(e.message);}finally{setLoading(false);}}
 useEffect(()=>{load();},[]);
 useEffect(()=>{if(!lesson)return;let local;try{local=JSON.parse(localStorage.getItem(`cling:learning:${userKey}:${lesson.id}`)||'null');}catch{}const valid=local&&typeof local.evidence==='string'&&['reading','practiced','verified'].includes(local.status)&&['note_id','run_id'].every(key=>local[key]==null||Number.isInteger(local[key]));setDraft({lessonId:lesson.id,...normalize(valid?local:lesson.progress)});setDraftError(false);try{const pending=JSON.parse(localStorage.getItem(`cling:learning-note-request:${userKey}:${lesson.id}`)||'null');noteRequest.current=pending&&typeof pending.fingerprint==='string'&&typeof pending.key==='string'?pending:{fingerprint:'',key:requestId()};}catch{noteRequest.current={fingerprint:'',key:requestId()};}},[lesson?.id]);
 const hydrated=draft?.lessonId===lesson?.id;
 const dirty=hydrated&&JSON.stringify(normalize(draft))!==JSON.stringify(normalize(lesson?.progress));
 useEffect(()=>{if(!hydrated)return;try{const key=`cling:learning:${userKey}:${lesson.id}`;if(dirty)localStorage.setItem(key,JSON.stringify(normalize(draft)));else localStorage.removeItem(key);setDraftError(false);}catch{setDraftError(true);}},[draft,dirty,lesson?.id]);
 useEffect(()=>{const id=params.get('run')||String(draft?.run_id||'');if(!id||!/^\d+$/.test(id)||!lesson||!practiceAllowed||!hydrated)return;const stamp=lesson.id+':'+id;if(loadedRun.current===stamp)return;loadedRun.current=stamp;let alive=true;client.get('/v1/practice-lab/runs/'+id).then(row=>{if(!alive)return;if(row.suite!==lesson.suite)throw new Error('本次执行类型与当前章节不一致，请重新选择');if(['queued','running'].includes(row.status))throw new Error('执行尚未结束，请在实验室等待结果');setRuns(current=>[row,...current.filter(item=>item.id!==row.id)]);setDraft(current=>({...current,run_id:row.id}));setRunError('');}).catch(e=>{if(alive)setRunError(e.message);});return()=>{alive=false;};},[params.get('run'),lesson?.id,hydrated,practiceAllowed,draft?.run_id]);
 function patch(values){setDraft(current=>({...current,...values}));}
 async function persist(makeNote=false){
  if(write.current||!hydrated)return;
  if(makeNote&&draft.evidence.trim().length<10){message.warning('先写下至少10字自己的观察或心得');return;}
  write.current=true;setBusy(true);const payload=normalize(draft),id=lesson.id;
  try{
   if(makeNote){const fingerprint=JSON.stringify({id,...payload});if(noteRequest.current.fingerprint!==fingerprint)noteRequest.current={fingerprint,key:requestId()};try{localStorage.setItem(`cling:learning-note-request:${userKey}:${id}`,JSON.stringify(noteRequest.current));}catch{setDraftError(true);}const result=await client.post(API+'/lessons/'+id+'/notebook',{...payload,client_request_id:noteRequest.current.key});try{localStorage.removeItem(`cling:learning-note-request:${userKey}:${id}`);}catch{}payload.note_id=result.note.id;setNotes(current=>[result.note,...current.filter(row=>row.id!==result.note.id)]);setDraft(current=>({...current,note_id:result.note.id}));message.success(payload.run_id?'学习心得与实际执行摘要已整理到关联笔记':'学习心得已整理到关联笔记');}
   else{await client.put(API+'/lessons/'+id,payload);message.success('学习记录已保存');}
   const items=await client.get(API+'/lessons');setLessons(items);
  }catch(e){message.error(e.message);}finally{write.current=false;setBusy(false);}
 }
 function archive(){if(draft.note_id){modal.confirm({title:'另存为新的学习笔记？',content:'原笔记会保留，不会覆盖你已经编辑的内容。新的笔记将关联到本章。',okText:'生成新笔记',onOk:()=>persist(true)});}else persist(true);}
 if(loading&&!lessons.length)return <div className="personal-loading"><Spin/></div>;
 if(error)return <Alert type="error" title={error} action={<Button onClick={load}>重试</Button>}/>;
 if(!lesson)return <Empty description="学习路线暂未准备好"/>;
 if(!hydrated)return <div className="personal-loading"><Spin/></div>;
 const selectedRun=runs.find(row=>row.id===draft.run_id),eligible=covers(lesson,selectedRun),finished=lessons.filter(item=>item.completed).length;
 const step=!draft.evidence.trim()?0:lesson.suite&&!draft.run_id?1:!lesson.note_available?2:3;
 const suggestion=!draft.evidence.trim()?'先运行示例，写下你改了什么、实际输出与观察结果。':lesson.suite&&!draft.run_id?'进入本章对应测试工程，带回一条自己的真实执行记录。':draft.status==='reading'?'选择学习状态并保存。基础章节使用“已练习”，参考工程通过对应检查后可选择“已验证”。':!lesson.note_available?'把心得与执行摘要整理为关联笔记，形成可回看的记录。':lesson.completed?'本章记录已完成，可以回看笔记或继续下一章。':'当前记录仍缺少本章验证条件，请核对执行覆盖和学习状态。';
 return <div className="learning-route">
  <aside className="learning-route-nav"><span className="personal-kicker">从理解到验证</span><h2>Python · 测试实践</h2><p>自由查看，不用为了解锁而赶进度。</p><Progress percent={Math.round(finished/lessons.length*100)} size="small"/><p>已归档完成 {finished} / {lessons.length} 章</p><Button className="learning-outline-toggle" aria-expanded={outlineOpen} onClick={()=>setOutlineOpen(value=>!value)}>{outlineOpen?'收起章节目录':'展开章节目录'}</Button><div className={'learning-chapter-list'+(outlineOpen?' is-open':'')}>{lessons.map(item=><button key={item.id} disabled={busy} className={lesson.id===item.id?'active':''} onClick={()=>{setOutlineOpen(false);onNavigate('learning_route',{lesson:item.id});}}><small>{item.stage}</small><strong>{item.title}</strong><span>{item.completed?'已完成并归档':item.progress?.status==='verified'?'参考验证记录':item.progress?.status==='practiced'?'已练习':item.progress?'学习中':'未开始'}</span></button>)}</div></aside>
  <div className="learning-route-body">
   <Card className="learning-next-step"><Steps size="small" current={step} items={[{title:'理解与改写'},{title:'运行与验证'},{title:'整理心得'},{title:'笔记归档'}]}/><h3>下一步</h3><p>{suggestion}</p>{lesson.completed&&lesson.next_lesson_id&&<Button type="primary" onClick={()=>onNavigate('learning_route',{lesson:lesson.next_lesson_id})}>继续下一章</Button>}</Card>
   <Card><Tag>{lesson.stage}</Tag><h2>{lesson.title}</h2><p className="learning-goal">{lesson.goal}</p><p>{lesson.why}</p><MarkdownView text={'```'+(lesson.language||'python')+'\n'+lesson.example+'\n```'}/>{lesson.language==='bash'&&<p className="personal-footnote">命令在下载的参考工程目录中执行，先按 README 配置环境。也可直接使用平台的固定参考验证；不会执行你的本机改写代码。</p>}<h3>动手练习</h3><ol>{lesson.steps?.map(text=><li key={text}>{text}</li>)}</ol><p>{lesson.exercise}</p><p><strong>需要留下：</strong>{lesson.deliverable}</p><Collapse items={[{key:'answer',label:'查看参考答案',children:<p>{lesson.answer}</p>}]}/><Space wrap className="learning-actions">{practiceAllowed&&<Button disabled={busy} onClick={()=>onNavigate('practice_lab',{lesson:lesson.id,suite:lesson.suite||'api'})}>{lesson.suite?'进入本章参考验证':'打开订单库存练习'}</Button>}<Button disabled={busy} onClick={archive}>{draft.note_id?'另存学习笔记':'整理成笔记'}</Button></Space><p className="personal-footnote">{lesson.verification_scope}</p></Card>
   <Card title="留下练习证据">{draftError&&<Alert type="warning" title="本机草稿不可用，请先保存再切换页面"/>}{runError&&<Alert type="warning" title="执行记录暂不可用" description={runError} action={<Button onClick={load}>重新读取</Button>}/>}
    {lesson.suite&&<div className="learning-verification"><h3>本章参考检查目标</h3><ul>{lesson.checks?.length?lesson.checks.map(check=><li key={check.name}>{check.title}</li>):<li>有效请求数大于0，且失败数为0；解读与对比由你记录。</li>}</ul>{selectedRun&&<Alert type={eligible?'success':selectedRun.status==='passed'?'warning':'info'} title={`已关联执行 #${selectedRun.id} · ${selectedRun.status}`} description={eligible?'本章参考检查已覆盖。请记录自己的观察，再选择学习状态保存。':'可作为排错记录保留；尚不能据此标记本章已验证。'}/>}</div>}
    {draft.note_id&&(draft.note_id===lesson.progress?.note_id?!lesson.note_available:!notes.some(row=>row.id===draft.note_id))&&<Alert type="warning" title="关联笔记不可用，请恢复原笔记或清除关联后重新整理" action={<Button onClick={()=>patch({note_id:null})}>清除失效关联</Button>}/>}
    <Input.TextArea aria-label="学习练习记录" disabled={busy} value={draft.evidence} onChange={event=>patch({evidence:event.target.value})} rows={5} maxLength={10000} placeholder="写下你运行了什么、修改了什么、实际输出与原因判断。参考工程通过不代表本地代码已经通过。"/>
    <div className="learning-evidence-options"><label>完成状态<Select disabled={busy} value={draft.status} onChange={value=>patch({status:value})} options={[{value:'reading',label:'学习中'},{value:'practiced',label:'已练习（自己确认）'},...(lesson.suite?[{value:'verified',label:'已验证（关联通过的测试）'}]:[])]}/></label><label>关联笔记<Select disabled={busy} allowClear value={draft.note_id||undefined} onChange={value=>patch({note_id:value||null})} options={notes.map(row=>({value:row.id,label:row.title}))}/></label>{lesson.suite&&<label>关联执行记录<Select disabled={busy} allowClear value={draft.run_id||undefined} onChange={value=>patch({run_id:value||null})} options={runs.filter(row=>row.suite===lesson.suite&&!['queued','running'].includes(row.status)).map(row=>({value:row.id,label:'#'+row.id+' · '+row.status}))}/></label>}</div>
    <Space wrap><Button type="primary" loading={busy} onClick={()=>persist(false)}>保存学习记录</Button><Button loading={busy} onClick={archive}>{draft.note_id?'另存为新笔记':'保存心得并生成笔记'}</Button>{draft.note_id&&<Button disabled={busy} onClick={()=>onNavigate('knowledge',{record:draft.note_id})}>打开关联笔记</Button>}</Space><p className="personal-footnote">{dirty?'修改尚未保存到服务器。':lesson.progress?'已保存的章节记录。':'本章尚未保存。'}草稿按账号与章节保留在本机；生成笔记不会覆盖旧笔记。</p>
   </Card>
  </div>
 </div>;
}
