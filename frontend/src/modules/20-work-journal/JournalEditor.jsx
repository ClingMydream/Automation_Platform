// File purpose: 工作日志编辑器。负责表单、防抖保存、串行提交与冲突提示。
// How to change: 保存协议改动时同步 service.py 的 revision 校验；展示文案改这里即可。

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert, Button, Collapse, DatePicker, Dropdown, Input, InputNumber, Select, Space, Tag, Tooltip, message,
} from 'antd';
import {
  CopyOutlined, DeleteOutlined, DownloadOutlined, MoreOutlined, SaveOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  CATEGORIES, PROGRESS_LABELS, REMARKS_MAX, copyText, downloadText, formatClock, newId, shanghaiToday,
} from './workJournalUtils.js';

const API = '/v1/work-journal';
const AUTOSAVE_DELAY = 1500;

function blankEntry(workDate) {
  return {
    id: null,
    work_date: workDate,
    title: '',
    body_markdown: '',
    project: '',
    category: '测试执行',
    progress_status: 'in_progress',
    duration_minutes: null,
    tags: [],
    outcome_markdown: '',
    blocker_markdown: '',
    next_step_markdown: '',
    remarks_markdown: '',
    revision: 1,
  };
}

function toForm(entry, workDate) {
  if (!entry || !entry.id) return blankEntry(workDate);
  return {
    ...entry,
    project: entry.project || '',
    outcome_markdown: entry.outcome_markdown || '',
    blocker_markdown: entry.blocker_markdown || '',
    next_step_markdown: entry.next_step_markdown || '',
    remarks_markdown: entry.remarks_markdown || '',
    tags: entry.tags || [],
  };
}

