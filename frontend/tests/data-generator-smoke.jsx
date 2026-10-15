import React from 'react';
import { createRoot } from 'react-dom/client';
import { App, ConfigProvider } from 'antd';
import 'antd/dist/reset.css';
import { DataGeneratorPanel } from '../src/modules/05-data-generator/DataGeneratorPanel.jsx';
const saved = [];
const client = {
 get: async path => path.includes('?') ? { items: [...saved], total: saved.length } : structuredClone(saved.find(r => r.id === Number(path.split('/').pop()))),
 post: async (path, body) => {
  if(path.endsWith('/batches')) { const item = {...structuredClone(body), id: saved.length + 1}; saved.push(item); return item; }
  return { rows: Array.from({length: body.count}, () => ({phone: `TEST-PHONE-${crypto.randomUUID().replaceAll('-', '').toUpperCase()}`, remark: '', source: 'synthetic', sms_capable: false})), warning: '虚拟测试号码，不是真实手机号' };
 },
 put: async (path, body) => { const item = {...structuredClone(body), revision: body.revision+1}; saved.splice(saved.findIndex(r=>r.id===body.id),1,item); return item; },
 delete: async path => { saved.splice(saved.findIndex(r=>r.id===Number(path.split('/').pop().split('?')[0])),1); return {deleted:true}; },
};
window.generatorSmoke = saved;
createRoot(document.getElementById('root')).render(<ConfigProvider><App><DataGeneratorPanel client={client}/></App></ConfigProvider>);
