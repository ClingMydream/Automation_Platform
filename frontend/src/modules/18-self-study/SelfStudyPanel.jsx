import React, { useEffect, useState } from 'react';
import { Button, Checkbox, Modal, Progress, Radio, Tag, Select } from 'antd';
import bank from './questionBank.json';
import { createPaper, gradePaper, POINTS } from './examEngine.js';
import './self-study.css';

const sources = [...new Set(bank.questions.map(q => q.source))].sort((a, b) => a.localeCompare(b, 'zh-CN', { numeric: true }));
const labels = { choice: '单项选择题', short: '简答题', material: '材料题' };
const byId = new Map(bank.questions.map(q => [q.id, q]));
function restore(key) {
  try {
    const value = JSON.parse(localStorage.getItem(key));
    if (value?.version !== bank.version || !value.ids?.length || !value.ids.every(id => byId.has(id)) || !value.responses || value.index < 0 || value.index >= value.ids.length) return null;
    return value;
  } catch { return null; }
}

export function SelfStudyPanel({ userId }) {
  const storageKey = `cling:self-study:${userId}:v1`;
  const [session, setSession] = useState(() => restore(storageKey));
  const [selected, setSelected] = useState(sources);
  const [mode, setMode] = useState('mixed');
  const [storageError, setStorageError] = useState(false);
  useEffect(() => {
    try { if (session) localStorage.setItem(storageKey, JSON.stringify(session)); else localStorage.removeItem(storageKey); }
    catch { setStorageError(true); }
  }, [session, storageKey]);
  function start() {
    const paper = createPaper(bank.questions, selected, mode);
    setSession({ version: bank.version, ids: paper.map(q => q.id), index: 0, responses: {}, finished: false });
  }
  function restart() {
    Modal.confirm({ title: '重新组卷？', content: '本轮答题进度将被新的随机试卷替换。', okText: '重新组卷', cancelText: '继续本轮', onOk: () => setSession(null) });
  }
  const questions = session?.ids.map(id => byId.get(id)) || [];
  const q = questions[session?.index];
  const response = q && session.responses[q.id];
  const done = Object.keys(session?.responses || {}).length;
  const choices = questions.filter(item => item.type === 'choice');
  const correct = choices.filter(item => session.responses[item.id] === item.answer).length;
  const grade = gradePaper(questions, session?.responses, session?.selfScores);
  function respond(value) {
    setSession(prev => prev.responses[q.id] ? prev : { ...prev, responses: { ...prev.responses, [q.id]: value } });
  }
  function move(index) { setSession(prev => ({ ...prev, index })); }
  function finish() {
    const complete = () => setSession(prev => ({ ...prev, finished: true }));
    if (done < questions.length || grade.pending) Modal.confirm({ title: '确认结束本轮？', content: `还有 ${questions.length - done} 题未完成，${grade.pending} 道问答题未自评。未答选择题计 0 分；未自评问答题暂计 0 分，可回看补评。`, okText: '结束并查看结果', cancelText: '继续答题', onOk: complete });
    else complete();
  }
  return <div className="self-study">
    <header className="exam-hero"><div><span className="exam-eyebrow">STUDY A LITTLE, GROW EVERY DAY</span><h1>自考题库 <span>✦</span></h1><p>{bank.title} · 课程代码 {bank.course}</p></div><div className="exam-badge">每天一点<br /><strong>离目标更近</strong></div></header>
    {storageError && <p role="alert">当前浏览器无法保存进度，请在关闭页面前完成本轮练习。</p>}
    {!session ? <section className="exam-card exam-setup">
      <div className="exam-stats"><div><strong>{bank.questions.length}</strong><span>题库总量</span></div><div><strong>{bank.questions.filter(q => q.type === "choice").length}</strong><span>选择题</span></div><div><strong>{bank.questions.filter(q => q.type !== "choice").length}</strong><span>问答与材料题</span></div><div><strong>{sources.length}</strong><span>组来源</span></div></div>
      <h2>今天，从一套新题开始</h2><p>选择题选完立即看答案，核对后再点下一题。问答题先回想，点击展开参考答案。</p>
      <p>默认押题优先：套卷通常抽取 18 道押题选择、4 道押题简答、1 道押题论述，其余取自历年题。取消勾选押题来源即可恢复历年题练习。</p><p className="exam-muted">押题是复习参考，不代表实际命题或命中保证。资料提纲已改编为练习题；部分论述题仅有答题提示。仅选押题来源时会全部从该来源抽题。</p><h3>题目来源</h3><Checkbox.Group options={sources} value={selected} onChange={setSelected} />
      <p>原卷计分：选择题 25 × 2 分，简答题 5 × 7 分，材料题 1 × 15 分，总分 100 分。选择专项和问答专项各 50 分。选择题自动判分，问答题对照参考答案自评。</p>
      <h3>练习方式</h3><Radio.Group value={mode} onChange={e => setMode(e.target.value)}><Radio.Button value="mixed">随机套卷 · 31 题</Radio.Button><Radio.Button value="choice">选择专项 · 25 题</Radio.Button><Radio.Button value="written">问答专项 · 6 题</Radio.Button></Radio.Group>
      <p className="exam-muted">套卷包含 25 道选择、5 道简答、1 道材料题。同卷相同题干不重复；新一轮会重新抽题，不同轮次可能遇到相同题目。</p>
      <Button type="primary" size="large" disabled={!selected.length} onClick={start}>开始随机答题 →</Button>
      <p className="exam-muted">答案依据你提供的文件整理，保留原始参考答案。答题进度保存在当前账号的本浏览器中。</p>
    </section> : session.finished ? <section className="exam-card">
      <Tag color="purple">本轮练习完成</Tag><h2>每一道题，都是一次积累</h2>
      <p>已完成 {done} / {questions.length} 题</p><h3>选择题答对 {correct} / {choices.length} 题</h3>
      <div className="exam-answer"><h2>{grade.pending ? '暂计得分' : '本轮总分'}：{grade.total} / {grade.max} 分</h2><p>选择题自动判分 · 简答与材料题自评</p>{grade.pending > 0 && <p>还有 {grade.pending} 道问答题未自评，暂计 0 分。请回看题目补评分数。</p>}</div>
      <div className="exam-stats">{Object.entries(labels).map(([type, label]) => { const rows = grade.rows.filter(r => r.type === type); return rows.length > 0 && <div key={type}><strong>{rows.reduce((s,r) => s+r.score,0)} / {rows.reduce((s,r) => s+r.max,0)}</strong><span>{label} · {rows.length} 题</span></div>; })}</div>
      <details><summary>查看逐题得分</summary>{grade.rows.map((r, i) => <p key={r.id}>第 {i+1} 题 · {labels[r.type]}：{r.score} / {r.max} 分{r.pending ? '（待自评）' : r.type !== 'choice' ? '（自评）' : ''}</p>)}</details>
      <div className="exam-actions"><Button onClick={() => setSession(prev => ({ ...prev, finished: false, index: 0 }))}>回看本轮题目</Button><Button type="primary" onClick={() => setSession(null)}>再组一套新题</Button></div>
    </section> : <div className="exam-layout"><section className="exam-card">
      <div className="exam-meta"><Tag color="purple">{labels[q.type]}</Tag><span>{q.source} · 原题 {q.number}</span><strong>{session.index + 1} / {questions.length}</strong></div>
      <Progress percent={Math.round(done / questions.length * 100)} showInfo={false} strokeColor="#a395d1" />
      <h2 className="exam-prompt">{q.prompt}</h2>{q.priority && <Tag color="orange">高频押题 · {q.type === "choice" ? "考点改编" : "预测练习"}</Tag>}{q.note && <p className="exam-muted">{q.note}</p>}
      <p className="exam-muted">本题 {POINTS[q.type]} 分{q.type === 'choice' ? ' · 答对得 2 分，答错或未答得 0 分' : ' · 对照原卷参考答案自评，查看答案不自动得分'}</p>
      {q.type !== 'choice' && response && <div style={{marginBottom:16}}><label htmlFor="exam-self-score">本题自评分：</label><Select id="exam-self-score" aria-label="本题自评分" style={{width:150}} placeholder="请选择分数" value={session.selfScores?.[q.id]} options={Array.from({length:POINTS[q.type]+1},(_,i)=>({value:i,label:`${i} / ${POINTS[q.type]} 分`}))} onChange={value => setSession(prev => ({...prev,selfScores:{...prev.selfScores,[q.id]:value}}))} /><p className="exam-muted">原答案标明分值时按各要点累加；未标明细则时，请根据答题完整度自评，总分不超过本题分值。此分数为自评成绩。</p></div>}
      {q.type === 'choice' ? <div className="exam-options">{q.options.map(option => <button key={option.key} disabled={Boolean(response)} className={`exam-option ${response && option.key === q.answer ? 'is-correct' : ''} ${response === option.key && response !== q.answer ? 'is-wrong' : ''}`} onClick={() => respond(option.key)}><b>{option.key}</b><span>{option.text}</span>{response && option.key === q.answer && <span>✓</span>}{response === option.key && response !== q.answer && <span>✕</span>}</button>)}</div> : <Button type="primary" onClick={() => { if (!response) respond('viewed'); else setSession(prev => ({ ...prev, hidden: { ...prev.hidden, [q.id]: !prev.hidden?.[q.id] } })); }}>{response && !session.hidden?.[q.id] ? '收起参考答案' : '查看参考答案'}</Button>}
      {response && (q.type === 'choice' || !session.hidden?.[q.id]) && <div role="status" className={`exam-answer ${q.type === 'choice' && response !== q.answer ? 'answer-wrong' : ''}`}><h3>{q.type === 'choice' ? response === q.answer ? '回答正确 ✓' : `本次选择 ${response}，再记一次就好` : q.answerKind === 'hint' ? '答题提示（非完整答案）' : '参考答案'}</h3><div>{q.type === 'choice' ? `正确答案：${q.answer}．${q.options.find(o => o.key === q.answer).text}` : q.answer}</div><small>来源：{q.source}试题答案 · 第 {q.number} 题</small></div>}
      <div className="exam-actions"><Button disabled={session.index === 0} onClick={() => move(session.index - 1)}>上一题</Button>{session.index < questions.length - 1 ? <Button type="primary" onClick={() => move(session.index + 1)}>{response ? '下一题 →' : '暂时跳过 →'}</Button> : <Button type="primary" onClick={finish}>完成本轮</Button>}</div>
    </section><aside className="exam-card exam-map"><h3>答题卡</h3><p className="exam-muted">已完成 {done} / {questions.length}</p><div className="exam-numbers">{questions.map((item, i) => <button key={item.id} aria-label={`跳转第${i+1}题`} aria-current={i === session.index ? 'step' : undefined} className={`${session.responses[item.id] ? item.type !== 'choice' ? 'viewed' : session.responses[item.id] === item.answer ? 'right' : 'wrong' : ''} ${i === session.index ? 'current' : ''}`} onClick={() => move(i)}>{i+1}</button>)}</div><p className="exam-muted">绿色答对 · 粉色答错 · 紫色已看答案</p><div className="exam-actions"><Button onClick={finish}>结束本轮</Button><Button onClick={restart}>重新组卷</Button></div></aside></div>}
  </div>;
}
