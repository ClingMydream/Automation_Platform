import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert, Button, Card, Checkbox, Col, Collapse, Drawer, Empty, Input, List, Modal, Progress, Radio,
  Row, Space, Steps, Tag, Typography, message,
} from 'antd';
import {
  CheckCircleFilled, ClockCircleOutlined, DeleteOutlined, FileTextOutlined, LockOutlined, MenuFoldOutlined, MenuUnfoldOutlined, PauseCircleOutlined,
  PlayCircleOutlined, PlusOutlined, RedoOutlined, SaveOutlined, StopOutlined,
} from '@ant-design/icons';
import './mastery-learning.css';

const { Paragraph, Text, Title } = Typography;
const API = '/v1/learning/mastery';
const LEARNING_PHASES = [
  { title: '理解原理', description: '为什么、流程与逐行示例', progressStep: 0 },
  { title: '动手实践', description: '跟写、改写与独立小题', progressStep: 4 },
  { title: '掌握验收', description: '理解问答、证据与复盘', progressStep: 7 },
];
const PHASE_STEP_GROUPS = [[0, 1, 2, 3], [4, 5, 6], [7, 8]];
const EMPTY_EVIDENCE = { run_confirmed: false, run_output: '', modified_code: '', exercise_answer: '', quiz_answers: [], explanation: '' };

function phaseFromProgress(step = 0) {
  if (step >= 7) return 2;
  if (step >= 4) return 1;
  return 0;
}

function duration(seconds = 0) {
  const minutes = Math.floor(seconds / 60);
  return `${Math.floor(minutes / 60)}小时 ${minutes % 60}分钟`;
}

function statusMeta(status) {
  if (status === 'mastered') return { label: '已掌握', color: 'green', icon: <CheckCircleFilled /> };
  if (status === 'in_progress') return { label: '学习中', color: 'blue', icon: <PlayCircleOutlined /> };
  if (status === 'available') return { label: '可开始', color: 'purple', icon: <PlayCircleOutlined /> };
  return { label: '未解锁', color: 'default', icon: <LockOutlined /> };
}

function Journey({ rows = [] }) {
  return <div className="request-journey">{rows.map((row, index) => <React.Fragment key={row}><div><span>{index + 1}</span><b>{row}</b></div>{index < rows.length - 1 && <i>→</i>}</React.Fragment>)}</div>;
}

