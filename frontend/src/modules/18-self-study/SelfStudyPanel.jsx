import React, { useEffect, useState, useMemo, useRef } from 'react';
import { Button, Checkbox, Modal, Progress, Radio, Tag, Select, Input, Alert, message } from 'antd';
import bank from './questionBank.json';
import { createPaper, gradePaper, POINTS } from './examEngine.js';
import { validateSession, mayEditSession } from './sessionState.js';
import { newAttemptId, answerRevealed, hasWrittenAnswer, updateWrittenAnswer, manualScore, applyAssessment } from './writtenState.js';
import './self-study.css';

const sources = [...new Set(bank.questions.map(q => q.source))].sort((a, b) => a.localeCompare(b, 'zh-CN', { numeric: true }));
const labels = { choice: '单项选择题', short: '简答题', material: '材料题' };
const byId = new Map(bank.questions.map(q => [q.id, q]));
function restore(key) {
  let raw;
  try {
    raw = localStorage.getItem(key);
    const value = JSON.parse(raw);
    const valid = validateSession(value, bank);
    if (valid) return { ...valid, attemptId: valid.attemptId || newAttemptId() };
  } catch { /* Retain malformed JSON below as well as version mismatches. */ }
  if (raw) {
    try {
      localStorage.setItem(`${key}:recovery`, raw);
      sessionStorage.setItem(`${key}:notice`, '原进度格式或题库版本已变化，已保留恢复副本，请重新组卷。');
    } catch { /* Storage may be unavailable; in-memory practice still works. */ }
  }
  return null;
}

