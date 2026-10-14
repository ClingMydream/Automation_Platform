// Isolated UI fixture: no production API calls or external writes.
import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { App, ConfigProvider } from 'antd';
import 'antd/dist/reset.css';
import { ReportEditor } from '../src/modules/20-work-journal/ReportEditor.jsx';
import '../src/modules/20-work-journal/work-journal.css';
import { SelfStudyPanel } from '../src/modules/18-self-study/SelfStudyPanel.jsx';
import { UiAutomationPage } from '../src/modules/16-ui-automation/UiAutomationPage.jsx';
import { MasteryLearningPanel } from '../src/modules/08-learning/MasteryLearningPanel.jsx';
import { CommandLibraryPanel } from '../src/modules/12-command-library/CommandLibraryPanel.jsx';
import { OnlinePreviewPanel } from '../src/modules/15-online-preview/OnlinePreviewPanel.jsx';

const initialReport = { id: 1, revision: 1, status: 'draft', template_version: 'daily_v2', report_type: 'daily', title: '隔离自测日报', period_start: '2026-10-14', period_end: '2026-10-14', sections: { items: [{ item_id: 'one', content: '自测事项', status: 'in_progress', progress_percent: 60 }], blockers: [], next_plan: [], remarks: '' } };
const progress = { status: 'available', current_step: 0, evidence: {}, timer_status: 'stopped', elapsed_seconds: 0, blockers: [] };
const lesson = { id: 1, title: '自测第一关', stage: { title: '自测课程', icon: '📚' }, outcome: '理解请求', progress, gates: {}, content: { why: '测试说明', mental_model: '输入处理输出', journey: [], annotated_code: 'print(1)', prediction: '输出1', follow_steps: ['运行代码'], rewrite_task: '修改输出', exercise: { prompt: '改写', hint: '尝试' }, quiz: [] } };
window.smoke = { failSave: false, puts: 0, completes: 0, runReads: 0, saved: null };
function Harness() {
  const [kind, setKind] = useState('report');
  const [report, setReport] = useState(initialReport);
  const client = {
    get: async path => {
      if (path.includes('/online-preview/status')) return { building: false, result: 'SUCCESS', branch: 'dev-20260811-1.9.1', commit_sha: 'abcdefgh' };
      if (path.includes('/online-preview/revision')) return { sha: 'abcdefgh', committed_at: '2026-10-14T08:00:00Z', author: '测试', subject: '隔离测试' };
      if (path.includes('/online-preview/comparison')) {
        const branch = new URL(path, location.origin).searchParams.get('branch');
        await new Promise(resolve => setTimeout(resolve, branch === 'feature-smoke' ? 50 : 1200));
        return { matches: true, message: `版本:${branch}`, remote: { sha: 'abcdefgh' }, deployed: { sha: 'abcdefgh', branch } };
      }
      if (path.includes('/overview') && path.includes('mastery')) return { current_lesson_id: 1, mastered: 0, total: 2, total_seconds: 0, stages: [{ id: 1, title: '自测课程', lessons: [{ ...lesson }, { ...lesson, id: 2, title: '自测第二关' }] }] };
      if (path.includes('/mastery/lessons/')) return { ...lesson, id: Number(path.split('/').at(-1)), title: path.endsWith('/2') ? '自测第二关' : '自测第一关' };
      if (path.includes('/ui-automation/overview')) return { cases: [{ id: 1, name: '后续步骤失败用例', feature_id: 1, steps: [], enabled: true }], features: [{ id: 1, name: '发帖' }], requirements: [], runs: [{ id: 1, status: 'failed' }] };
      if (path.includes('/ui-automation/runs/')) { window.smoke.runReads++; return { id: 1, status: 'failed', case_ids: [1], result_summary: { timeline: [{ case_id: 1, status: 'passed', name: '打开首页' }, { case_id: 1, status: 'failed', name: '发布失败' }] }, artifacts: [] }; }
      if (path.includes('/data-sets')) return [];
      if (path.includes('/branches')) return ['dev-20260811-1.9.1', 'feature-smoke'];
      if (path.includes('command-library/categories')) return ['Linux', '自定义分类'];
      if (path.includes('command-library')) return [{ id: 1, title: '测试命令', category: 'Linux', command: 'echo demo', description: '隔离样例', tags: [], is_builtin: true }];
      return [];
    },
    put: async (path, payload) => {
      window.smoke.puts++;
      await new Promise(resolve => setTimeout(resolve, 1000));
      if (window.smoke.failSave) throw new Error('模拟保存失败');
      if (path.includes('/mastery/')) return { ...lesson, progress: { ...progress, evidence: payload } };
      const next = { ...report, title: payload.title, sections: payload.sections, revision: payload.revision + 1 };
      window.smoke.saved = next;
      return next;
    },
    post: async () => { window.smoke.completes++; return { ...report, revision: report.revision + 1, status: 'completed' }; },
    download: async () => ({ blob: new Blob(['测试正文']), filename: 'test.md' }),
  };
  return <App><div style={{ padding: 12 }}><label>自测模块 <select aria-label="自测模块" value={kind} onChange={event => setKind(event.target.value)}><option value="report">工作手记</option><option value="exam">自考题库</option><option value="ui">UI自动化</option><option value="learning">学习空间</option><option value="commands">命令手册</option><option value="preview">在线预览</option></select></label>
    {kind === 'report' && <div className="work-journal"><ReportEditor key={report.id} client={client} report={report} onSaved={setReport} /></div>}
    {kind === 'exam' && <SelfStudyPanel userId="isolated-smoke" />}
    {kind === 'ui' && <UiAutomationPage client={client} />}
    {kind === 'learning' && <MasteryLearningPanel client={client} />}
    {kind === 'commands' && <CommandLibraryPanel client={client} />}
    {kind === 'preview' && <OnlinePreviewPanel client={client} />}
  </div></App>;
}
createRoot(document.getElementById('root')).render(<ConfigProvider><Harness /></ConfigProvider>);