export function JournalEditor({ client, entry, workDate, onSaved, onDeleted, onDirtyChange, onRegisterSave }) {
  const [form, setForm] = useState(() => toForm(entry, workDate));
  const [saveState, setSaveState] = useState('idle');
  const [savedAt, setSavedAt] = useState(null);
  const [conflict, setConflict] = useState(false);
  const [busy, setBusy] = useState(false);

  const requestId = useRef(newId());
  const revision = useRef(entry?.revision || 1);
  const recordId = useRef(entry?.id || null);
  const sequence = useRef(0);
  const edits = useRef(0);
  const queue = useRef(Promise.resolve());
  const timer = useRef(null);
  const dirty = useRef(false);

  // 切换记录时整体重置编辑器，避免上一条的内容串到下一条。
  useEffect(() => {
    // First create response belongs to this editor; keep any input typed during saving.
    if (entry?.id && recordId.current === entry.id) return;
    setForm(toForm(entry, workDate));
    setSaveState(entry?.id ? 'saved' : 'idle');
    setSavedAt(entry?.id ? new Date() : null);
    setConflict(false);
    requestId.current = newId();
    revision.current = entry?.revision || 1;
    recordId.current = entry?.id || null;
    dirty.current = false;
    onDirtyChange?.(false);
  }, [entry?.id, workDate]);

  useEffect(() => () => clearTimeout(timer.current), []);
  useEffect(() => { onRegisterSave?.(saveNow); });

  const runSave = useCallback(
    (snapshot, { silent }) => {
      const seq = (sequence.current += 1);
      const editVersion = edits.current;
      setSaveState('saving');
      queue.current = queue.current.then(async () => {
        try {
          const payload = {
            work_date: snapshot.work_date,
            title: snapshot.title,
            body_markdown: snapshot.body_markdown,
            project: snapshot.project || null,
            category: snapshot.category,
            progress_status: snapshot.progress_status,
            duration_minutes: snapshot.duration_minutes,
            tags: snapshot.tags || [],
            outcome_markdown: snapshot.outcome_markdown || null,
            blocker_markdown: snapshot.blocker_markdown || null,
            next_step_markdown: snapshot.next_step_markdown || null,
            remarks_markdown: snapshot.remarks_markdown || null,
          };
          const saved = recordId.current
            ? await client.put(`${API}/entries/${recordId.current}`, { ...payload, revision: revision.current })
            : await client.post(`${API}/entries`, { ...payload, client_request_id: requestId.current });
          recordId.current = saved.id;
          revision.current = saved.revision;
          setConflict(false);
          // 只有这次提交仍是最新输入时才显示"已保存"，否则等下一轮防抖保存。
          if (seq === sequence.current && editVersion === edits.current) {
            setSaveState('saved');
            setSavedAt(new Date());
            dirty.current = false;
            onDirtyChange?.(false);
          }
          onSaved?.(saved);
          return editVersion === edits.current;
        } catch (error) {
          const text = String(error?.message || '');
          if (seq === sequence.current && editVersion === edits.current) {
            if (text.includes('已被修改') || text.includes('409')) {
              setConflict(true);
              setSaveState('error');
            } else {
              setSaveState('error');
              if (!silent) message.error(text || '保存失败，请重试');
            }
          }
          return false;
        }
      });
      return queue.current;
    },
    [client, onDirtyChange, onSaved],
  );

  function patch(values) {
    edits.current++;
    setForm((current) => {
      const next = { ...current, ...values };
      dirty.current = true;
      onDirtyChange?.(true);
      setSaveState('dirty');
      clearTimeout(timer.current);
      // 首次保存前明确提示"尚未保存"，不静默创建草稿。
      timer.current = setTimeout(() => runSave(next, { silent: true }), AUTOSAVE_DELAY);
      return next;
    });
  }

  async function saveNow() {
    clearTimeout(timer.current);
    if (!form.title.trim() || !form.body_markdown.trim()) {
      message.warning('请填写工作事项；标题可在更多信息中调整');
      setSaveState('error');
      return false;
    }
    return runSave(form, { silent: false });
  }

  async function remove() {
    if (!recordId.current) return;
    setBusy(true);
    try {
      await client.delete(`${API}/entries/${recordId.current}?revision=${revision.current}`);
      dirty.current = false;
      onDirtyChange?.(false);
      onDeleted?.();
    } catch (error) {
      message.error(error.message || '删除失败');
    } finally {
      setBusy(false);
    }
  }

  async function copyBody() {
    const text = [form.title, '', form.body_markdown].join('\n');
    if (await copyText(text)) message.success('已复制标题和正文');
    else message.warning('复制失败，请在正文区手动选择复制');
  }

  function downloadBody() {
    downloadText(
      [`# ${form.title || '工作日志'}`, '', `- 工作日期：${form.work_date}`, '', form.body_markdown].join('\n'),
      `${form.work_date} ${form.title || '工作日志'}.md`,
    );
  }

  const stateText = useMemo(() => {
    if (saveState === 'saving') return '保存中…';
    if (saveState === 'dirty') return recordId.current ? '有未保存修改' : '尚未保存';
    if (saveState === 'error') return '保存失败，请重试';
    if (saveState === 'saved' && savedAt) return `已保存 ${formatClock(savedAt.toISOString())}`;
    return '尚未保存';
  }, [saveState, savedAt]);

  const isNew = !recordId.current;

  return (
    <div className="work-journal__card">
      <div className="work-journal__bar">
        <div className="work-journal__bar-left">
          <strong>{isNew ? '记一笔' : '编辑日志'}</strong>
          <span className={`work-journal__save-state ${saveState === 'error' ? 'is-error' : ''} ${saveState === 'saved' ? 'is-saved' : ''}`}>
            {stateText}
          </span>
        </div>
        <div className="work-journal__bar-right">
          <Button icon={<SaveOutlined />} onClick={saveNow} loading={saveState === 'saving'}>
            {isNew ? '保存草稿' : '保存修改'}
          </Button>
          <Button icon={<CopyOutlined />} onClick={copyBody}>复制</Button>
          <Button icon={<DownloadOutlined />} onClick={downloadBody}>下载</Button>
          <Dropdown
            menu={{
              items: [{ key: 'delete', danger: true, icon: <DeleteOutlined />, label: '删除日志' }],
              onClick: ({ key }) => {
                if (key === 'delete' && recordId.current) {
                  if (window.confirm('删除后可在回收站恢复，确认删除这条日志吗？')) remove();
                }
              },
            }}
            trigger={['click']}
          >
            <Button icon={<MoreOutlined />} disabled={isNew} />
          </Dropdown>
        </div>
      </div>

      {conflict ? (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 10 }}
          message="这条日志在别处被修改过"
          description={
            <Space wrap>
              <span>为避免覆盖，请先复制本地内容，再重新加载。</span>
              <Button size="small" onClick={async () => {
                if (await copyText(form.body_markdown)) message.success('本地内容已复制');
              }}>复制本地内容</Button>
              <Button size="small" onClick={() => window.location.reload()}>重新加载</Button>
            </Space>
          }
        />
      ) : null}

      <div className="work-journal__field">
        <span className="work-journal__label">工作日期</span>
        <DatePicker
          value={dayjs(form.work_date)}
          allowClear={false}
          disabledDate={(current) => current && current.format('YYYY-MM-DD') > shanghaiToday()}
          onChange={(value) => patch({ work_date: value ? value.format('YYYY-MM-DD') : shanghaiToday() })}
          style={{ width: 180 }}
        />
      </div>

      <div className="work-journal__field">
        <span className="work-journal__label">事项 *</span>
        <Input.TextArea aria-label="工作事项" className="work-journal__textarea" value={form.body_markdown} autoSize={{minRows:4,maxRows:12}} maxLength={20000} placeholder="记录做了什么、当前进展；首行自动作为标题" onChange={event=>{const text=event.target.value;patch({body_markdown:text,...(!recordId.current ? {title:text.trim().split('\n')[0].slice(0,120)} : {})});}}/>
      </div>
      <div className="work-journal__field"><span className="work-journal__label">状态</span><Select aria-label="事项状态" value={form.progress_status} style={{minWidth:160}} onChange={value=>patch({progress_status:value})} options={Object.entries(PROGRESS_LABELS).map(([value,label])=>({value,label}))}/></div>
      <Collapse className="work-journal__advanced" items={[{key:'details',label:'更多信息（选填，历史内容保留）',children:<>
      <div className="work-journal__field"><span className="work-journal__label">标题</span><Input value={form.title} maxLength={120} onChange={event=>patch({title:event.target.value})}/></div>
      <div className="work-journal__field" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(190px,1fr))', gap: 12 }}>
        <div>
          <span className="work-journal__label">项目</span>
          <Input value={form.project} maxLength={80} placeholder="选填，例如 霖感 APP" onChange={(event) => patch({ project: event.target.value })} />
        </div>
        <div>
          <span className="work-journal__label">工作类型</span>
          <Select value={form.category} style={{ width: '100%' }} onChange={(value) => patch({ category: value })}
            options={CATEGORIES.map((item) => ({ value: item, label: item }))} />
        </div>
        <div>
          <span className="work-journal__label">工时（分钟，留空表示未记录）</span>
          <InputNumber
            value={form.duration_minutes}
            min={0}
            max={1440}
            style={{ width: '100%' }}
            placeholder="未记录"
            onChange={(value) => patch({ duration_minutes: value === '' || value == null ? null : Number(value) })}
          />
        </div>
      </div>

      <div className="work-journal__field">
        <span className="work-journal__label">标签（最多 10 个）</span>
        <Select
          mode="tags"
          value={form.tags}
          style={{ width: '100%' }}
          placeholder="回车添加标签"
          tokenSeparators={[',', '，']}
          onChange={(value) => patch({ tags: value.slice(0, 10).map((item) => String(item).slice(0, 24)) })}
        />
      </div>

      {[
        ['outcome_markdown', '结果与产出', '例如报告链接、修复结果、已完成范围'],
        ['blocker_markdown', '风险与阻碍', '例如影响范围、待确认事项'],
        ['next_step_markdown', '下一步', '例如明天准备推进什么'],
      ].map(([key, label, placeholder]) => (
        <div className="work-journal__field" key={key}>
          <span className="work-journal__label">{label}</span>
          <Input.TextArea
            className="work-journal__textarea"
            value={form[key]}
            autoSize={{ minRows: 2, maxRows: 6 }}
            placeholder={placeholder}
            onChange={(event) => patch({ [key]: event.target.value })}
          />
        </div>
      ))}

      {form.duration_minutes === null ? (
        <Tooltip title="留空表示没有记录工时，不会被当作 0 分钟">
          <Tag>工时未记录</Tag>
        </Tooltip>
      ) : null}

      </>}]} />
      <div className="work-journal__field" style={{ marginTop: 12 }}>
        <span className="work-journal__label">备注（选填）</span>
        <Input.TextArea
          className="work-journal__textarea"
          value={form.remarks_markdown || ''}
          autoSize={{ minRows: 2, maxRows: 6 }}
          maxLength={REMARKS_MAX}
          placeholder="补充说明、背景或链接（选填）"
          onChange={(event) => patch({ remarks_markdown: event.target.value })}
        />
      </div>
    </div>
  );
}