export function SelfStudyPanel({ userId, client }) {
  const storageKey = `cling:self-study:${userId}:v1`;
  const [session, setSession] = useState(() => restore(storageKey));
  const legacyKey = 'cling:self-study:undefined:v1';
  const [hasLegacy, setHasLegacy] = useState(() => {
    try { const owner = localStorage.getItem(`${legacyKey}:owner`); return userId != null && Boolean(localStorage.getItem(legacyKey)) && (!owner || owner === String(userId)); }
    catch { return false; }
  });
  function importLegacy() {
    Modal.confirm({ title: '导入本机旧进度？', content: '旧版本进度未区分账号。请确认这是你本人的作答，确认后复制到当前账号；原始副本仍会保留。', okText: '确认是我的进度', cancelText: '取消', onOk: () => {
      try {
        const owner = localStorage.getItem(`${legacyKey}:owner`);
        if (owner && owner !== String(userId)) { setHasLegacy(false); message.warning('旧进度已归属其他账号'); return; }
        const old = restore(legacyKey);
        if (!old) { message.warning('旧进度不兼容，已保留恢复副本'); return; }
        localStorage.setItem(storageKey, JSON.stringify(old));
        localStorage.setItem(`${legacyKey}:owner`, String(userId));
        setSession(old);setHasLegacy(false);
      } catch { message.error('浏览器存储不可用，未导入，原始进度仍保留'); }
    } });
  }
  const [aiStatus, setAiStatus] = useState({ enabled: false, loading: true });
  const [grading, setGrading] = useState(null);
  const [gradeError, setGradeError] = useState(null);
  const alive = useRef(true);
  const activeRequest = useRef(null);
  useEffect(() => {
    alive.current = true;
    let current = true;
    if (!client) setAiStatus({ enabled: false, loading: false });
    else client.get('/v1/self-study/grading-status').then(result => {
      if (current) setAiStatus({ ...result, loading: false });
    }).catch(() => { if (current) setAiStatus({ enabled: false, loading: false, unavailable: true }); });
    return () => { current = false; alive.current = false; activeRequest.current = null; };
  }, [client, userId]);
  const [selected, setSelected] = useState(sources);
  const [mode, setMode] = useState('mixed');
  const [storageError, setStorageError] = useState(false);
  const [recoveryNotice, setRecoveryNotice] = useState(() => {
    try { return sessionStorage.getItem(`${storageKey}:notice`); } catch { return ''; }
  });
  useEffect(() => {
    try { if (session) localStorage.setItem(storageKey, JSON.stringify(session)); else localStorage.removeItem(storageKey); }
    catch { setStorageError(true); }
  }, [session, storageKey]);
  const availablePaper = useMemo(() => createPaper(bank.questions, selected, mode), [selected, mode]);
  const availableMax = gradePaper(availablePaper).max;
  function start() {
    const paper = createPaper(bank.questions, selected, mode);
    if (!paper.length) { message.warning('所选来源没有此题型，请调整来源或练习方式'); return; }
    setRecoveryNotice('');
    try { sessionStorage.removeItem(`${storageKey}:notice`); } catch { /* In-memory practice remains usable. */ }
    setGradeError(null);
    setSession({ attemptId: newAttemptId(), version: bank.version, ids: paper.map(q => q.id), index: 0, responses: {}, finished: false });
  }
  function restart() {
    Modal.confirm({ title: '重新组卷？', content: '本轮答题进度将被新的随机试卷替换。', okText: '重新组卷', cancelText: '继续本轮', onOk: () => setSession(null) });
  }
  const questions = session?.ids.map(id => byId.get(id)) || [];
  const q = questions[session?.index];
  const response = q && session.responses[q.id];
  const done = questions.filter(item => item.type === 'choice' ? session.responses[item.id] : hasWrittenAnswer(session, item.id)).length;
  const choices = questions.filter(item => item.type === 'choice');
  const correct = choices.filter(item => session.responses[item.id] === item.answer).length;
  const grade = session?.finished && session.gradeSnapshot ? session.gradeSnapshot : gradePaper(questions, session?.responses, session?.selfScores);
  function respond(value) {
    if (!mayEditSession(session)) return;
    setSession(prev => prev.responses[q.id] ? prev : { ...prev, responses: { ...prev.responses, [q.id]: value } });
  }
  const assessment = q && session?.aiAssessments?.[q.id];
  const written = q && (session?.writtenAnswers?.[q.id] || '');
  const scoreSource = q && session?.scoreSources?.[q.id];
  const revealed = q && answerRevealed(session, q.id);
  async function assessAnswer() {
    if (!mayEditSession(session) || !hasWrittenAnswer(session, q.id) || activeRequest.current) return;
    const question = q;
    const ticket = { attemptId: session.attemptId, answer: written, revision: session.scoreRevisions?.[q.id] || 0 };
    const requestId = newAttemptId(); activeRequest.current = requestId;
    setGrading(q.id); setGradeError(null);
    setSession(prev => ({ ...prev, responses: { ...prev.responses, [question.id]: 'answered' } }));
    try {
      const result = await client.post('/v1/self-study/grade', { question_id: question.id, bank_version: bank.version, answer: written.trim() });
      if (!alive.current || activeRequest.current !== requestId) return;
      // Validate outside the state updater so a malformed response cannot crash React.
      applyAssessment(session, ticket, result, question);
      setSession(prev => applyAssessment(prev, ticket, result, question));
    } catch (error) {
      if (alive.current && activeRequest.current === requestId) setGradeError({ id: question.id, attemptId: ticket.attemptId, answer: ticket.answer, text: error.message || 'AI 评分失败，请重试或手动评分' });
    } finally {
      if (alive.current && activeRequest.current === requestId) { activeRequest.current = null; setGrading(null); }
    }
  }
  function move(index) { setSession(prev => ({ ...prev, index })); }
  function finish() {
    if (activeRequest.current) { message.info('AI 正在评分，请稍候再结束本轮；答题内容已在本地保存。'); return; }
    const complete = () => setSession(prev => ({ ...prev, finished: true, reviewing: false, gradeSnapshot: gradePaper(questions, prev.responses, prev.selfScores) }));
    if (questions.filter(item => item.type === 'choice' && !session.responses[item.id]).length || grade.pending) Modal.confirm({ title: '确认结束本轮？', content: `还有 ${questions.length - done} 题未完成，${grade.pending} 道问答题未评分。未答选择题计 0 分；未评分问答题暂计 0 分，可回看补评。`, okText: '结束并查看结果', cancelText: '继续答题', onOk: complete });
    else complete();
  }
  return <div className="self-study">
    <header className="exam-hero"><div><span className="exam-eyebrow">STUDY A LITTLE, GROW EVERY DAY</span><h1>自考题库 <span>✦</span></h1><p>{bank.title} · 课程代码 {bank.course}</p></div><div className="exam-badge">每天一点<br /><strong>离目标更近</strong></div></header>
    {storageError && <p role="alert">当前浏览器无法保存进度，请在关闭页面前完成本轮练习。</p>}
    {!session && hasLegacy && <Alert type="info" title="发现本机旧版答题进度" description="旧进度仍保留，确认属于本人后可导入当前账号。" action={<Button onClick={importLegacy}>导入旧进度</Button>} />}
    {recoveryNotice && <p role="alert">{recoveryNotice}</p>}
    {!session ? <section className="exam-card exam-setup">
      <div className="exam-stats"><div><strong>{bank.questions.length}</strong><span>题库总量</span></div><div><strong>{bank.questions.filter(q => q.type === "choice").length}</strong><span>选择题</span></div><div><strong>{bank.questions.filter(q => q.type !== "choice").length}</strong><span>问答与材料题</span></div><div><strong>{sources.length}</strong><span>组来源</span></div></div>
      <h2>今天，从一套新题开始</h2><p>选择题选完立即看答案，核对后再点下一题。简答题和材料题可输入答案，使用 AI 参考评分或手动评分，也可随时查看参考答案。</p>
      <p>默认押题优先：套卷通常抽取 18 道押题选择、4 道押题简答、1 道押题论述，其余取自历年题。取消勾选押题来源即可恢复历年题练习。</p><p className="exam-muted">押题是复习参考，不代表实际命题或命中保证。资料提纲已改编为练习题；部分论述题仅有答题提示。仅选押题来源时会全部从该来源抽题。</p><h3>题目来源</h3><Checkbox.Group options={sources} value={selected} onChange={setSelected} />
      <p>原卷计分：选择题 25 × 2 分，简答题 5 × 7 分，材料题 1 × 15 分，总分 100 分。选择专项和问答专项各 50 分。选择题自动判分，简答与材料题支持 DeepSeek 参考评分，之后可手动改分。</p>
      <h3>练习方式</h3><Radio.Group value={mode} onChange={e => setMode(e.target.value)}><Radio.Button value="mixed">随机套卷 · 31 题</Radio.Button><Radio.Button value="choice">选择专项 · 25 题</Radio.Button><Radio.Button value="written">问答专项 · 6 题</Radio.Button></Radio.Group>
      <p className="exam-muted">套卷包含 25 道选择、5 道简答、1 道材料题。同卷相同题干不重复；新一轮会重新抽题，不同轮次可能遇到相同题目。</p>
      <p role="status">当前来源实际可抽取 {availablePaper.length} 题，满分 {availableMax} 分。{!availablePaper.length && '没有可用题目，请调整题型或来源。'}</p><Button type="primary" size="large" disabled={!selected.length || !availablePaper.length} onClick={start}>开始随机答题 →</Button>
      <p className="exam-muted">答案依据你提供的文件整理，保留原始参考答案。答题进度保存在当前账号的本浏览器中。</p>
    </section> : (session.finished && !session.reviewing) ? <section className="exam-card">
      <Tag color="purple">本轮练习完成</Tag><h2>每一道题，都是一次积累</h2>
      <p>已完成 {done} / {questions.length} 题</p><h3>选择题答对 {correct} / {choices.length} 题</h3>
      <div className="exam-answer"><h2>{grade.pending ? '暂计得分' : '本轮总分'}：{grade.total} / {grade.max} 分</h2><p>选择题自动判分 · 简答与材料题 AI 参考分 / 手动评分</p>{grade.pending > 0 && <p>还有 {grade.pending} 道问答题未评分，暂计 0 分。请回看题目补评分数。</p>}</div>
      <div className="exam-stats">{Object.entries(labels).map(([type, label]) => { const rows = grade.rows.filter(r => r.type === type); return rows.length > 0 && <div key={type}><strong>{rows.reduce((s,r) => s+r.score,0)} / {rows.reduce((s,r) => s+r.max,0)}</strong><span>{label} · {rows.length} 题</span></div>; })}</div>
      <details><summary>查看逐题得分</summary>{grade.rows.map((r, i) => <p key={r.id}>第 {i+1} 题 · {labels[r.type]}：{r.score} / {r.max} 分{r.pending ? '（待评分）' : r.type !== 'choice' ? (session.scoreSources?.[r.id] === 'ai' ? '（AI 参考分）' : '（手动评分）') : ''}</p>)}</details>
      <div className="exam-actions"><Button onClick={() => setSession(prev => ({ ...prev, reviewing: true, index: 0 }))}>回看本轮题目</Button><Button onClick={() => setSession(prev => ({ ...prev, finished: false, reviewing: false, assessmentEditing: true }))}>进入补答 / 补评</Button><Button type="primary" onClick={() => setSession(null)}>再组一套新题</Button></div>
    </section> : <div className="exam-layout"><section className="exam-card">
      <div className="exam-meta">{session.reviewing && <Tag color="blue">只读回看 · 成绩不变</Tag>}<Tag color="purple">{labels[q.type]}</Tag><span>{q.source} · 原题 {q.number}</span><strong>{session.index + 1} / {questions.length}</strong></div>
      <Progress percent={Math.round(done / questions.length * 100)} showInfo={false} strokeColor="#a395d1" />
      <h2 className="exam-prompt">{q.prompt}</h2>{q.priority && <Tag color="orange">高频押题 · {q.type === "choice" ? "考点改编" : "预测练习"}</Tag>}{q.note && <p className="exam-muted">{q.note}</p>}
      <p className="exam-muted">本题 {POINTS[q.type]} 分{q.type === 'choice' ? ' · 答对得 2 分，答错或未答得 0 分' : ' · 可输入答案后 AI 评分，也可手动评分；查看答案不自动得分'}</p>
      {q.type !== 'choice' && <section className="exam-written">
        <label htmlFor="exam-written-answer">我的答案</label>
        <Input.TextArea id="exam-written-answer" aria-label="我的答案" value={written} maxLength={10000} showCount
          autoSize={{ minRows: 7, maxRows: 18 }} disabled={!mayEditSession(session)}
          placeholder={q.type === 'material' ? '结合题目材料，按小问或要点分别作答…' : '用自己的话分点写出答案…'}
          onChange={e => setSession(prev => updateWrittenAnswer(prev, q.id, e.target.value))} />
        <p className="exam-muted">输入自动保存在当前浏览器。修改答案会清除本题旧评分，需要重新评分。</p>
        <div className="exam-written-actions"><Button type="primary" loading={grading === q.id}
          disabled={!mayEditSession(session) || !written.trim() || Boolean(grading) || !aiStatus.enabled || q.answerKind === 'hint'}
          onClick={assessAnswer}>{assessment ? '重新 AI 评分' : '提交并 AI 评分'}</Button>
          <label htmlFor="exam-self-score">{scoreSource === 'ai' ? 'AI 参考分 / 手动修改：' : '手动评分：'}</label>
          <Select virtual={false} id="exam-self-score" aria-label="本题评分" style={{ width: 155 }}
            disabled={!mayEditSession(session) || grading === q.id || (!written.trim() && response !== 'viewed')}
            placeholder="选择分数" value={session.selfScores?.[q.id]}
            options={Array.from({ length: POINTS[q.type] + 1 }, (_, i) => ({ value: i, label: `${i} / ${POINTS[q.type]} 分` }))}
            onChange={value => setSession(prev => manualScore(prev, q, value))} />
          {scoreSource && <Tag color={scoreSource === 'ai' ? 'purple' : 'blue'}>{scoreSource === 'ai' ? 'AI 参考分' : '手动评分'}</Tag>}
        </div>
        <p className="exam-muted">点击 AI 评分时，仅发送本题题目、参考答案和你的作答给 DeepSeek。评分仅供练习参考，可手动修改，不代表官方考试成绩。</p>
        {q.answerKind === 'hint' ? <Alert type="info" title="本题仅有答题提示，缺少完整评分依据，请手动评分。" /> :
          !aiStatus.loading && !aiStatus.enabled && <Alert type="warning" title={aiStatus.unavailable ? 'AI 服务状态暂不可用，可以先手动评分，答案不会丢失。' : 'DeepSeek 评分尚未配置，可以先作答并手动评分。'} />}
        {gradeError?.id === q.id && gradeError.attemptId === session.attemptId && gradeError.answer === written && <Alert type="error" showIcon title={gradeError.text} />}
        {assessment && <div className="exam-ai-feedback"><h3>DeepSeek 参考点评 <Tag>{assessment.score} / {POINTS[q.type]} 分</Tag></h3>
          {scoreSource === 'manual' && <p>当前采用你的手动评分，以下保留原 AI 点评供参考。</p>}
          <p>{assessment.feedback}</p>
          {assessment.strengths.length > 0 && <><strong>已覆盖的要点</strong><ul>{assessment.strengths.map((item, i) => <li key={i}>{item}</li>)}</ul></>}
          {assessment.missing_points.length > 0 && <><strong>可以补充的要点</strong><ul>{assessment.missing_points.map((item, i) => <li key={i}>{item}</li>)}</ul></>}
          {assessment.referenceViewed && <small>本次评分前已查看参考答案，建议作为对照练习成绩。</small>}
        </div>}
      </section>}
      {q.type === 'choice' ? <div className="exam-options">{q.options.map(option => <button key={option.key} disabled={Boolean(response) || !mayEditSession(session)} className={`exam-option ${response && option.key === q.answer ? 'is-correct' : ''} ${response === option.key && response !== q.answer ? 'is-wrong' : ''}`} onClick={() => respond(option.key)}><b>{option.key}</b><span>{option.text}</span>{response && option.key === q.answer && <span>✓</span>}{response === option.key && response !== q.answer && <span>✕</span>}</button>)}</div> : <Button onClick={() => setSession(prev => ({ ...prev, revealed: { ...prev.revealed, [q.id]: !answerRevealed(prev, q.id) } }))}>{revealed ? '收起参考答案' : '查看参考答案'}</Button>}
      {(q.type === 'choice' ? Boolean(response) : revealed) && <div role="status" className={`exam-answer ${q.type === 'choice' && response !== q.answer ? 'answer-wrong' : ''}`}><h3>{q.type === 'choice' ? response === q.answer ? '回答正确 ✓' : `本次选择 ${response}，再记一次就好` : q.answerKind === 'hint' ? '答题提示（非完整答案）' : '参考答案'}</h3><div>{q.type === 'choice' ? `正确答案：${q.answer}．${q.options.find(o => o.key === q.answer).text}` : q.answer}</div><small>来源：{q.source}试题答案 · 第 {q.number} 题</small></div>}
      <div className="exam-actions"><Button disabled={session.index === 0} onClick={() => move(session.index - 1)}>上一题</Button>{session.index < questions.length - 1 ? <Button type="primary" onClick={() => move(session.index + 1)}>{(q.type === 'choice' ? response : written.trim()) ? '下一题 →' : '暂时跳过 →'}</Button> : <Button type="primary" onClick={session.reviewing ? () => setSession(prev => ({ ...prev, reviewing: false })) : finish}>{session.reviewing ? '返回成绩' : '完成本轮'}</Button>}</div>
    </section><aside className="exam-card exam-map"><h3>答题卡</h3><p className="exam-muted">已完成 {done} / {questions.length}</p><div className="exam-numbers">{questions.map((item, i) => <button key={item.id} aria-label={`跳转第${i+1}题`} aria-current={i === session.index ? 'step' : undefined} className={`${item.type !== 'choice' ? hasWrittenAnswer(session, item.id) ? 'viewed' : '' : session.responses[item.id] ? session.responses[item.id] === item.answer ? 'right' : 'wrong' : ''} ${i === session.index ? 'current' : ''}`} onClick={() => move(i)}>{i+1}</button>)}</div><p className="exam-muted">绿色答对 · 粉色答错 · 紫色已作答（不代表已评分）</p><div className="exam-actions"><Button onClick={session.reviewing ? () => setSession(prev => ({ ...prev, reviewing: false })) : finish}>{session.reviewing ? '返回成绩' : '结束本轮'}</Button><Button onClick={restart}>重新组卷</Button></div></aside></div>}
  </div>;
}