export function MasteryLearningPanel({ client, isAdmin = false }) {
  const [overview, setOverview] = useState(null);
  const [lesson, setLesson] = useState(null);
  const [lessonId, setLessonId] = useState(null);
  const [step, setStep] = useState(0);
  const [evidence, setEvidence] = useState(EMPTY_EVIDENCE);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveState, setSaveState] = useState('已保存');
  const [blocker, setBlocker] = useState('');
  const [resetOpen, setResetOpen] = useState(false);
  const [resetText, setResetText] = useState('');
  const [timer, setTimer] = useState({ timer_status: 'stopped', elapsed_seconds: 0 });
  const [notesOpen, setNotesOpen] = useState(false);
  const [notes, setNotes] = useState([]);
  const [selectedNote, setSelectedNote] = useState(null);
  const [notesListCollapsed, setNotesListCollapsed] = useState(false);
  const hydrated = useRef(false);
  const saveTimer = useRef(null);

  async function loadOverview(preferredLessonId) {
    const data = await client.get(`${API}/overview`);
    setOverview(data);
    const target = preferredLessonId || lessonId || data.current_lesson_id;
    await openLesson(target, false);
  }

  async function openNotes() {
    setNotesOpen(true);
    try {
      const rows = await client.get('/v1/learning/notes');
      setNotes(rows);
      setSelectedNote((current) => current || rows[0] || null);
    } catch (error) { message.error(error.message); }
  }

  function editNote(patch) {
    setSelectedNote((current) => current ? { ...current, ...patch } : current);
  }

  async function createNote() {
    try {
      const created = await client.post('/v1/learning/notes', { title: '未命名笔记', content_markdown: '', tags: [], is_pinned: false });
      setNotes((rows) => [created, ...rows]); setSelectedNote(created);
    } catch (error) { message.error(error.message); }
  }

  async function saveSelectedNote() {
    if (!selectedNote) return;
    try {
      const saved = await client.put(`/v1/learning/notes/${selectedNote.id}`, {
        folder_id: selectedNote.folder_id, linked_task_id: selectedNote.linked_task_id,
        title: selectedNote.title.trim() || '未命名笔记', content_markdown: selectedNote.content_markdown,
        tags: selectedNote.tags || [], is_pinned: selectedNote.is_pinned || false,
      });
      setNotes((rows) => rows.map((row) => row.id === saved.id ? saved : row)); setSelectedNote(saved); message.success('笔记已保存');
    } catch (error) { message.error(error.message); }
  }

  function deleteSelectedNote() {
    if (!selectedNote) return;
    Modal.confirm({ title: `删除笔记「${selectedNote.title}」？`, content: '删除后可在回收站恢复。', okText: '删除', okButtonProps: { danger: true }, onOk: async () => {
      try {
        await client.delete(`/v1/learning/notes/${selectedNote.id}`);
        setNotes((rows) => { const next = rows.filter((row) => row.id !== selectedNote.id); setSelectedNote(next[0] || null); return next; });
        message.success('笔记已移至回收站');
      } catch (error) { message.error(error.message); }
    }});
  }

  async function openLesson(id, saveCurrent = true) {
    if (saveCurrent && lesson && hydrated.current) await saveDraft(false);
    setLoading(true); hydrated.current = false;
    try {
      const data = await client.get(`${API}/lessons/${id}`);
      setLesson(data); setLessonId(id); setStep(phaseFromProgress(data.progress.current_step));
      setEvidence({ ...EMPTY_EVIDENCE, ...(data.progress.evidence || {}) });
      setTimer(data.progress); setSaveState('已保存');
    } catch (error) { message.error(error.message); }
    finally { setLoading(false); window.setTimeout(() => { hydrated.current = true; }, 0); }
  }

  useEffect(() => { loadOverview().catch((error) => message.error(error.message)); return () => clearTimeout(saveTimer.current); }, []);
  useEffect(() => {
    if (timer.timer_status !== 'running') return undefined;
    const interval = window.setInterval(() => setTimer((value) => ({ ...value, elapsed_seconds: value.elapsed_seconds + 1 })), 1000);
    return () => window.clearInterval(interval);
  }, [timer.timer_status]);

  function changeEvidence(patch) {
    setEvidence((value) => ({ ...value, ...patch })); setSaveState('等待保存');
    clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(() => saveDraft(false, patch), 1200);
  }

  async function saveDraft(showMessage = true, immediatePatch = null) {
    if (!lessonId || !hydrated.current) return;
    setSaving(true); setSaveState('保存中…');
    try {
      const payloadEvidence = { ...evidence, ...(immediatePatch || {}) };
      const data = await client.put(`${API}/lessons/${lessonId}/progress`, { ...payloadEvidence, current_step: LEARNING_PHASES[step].progressStep, complete: false });
      setLesson(data); setSaveState('已保存');
      if (showMessage) message.success('学习证据已保存，并已同步到关卡笔记');
    } catch (error) { setSaveState('保存失败'); if (showMessage) message.error(error.message); }
    finally { setSaving(false); }
  }

  async function completeLesson() {
    clearTimeout(saveTimer.current); setSaving(true);
    try {
      const data = await client.put(`${API}/lessons/${lessonId}/progress`, { ...evidence, current_step: 8, complete: true });
      setLesson(data); message.success(data.message); await loadOverview(lessonId);
    } catch (error) { message.warning(error.message); }
    finally { setSaving(false); }
  }

  async function changePhase(nextPhase) {
    clearTimeout(saveTimer.current);
    setSaving(true); setSaveState('保存中…');
    try {
      const data = await client.put(`${API}/lessons/${lessonId}/progress`, {
        ...evidence, current_step: LEARNING_PHASES[nextPhase].progressStep, complete: false,
      });
      setLesson(data); setStep(nextPhase); setSaveState('已保存');
      document.querySelector('.lesson-document')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (error) { setSaveState('保存失败'); message.error(error.message); }
    finally { setSaving(false); }
  }

  async function timerAction(action) {
    try { setTimer(await client.post(`${API}/lessons/${lessonId}/timer`, { action })); }
    catch (error) { message.error(error.message); }
  }

  async function addBlocker() {
    if (blocker.trim().length < 2) return message.warning('请写下具体哪一点不理解');
    const progress = await client.post(`${API}/lessons/${lessonId}/blockers`, { content: blocker.trim() });
    setLesson((value) => ({ ...value, progress })); setBlocker(''); message.success('卡点已记录，可以先停下来复习');
  }

  async function resetLearning() {
    try {
      const result = await client.post(`${API}/reset`, { confirm_text: resetText });
      message.success(result.message); setResetOpen(false); setResetText(''); setLesson(null); setLessonId(null);
      await loadOverview();
    } catch (error) { message.error(error.message); }
  }

  const gates = lesson?.gates || {};
  const gateRows = useMemo(() => [
    ['run', '代码真实运行并保存输出'], ['rewrite', '完成一次有解释的改写'],
    ['exercise', '独立完成当前小题'], ['understanding', '理解题正确且个人解释不少于 20 字'],
  ], [lesson]);
  if (!overview || !lesson) return <Card loading={loading} />;
  const content = lesson.content;
  const quiz = content.quiz || [];

  const stepBody = [
    <div><Tag color="green">先理解问题，再看代码</Tag><Title level={3}>{lesson.title}</Title><Paragraph className="mastery-lead">{content.why}</Paragraph><Alert type="success" showIcon title="本关学完能做到" description={lesson.outcome} /></div>,
    <div><Title level={4}>先建立脑海中的模型</Title><Paragraph className="mastery-lead">{content.mental_model}</Paragraph><Journey rows={content.journey} /><Paragraph type="secondary">你不需要背报文；需要能指出问题发生在旅程的哪一段。</Paragraph></div>,
    <div><Alert type="info" showIcon title="每行都有用途" description="第一遍逐字输入并读注释；不要整段粘贴。看不懂的词先记录卡点。" /><pre className="mastery-code"><code>{content.annotated_code}</code></pre></div>,
    <div><Title level={4}>运行前先猜结果</Title><Paragraph className="mastery-lead">{content.prediction}</Paragraph><Input.TextArea rows={6} value={evidence.prediction || ''} onChange={(event) => changeEvidence({ prediction: event.target.value })} placeholder="我认为会输出……，因为……" /></div>,
    <div><Title level={4}>一次只完成一个动作</Title><ol className="mastery-actions">{content.follow_steps.map((row, index) => <li key={row}><span>{index + 1}</span><div><b>{row}</b><small>完成后对比实际结果；报错时保留完整错误，不要只截最后一行。</small></div></li>)}</ol></div>,
    <div><Alert type="warning" showIcon title="改写不是重新复制" description={content.rewrite_task} /><Input.TextArea className="code-input" rows={14} value={evidence.modified_code} onChange={(event) => changeEvidence({ modified_code: event.target.value })} placeholder="粘贴你亲自修改后的代码或命令，并在注释中说明改了什么" /></div>,
    <div><Title level={4}>不看答案，自己完成</Title><Paragraph className="mastery-lead">{content.exercise.prompt}</Paragraph><Paragraph type="secondary">提示：{content.exercise.hint}</Paragraph><Input.TextArea rows={12} value={evidence.exercise_answer} onChange={(event) => changeEvidence({ exercise_answer: event.target.value })} placeholder="写下代码、命令、排查过程或答案" /></div>,
    <div><Title level={4}>确认你知道为什么</Title>{quiz.map((row, index) => <Card size="small" key={row.question} title={`${index + 1}. ${row.question}`} className="quiz-card"><Radio.Group value={evidence.quiz_answers[index]} onChange={(event) => { const answers = [...evidence.quiz_answers]; answers[index] = event.target.value; changeEvidence({ quiz_answers: answers }); }}><Space direction="vertical">{row.options.map((option, optionIndex) => <Radio value={optionIndex} key={option}>{option}</Radio>)}</Space></Radio.Group>{row.is_correct === false && <Alert style={{ marginTop: 12 }} type="warning" title="这次答案还不正确" description={row.explanation} />}{row.is_correct === true && <Alert style={{ marginTop: 12 }} type="success" title="理解正确" description={row.explanation} />}</Card>)}<Title level={5}>用自己的话解释本关</Title><Input.TextArea rows={6} value={evidence.explanation} onChange={(event) => changeEvidence({ explanation: event.target.value })} placeholder="至少 20 个字：为什么要这样写？输入、处理、输出分别是什么？" showCount maxLength={10000} /></div>,
    <div><Title level={4}>提交真实学习证据</Title><Checkbox checked={evidence.run_confirmed} onChange={(event) => changeEvidence({ run_confirmed: event.target.checked })}>我确认代码由我亲自运行，不是只复制未执行</Checkbox><Input.TextArea style={{ marginTop: 12 }} rows={8} value={evidence.run_output} onChange={(event) => changeEvidence({ run_output: event.target.value })} placeholder="粘贴终端输出、pytest 结果或完整错误信息" /><div className="mastery-gates">{gateRows.map(([key, label]) => <div className={gates[key] ? 'passed' : ''} key={key}>{gates[key] ? <CheckCircleFilled /> : <ClockCircleOutlined />}<span>{label}</span></div>)}</div><Alert type="info" showIcon title="学不懂就停下来记录" description={<Space.Compact style={{ width: '100%' }}><Input value={blocker} onChange={(event) => setBlocker(event.target.value)} placeholder="例如：我不理解 self 为什么每个方法都要写" onPressEnter={addBlocker} /><Button onClick={addBlocker}>记录卡点</Button></Space.Compact>} />{lesson.progress.blockers?.length > 0 && <Collapse style={{ marginTop: 12 }} items={[{ key: 'blockers', label: `我的卡点（${lesson.progress.blockers.length}）`, children: lesson.progress.blockers.map((row) => <Paragraph key={row.created_at}>• {row.content} <Text type="secondary">{row.created_at}</Text></Paragraph>) }]} />}</div>,
  ];

  return <div className="mastery-learning">
    <header className="mastery-header"><div><Text>个人成长 · 零代码基础</Text><Title level={2}>🐍 Python、HTTP 与接口自动化</Title><Paragraph>{overview.principle}</Paragraph></div><Space wrap><Button icon={<FileTextOutlined />} onClick={openNotes}>查看关卡笔记</Button><Tag color="blue">已掌握 {overview.mastered}/{overview.total}</Tag><Tag>{duration(overview.total_seconds)}</Tag>{isAdmin && <Button danger icon={<RedoOutlined />} onClick={() => setResetOpen(true)}>备份并彻底重置</Button>}</Space></header>
    <Progress percent={Math.round(overview.mastered / overview.total * 100)} showInfo={false} />
    <div className="mastery-shell">
      <aside className="mastery-route"><div className="route-title"><b>能力路线</b><Text type="secondary">可回到已解锁关卡复习</Text></div>{overview.stages.map((stage) => <section key={stage.id}><div className="stage-title"><span>{stage.icon}</span><div><b>{stage.title}</b><small>{stage.objective}</small></div></div>{stage.lessons.map((item) => { const meta = statusMeta(item.progress.status); return <button key={item.id} disabled={item.progress.status === 'locked'} className={lessonId === item.id ? 'active' : ''} onClick={() => openLesson(item.id)}><span>{meta.icon}</span><div><b>{item.title}</b><small>{meta.label}</small></div></button>; })}</section>)}</aside>
      <main className="mastery-lesson">
        <Card className="lesson-top"><Row gutter={[16, 16]} align="middle"><Col flex="auto"><Space wrap><Tag color="purple">{lesson.stage.icon} {lesson.stage.title}</Tag><Tag>{lesson.estimated_minutes} 分钟建议</Tag><Text type="secondary">{saveState}</Text></Space><Title level={2}>{lesson.title}</Title><Paragraph>{lesson.outcome}</Paragraph></Col><Col><Space direction="vertical"><Text strong>本关计时：{duration(timer.elapsed_seconds)}</Text><Space><Button icon={<PlayCircleOutlined />} disabled={timer.timer_status === 'running'} onClick={() => timerAction('start')}>开始</Button><Button icon={<PauseCircleOutlined />} disabled={timer.timer_status !== 'running'} onClick={() => timerAction('pause')}>暂停</Button><Button icon={<StopOutlined />} onClick={() => timerAction('stop')}>结束</Button></Space></Space></Col></Row></Card>
        <div className="lesson-workbench document-workbench"><Steps className="mastery-phase-nav" current={step} responsive items={LEARNING_PHASES.map((phase) => ({ title: phase.title, description: phase.description }))} onChange={changePhase} /><Card loading={loading} className="lesson-content lesson-document"><article className="learning-document">{PHASE_STEP_GROUPS[step].map((contentIndex) => <section key={contentIndex}>{stepBody[contentIndex]}</section>)}</article><div className="lesson-nav"><Button disabled={step === 0} onClick={() => changePhase(step - 1)}>上一阶段</Button><Space wrap><Button icon={<SaveOutlined />} loading={saving} onClick={() => saveDraft(true)}>保存当前内容</Button>{step < LEARNING_PHASES.length - 1 ? <Button type="primary" loading={saving} onClick={() => changePhase(step + 1)}>进入下一阶段</Button> : <Button type="primary" loading={saving} onClick={completeLesson}>完成本关并解锁下一关</Button>}</Space></div></Card></div>
      </main>
    </div>
    <Drawer title="📒 关卡笔记" open={notesOpen} onClose={() => setNotesOpen(false)} width={760} extra={<Space><Button icon={notesListCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} onClick={() => setNotesListCollapsed((value) => !value)}>{notesListCollapsed ? '展开目录' : '收起目录'}</Button><Button type="primary" icon={<PlusOutlined />} onClick={createNote}>新建笔记</Button></Space>}>
      <Paragraph type="secondary">每次保存学习内容后，系统都会自动同步一篇关卡笔记，也可在这里新建、编辑或删除。</Paragraph>
      <div className={`mastery-notes-drawer ${notesListCollapsed ? 'notes-list-collapsed' : ''}`}><List className="mastery-note-list" dataSource={notes} locale={{ emptyText: <Empty description="还没有笔记" /> }} renderItem={(item) => <List.Item className={selectedNote?.id === item.id ? 'selected' : ''} onClick={() => setSelectedNote(item)}><List.Item.Meta title={item.title} description={(item.content_markdown || '空白笔记').replace(/\n/g, ' ').slice(0, 58)} /></List.Item>} /><section className="mastery-note-content">{selectedNote ? <><Space className="mastery-note-actions"><Button type="primary" icon={<SaveOutlined />} onClick={saveSelectedNote}>保存</Button><Button danger icon={<DeleteOutlined />} onClick={deleteSelectedNote}>删除</Button></Space><Input className="mastery-note-title" value={selectedNote.title} onChange={(event) => editNote({ title: event.target.value })} placeholder="笔记标题" /><Input.TextArea value={selectedNote.content_markdown} onChange={(event) => editNote({ content_markdown: event.target.value })} placeholder="记录你的学习笔记" autoSize={{ minRows: 18 }} /></> : <Empty description="选择或新建一篇笔记" />}</section></div>
    </Drawer>
    <Modal open={resetOpen} title="备份并彻底重置学习空间" okText="确认备份并重置" okButtonProps={{ danger: true, disabled: resetText !== '彻底重置学习空间' }} onOk={resetLearning} onCancel={() => { setResetOpen(false); setResetText(''); }}><Alert type="warning" showIcon title="旧课程、进度、笔记和附件会先备份，再从页面清空。其他平台模块不受影响。" /><Paragraph style={{ marginTop: 16 }}>请输入：<Text code>彻底重置学习空间</Text></Paragraph><Input value={resetText} onChange={(event) => setResetText(event.target.value)} /></Modal>
  </div>;
}
