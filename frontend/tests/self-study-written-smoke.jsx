// Isolated fixture: AI responses are simulated; no external data is sent.
import React from 'react';
import { createRoot } from 'react-dom/client';
import { ConfigProvider, App } from 'antd';
import 'antd/dist/reset.css';
import { SelfStudyPanel } from '../src/modules/18-self-study/SelfStudyPanel.jsx';
import bank from '../src/modules/18-self-study/questionBank.json';
const short=bank.questions.find(q=>q.type==='short' && q.answerKind!=='hint');
const material=bank.questions.find(q=>q.type==='material' && q.answerKind!=='hint');
const hint=bank.questions.find(q=>q.answerKind==='hint');
const key='cling:self-study:written-smoke:v1';
if(!new URLSearchParams(location.search).has('restore')) localStorage.setItem(key,JSON.stringify({attemptId:'smoke',version:bank.version,ids:[short.id,material.id,hint.id],index:0,responses:{},finished:false}));
window.writtenSmoke={calls:[],fail:false,deferred:false,resolve:null,key};
const client={get:async()=>({enabled:true}),post:async(path,payload)=>{
 window.writtenSmoke.calls.push({path,payload});
 if(window.writtenSmoke.fail)throw new Error('模拟 AI 超时：答案已保留');
 const result={question_id:payload.question_id,max_score:payload.question_id===short.id?7:15,score:payload.question_id===short.id?5:12,feedback:'已覆盖主要概念，建议补充材料分析。',strengths:['核心观点准确'],missing_points:['补充现实材料联系'],source:'ai',provider:'DeepSeek',model:'simulated'};
 if(window.writtenSmoke.deferred)return await new Promise(resolve=>{window.writtenSmoke.resolve=()=>resolve(result);});
 return result;
}};
createRoot(document.getElementById('root')).render(<ConfigProvider><App><SelfStudyPanel userId="written-smoke" client={client}/></App></ConfigProvider>);
