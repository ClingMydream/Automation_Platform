// File purpose: 日报与周报编辑器（二期）。事项只有内容 / 状态 / 进度三个字段，周报固定 P / R / O。
// How to change: 周报标题与「● 进展 / ● 结果」标签是用户指定格式，不要改动；其它展示文案可调整。

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert, Button, Collapse, Dropdown, Input, Select, Space, Tag, Tooltip, message,
} from 'antd';
import {
  ArrowDownOutlined, ArrowUpOutlined, CheckOutlined, CopyOutlined, DeleteOutlined,
  DownloadOutlined, EditOutlined, MoreOutlined, PlusOutlined, SaveOutlined, ThunderboltOutlined,
} from '@ant-design/icons';
import {
  CONTENT_MAX, PROGRESS_LABELS, PROGRESS_OPTIONS, PROGRESS_PLACEHOLDER, REMARKS_MAX,
  applyProgressChange, applyStatusChange, chineseIndex, contentSummary, copyText,
  formatClock, newId, progressSentence, saveBlob,
} from './workJournalUtils.js';

const API = '/v1/work-journal';
const AUTOSAVE_DELAY = 1500;
const V1_TEMPLATES = ['daily_v1', 'weekly_pro_v1'];

function progressOptions() {
  return PROGRESS_OPTIONS.map((value) => ({ value, label: `${value}%` }));
}

export function normalizeSections(report) {
  const raw = report?.sections || {};
  const asItem = (item) => ({
    ...item,
    item_id: item.item_id || newId(),
    // 老记录没有百分比时保持空，展示为「请选择进度」，不推断 50%。
    progress_percent: item.progress_percent ?? null,
  });
  if (report?.report_type === 'daily') {
    return {
      // 展开原始字段，避免旧版报告的 body / legacy_supplement 在保存时被丢掉。
      ...raw,
      items: (raw.items || []).map(asItem),
      blockers: (raw.blockers || []).map((row) => ({ ...row, id: row.id || newId() })),
      next_plan: (raw.next_plan || []).map((row) => ({ ...row, id: row.id || newId() })),
      remarks: raw.remarks || '',
    };
  }
  return {
    ...raw,
    p_items: (raw.p_items || []).map(asItem),
    r_items: (raw.r_items || []).map((row) => ({ ...row, id: row.id || newId() })),
    o_items: (raw.o_items || []).map((row) => ({ ...row, id: row.id || newId() })),
    remarks: raw.remarks || '',
  };
}

function move(list, index, offset) {
  const target = index + offset;
  if (target < 0 || target >= list.length) return list;
  const next = [...list];
  [next[index], next[target]] = [next[target], next[index]];
  return next;
}

function RowActions({ index, total, onMove, onRemove }) {
  return (
    <div className="work-journal__block-actions">
      <Button size="small" type="text" icon={<ArrowUpOutlined />} disabled={index === 0} onClick={() => onMove(index, -1)} />
      <Button size="small" type="text" icon={<ArrowDownOutlined />} disabled={index === total - 1} onClick={() => onMove(index, 1)} />
      <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => onRemove(index)} />
    </div>
  );
}

// 二期事项：内容 / 状态 / 进度三项，状态与百分比联动。
function ItemFields({ item, onChange }) {
  return (
    <>
      <Input.TextArea
        className="work-journal__textarea"
        value={item.content || ''}
        autoSize={{ minRows: 2, maxRows: 6 }}
        maxLength={CONTENT_MAX}
        placeholder="描述具体做了什么"
        style={{ marginBottom: 8 }}
        onChange={(event) => onChange({ ...item, content: event.target.value })}
      />
      <div className="work-journal__item-row">
        <span className="work-journal__inline-label">状态</span>
        <Select
          value={item.status || 'in_progress'}
          popupClassName="work-journal-popup"
          style={{ width: 132 }}
          options={Object.entries(PROGRESS_LABELS).map(([value, label]) => ({ value, label }))}
          onChange={(value) => onChange(applyStatusChange(item, value))}
        />
        <span className="work-journal__inline-label">进度</span>
        <Select
          value={item.progress_percent ?? undefined}
          placeholder={PROGRESS_PLACEHOLDER}
          popupClassName="work-journal-popup"
          style={{ width: 132 }}
          options={progressOptions()}
          onChange={(value) => onChange(applyProgressChange(item, value))}
        />
      </div>
    </>
  );
}

function ItemRead({ item }) {
  return (
    <>
      <div className="work-journal__ro-name">
        {contentSummary(item.content) || '未命名事项'}
        <Tag color={item.status === 'completed' ? 'green' : item.status === 'blocked' ? 'orange' : 'blue'} style={{ marginLeft: 6 }}>
          {PROGRESS_LABELS[item.status] || '进行中'}
        </Tag>
        <Tag>{item.progress_percent ?? '—'}%</Tag>
        {item.status_conflict ? <span className="work-journal__flag">状态存在差异，待核对</span> : null}
      </div>
      <div className="work-journal__ro-line"><span className="work-journal__ro-bullet">●</span>进展：{item.content}</div>
      <div className="work-journal__ro-line"><span className="work-journal__ro-bullet">●</span>结果：{progressSentence(item)}</div>
    </>
  );
}

function LegacySupplement({ supplement }) {
  if (!supplement) return null;
  const hasDaily = supplement.quality || supplement.reflection || (supplement.results || []).length;
  const hasWeekly = (supplement.p_items || []).length;
  if (!hasDaily && !hasWeekly) return null;
  return (
    <Collapse
      ghost
      className="work-journal__legacy-supplement"
      items={[{
        key: 'legacy',
        label: '历史补充内容（一期记录，只读）',
        children: (
          <div>
            {supplement.quality ? <><div className="work-journal__label">测试与质量</div><div className="work-journal__text">{supplement.quality}</div></> : null}
            {supplement.reflection ? <><div className="work-journal__label">成长与复盘</div><div className="work-journal__text">{supplement.reflection}</div></> : null}
            {(supplement.results || []).map((row, index) => (
              <div key={`${row.item_id || index}`} className="work-journal__text">
                <strong>{row.name || '事项'}</strong>：{row.result}
              </div>
            ))}
            {(supplement.p_items || []).map((row, index) => (
              <div key={`${row.item_id || index}`} className="work-journal__text">
                <strong>{row.name || '事项'}</strong>　进展：{row.progress || '—'}　结果：{row.result || '—'}
              </div>
            ))}
          </div>
        ),
      }]}
    />
  );
}

export function ReportEditor({ client, report, onSaved, onDeleted, onDirtyChange, onOpenSources }) {
  const [title, setTitle] = useState(report?.title || '');
  const [sections, setSections] = useState(() => normalizeSections(report));
  const [status, setStatus] = useState(report?.status || 'draft');
  const [saveState, setSaveState] = useState('saved');
  const [savedAt, setSavedAt] = useState(new Date());
  const [conflict, setConflict] = useState(false);
  const [editing, setEditing] = useState(report?.status !== 'completed');

  const revision = useRef(report?.revision || 1);
  const sequence = useRef(0);
  const queue = useRef(Promise.resolve());
  const timer = useRef(null);
  const latest = useRef({ title, sections });

  latest.current = { title, sections };

  useEffect(() => {
    setTitle(report?.title || '');
    setSections(normalizeSections(report));
    setStatus(report?.status || 'draft');
    setSaveState('saved');
    setSavedAt(new Date());
    setConflict(false);
    setEditing(report?.status !== 'completed');
    revision.current = report?.revision || 1;
    onDirtyChange?.(false);
  }, [report?.id, report?.revision]);

  useEffect(() => () => clearTimeout(timer.current), []);

  const runSave = useCallback(
    (snapshotTitle, snapshotSections, { silent } = {}) => {
      const seq = (sequence.current += 1);
      setSaveState('saving');
      queue.current = queue.current.then(async () => {
        try {
          const saved = await client.put(`${API}/reports/${report.id}`, {
            title: snapshotTitle,
            sections: snapshotSections,
            revision: revision.current,
          });
          revision.current = saved.revision;
          setConflict(false);
          if (seq === sequence.current) {
            setSaveState('saved');
            setSavedAt(new Date());
            onDirtyChange?.(false);
          }
          onSaved?.(saved);
        } catch (error) {
          const text = String(error?.message || '');
          if (seq === sequence.current) {
            setConflict(text.includes('修改') || text.includes('409'));
            setSaveState('error');
            if (!silent) message.error(text || '保存失败，请重试');
          }
        }
      });
      return queue.current;
    },
    [client, onDirtyChange, onSaved, report?.id],
  );

  function schedule(nextTitle, nextSections) {
    onDirtyChange?.(true);
    setSaveState('dirty');
    clearTimeout(timer.current);
    timer.current = setTimeout(() => runSave(nextTitle, nextSections, { silent: true }), AUTOSAVE_DELAY);
  }

  function patchTitle(value) {
    setTitle(value);
    schedule(value, latest.current.sections);
  }

  function patchSections(updater) {
    setSections((current) => {
      const next = updater(current);
      schedule(latest.current.title, next);
      return next;
    });
  }

  async function saveNow() {
    clearTimeout(timer.current);
    if (!title.trim()) {
      message.warning('标题不能为空');
      return null;
    }
    await runSave(latest.current.title, latest.current.sections, { silent: false });
    return true;
  }

  async function complete() {
    clearTimeout(timer.current);
    await runSave(latest.current.title, latest.current.sections, { silent: false });
    try {
      const saved = await client.post(`${API}/reports/${report.id}/complete`, { revision: revision.current });
      revision.current = saved.revision;
      setStatus(saved.status);
      setEditing(false);
      onSaved?.(saved);
      message.success('已标记完成');
    } catch (error) {
      message.error(error.message || '完成失败');
    }
  }

  async function reopen() {
    try {
      const saved = await client.post(`${API}/reports/${report.id}/reopen`, { revision: revision.current });
      revision.current = saved.revision;
      setStatus(saved.status);
      setEditing(true);
      onSaved?.(saved);
    } catch (error) {
      message.error(error.message || '操作失败');
    }
  }

  async function copyBody() {
    if (saveState === 'dirty') await saveNow();
    try {
      const { blob } = await client.download(`${API}/reports/${report.id}/export?body_only=true`);
      const text = await blob.text();
      if (await copyText(text)) message.success('已复制正文');
      else message.warning('复制失败，请在阅读区手动选择复制');
    } catch (error) {
      message.error(error.message || '复制失败');
    }
  }

  async function download() {
    if (saveState === 'dirty') await saveNow();
    try {
      const { blob, filename } = await client.download(`${API}/reports/${report.id}/export`);
      saveBlob(blob, filename);
    } catch (error) {
      message.error(error.message || '下载失败');
    }
  }

  async function remove() {
    try {
      await client.delete(`${API}/reports/${report.id}?revision=${revision.current}`);
      onDirtyChange?.(false);
      onDeleted?.();
    } catch (error) {
      message.error(error.message || '删除失败');
    }
  }

  const isWeekly = report?.report_type === 'weekly';
  const isLegacy = String(report?.template_version || '').includes('legacy');
  const isV1 = V1_TEMPLATES.includes(report?.template_version);
  const legacyBody = report?.sections?.body || report?.sections?.markdown || '';
  const supplement = sections.legacy_supplement;

  // 完成校验与后端保持一致：每个保留事项都要有内容、有效状态与一致进度。
  const gap = useMemo(() => {
    if (isLegacy) return null;
    const items = (isWeekly ? sections.p_items : sections.items) || [];
    if (isV1) {
      const usable = isWeekly
        ? items.filter((item) => (item.name || '').trim() && (item.progress || '').trim() && (item.result || '').trim())
        : items.filter((item) => (item.name || '').trim() && (item.progress || '').trim());
      return usable.length ? null : '请至少填写一个事项的名称、进展与结果';
    }
    if (!items.length) return '请至少添加一个事项';
    for (let index = 0; index < items.length; index += 1) {
      const item = items[index];
      if (!String(item.content || '').trim()) return `第 ${index + 1} 个事项还没有内容，请补充或删除这张空卡片`;
      if (item.progress_percent === null || item.progress_percent === undefined) return `请为第 ${index + 1} 个事项选择进度`;
      if (item.status === 'completed' && item.progress_percent !== 100) return `第 ${index + 1} 个事项已完成，进度必须是 100%`;
      if (item.status !== 'completed' && item.progress_percent === 100) return `第 ${index + 1} 个事项进度 100% 时状态应为已完成`;
    }
    return null;
  }, [sections, isWeekly, isLegacy, isV1]);

  const stateText =
    saveState === 'saving' ? '保存中…'
      : saveState === 'dirty' ? '有未保存修改'
        : saveState === 'error' ? '保存失败，请重试'
          : `已保存 ${formatClock(savedAt.toISOString())}`;

  return (
    <div className="work-journal__card">
      <div className="work-journal__bar">
        <div className="work-journal__bar-left">
          <Tag color={status === 'completed' ? 'green' : 'orange'}>{status === 'completed' ? '已完成' : '草稿'}</Tag>
          <span className="work-journal__hint">{report.period_start} ～ {report.period_end}</span>
          <span className={`work-journal__save-state ${saveState === 'error' ? 'is-error' : ''} ${saveState === 'saved' ? 'is-saved' : ''}`}>
            {stateText}
          </span>
        </div>
        <div className="work-journal__bar-right">
          {onOpenSources ? (
            <Button type="primary" icon={<ThunderboltOutlined />} onClick={onOpenSources}>
              {isLegacy ? '转换为 P / R / O' : isV1 ? '整理为二期结构' : isWeekly ? '根据日报生成周报' : '从当日日志整理'}
            </Button>
          ) : null}
          {status === 'completed' ? (
            <Button icon={<EditOutlined />} onClick={reopen}>重新编辑</Button>
          ) : (
            <>
              <Button icon={<SaveOutlined />} onClick={saveNow} loading={saveState === 'saving'}>保存草稿</Button>
              <Tooltip title={gap || '校验通过即可标记完成'}>
                <Button type="primary" icon={<CheckOutlined />} onClick={complete} disabled={Boolean(gap)}>完成</Button>
              </Tooltip>
            </>
          )}
          <Button icon={<CopyOutlined />} onClick={copyBody}>复制正文</Button>
          <Button icon={<DownloadOutlined />} onClick={download}>下载</Button>
          <Dropdown
            menu={{
              items: [{ key: 'delete', danger: true, icon: <DeleteOutlined />, label: '删除报告' }],
              onClick: ({ key }) => {
                if (key === 'delete' && window.confirm('删除后可在回收站恢复，确认删除这份报告吗？')) remove();
              },
            }}
            trigger={['click']}
          >
            <Button icon={<MoreOutlined />} />
          </Dropdown>
        </div>
      </div>

      {conflict ? (
        <Alert type="error" showIcon style={{ marginBottom: 10 }} message="这份报告在别处被修改过，请先复制本地内容再重新加载。" />
      ) : null}

      <div className="work-journal__field">
        <span className="work-journal__label">标题</span>
        <Input value={title} disabled={!editing} maxLength={200} onChange={(event) => patchTitle(event.target.value)} />
      </div>

      {isLegacy ? (
        <>
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 12 }}
            message="这是旧版报告，正文按原文保留"
            description="点击「转换为 P / R / O」会先生成候选供你预览；采纳后原文保留在 legacy_body 中，历史内容不会被覆盖。"
          />
          <div className="work-journal__field">
            <span className="work-journal__label">旧版正文（只读）</span>
            <div className="work-journal__text">{legacyBody || '（无正文）'}</div>
          </div>
        </>
      ) : isV1 ? (
        <>
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 12 }}
            message="这是一期报告（名称 / 进展 / 结果）"
            description="点击「整理为二期结构」会按新的事项内容 / 状态 / 进度生成候选；原「结果、测试与质量、成长与复盘」会收进历史补充内容。"
          />
          {isWeekly
            ? <WeeklyBody sections={sections} editing={editing} onPatch={patchSections} isV1 />
            : <DailyBody sections={sections} editing={editing} onPatch={patchSections} isV1 />}
        </>
      ) : isWeekly ? (
        <WeeklyBody sections={sections} editing={editing} onPatch={patchSections} />
      ) : (
        <DailyBody sections={sections} editing={editing} onPatch={patchSections} />
      )}

      <LegacySupplement supplement={supplement} />

      {!isLegacy ? (
        <div className="work-journal__field" style={{ marginTop: 12 }}>
          <span className="work-journal__label">备注（选填）</span>
          <Input.TextArea
            className="work-journal__textarea"
            value={sections.remarks || ''}
            disabled={!editing}
            autoSize={{ minRows: 2, maxRows: 6 }}
            maxLength={REMARKS_MAX}
            placeholder="补充说明、背景或链接（选填）"
            onChange={(event) => patchSections((current) => ({ ...current, remarks: event.target.value }))}
          />
        </div>
      ) : null}
    </div>
  );
}

function WeeklyBody({ sections, editing, onPatch, isV1 = false }) {
  function patchList(key, updater) {
    onPatch((current) => ({ ...current, [key]: updater(current[key]) }));
  }
  const simpleKeys = [
    ['r_items', 'R-需要关注的风险与问题'],
    ['o_items', 'O-下周核心目标与计划'],
  ];
  return (
    <>
      <div className="work-journal__ro-heading">P-核心进展与结果</div>
      {sections.p_items.map((item, index) => (
        <div className="work-journal__block" key={item.item_id}>
          <div className="work-journal__block-head">
            <span className="work-journal__block-index">{chineseIndex(index + 1)}</span>
            <strong>{item.manually_edited ? '人工修改' : '自动整理'}</strong>
            {editing ? (
              <RowActions
                index={index}
                total={sections.p_items.length}
                onMove={(from, offset) => patchList('p_items', (list) => move(list, from, offset))}
                onRemove={(from) => patchList('p_items', (list) => list.filter((_, i) => i !== from))}
              />
            ) : null}
          </div>
          {editing ? (
            isV1 ? (
              <>
                <Input value={item.name || ''} placeholder="事项名称" style={{ marginBottom: 6 }}
                  onChange={(event) => patchList('p_items', (list) => list.map((row, i) => (i === index ? { ...row, name: event.target.value, manually_edited: true } : row)))} />
                <Input.TextArea className="work-journal__textarea" value={item.progress || ''} autoSize={{ minRows: 2, maxRows: 5 }} placeholder="进展" style={{ marginBottom: 6 }}
                  onChange={(event) => patchList('p_items', (list) => list.map((row, i) => (i === index ? { ...row, progress: event.target.value, manually_edited: true } : row)))} />
                <Input.TextArea className="work-journal__textarea" value={item.result || ''} autoSize={{ minRows: 2, maxRows: 5 }} placeholder="结果"
                  onChange={(event) => patchList('p_items', (list) => list.map((row, i) => (i === index ? { ...row, result: event.target.value, manually_edited: true } : row)))} />
              </>
            ) : (
              <ItemFields
                item={item}
                onChange={(next) => patchList('p_items', (list) => list.map((row, i) => (i === index ? { ...next, manually_edited: true } : row)))}
              />
            )
          ) : (
            isV1 ? (
              <>
                <div className="work-journal__ro-name">事项{chineseIndex(index + 1)}：{item.name}</div>
                <div className="work-journal__ro-line"><span className="work-journal__ro-bullet">●</span>进展：{item.progress || '未填写'}</div>
                <div className="work-journal__ro-line"><span className="work-journal__ro-bullet">●</span>结果：{item.result || '结果待确认'}</div>
              </>
            ) : <ItemRead item={item} />
          )}
          {item.source_item_refs?.length ? (
            <div className="work-journal__sub">
              来源：{item.source_item_refs.map((ref) => `${ref.work_date} ${ref.title || ''}`.trim()).join('；')}
            </div>
          ) : null}
        </div>
      ))}
      {editing ? (
        <Button
          size="small"
          icon={<PlusOutlined />}
          style={{ marginBottom: 12 }}
          onClick={() => patchList('p_items', (list) => [...list, isV1
            ? { item_id: newId(), name: '', progress: '', result: '', source_item_refs: [], manually_edited: true }
            : { item_id: newId(), content: '', status: 'in_progress', progress_percent: null, source_item_refs: [], manually_edited: true }])}
        >
          添加事项
        </Button>
      ) : null}

      {simpleKeys.map(([key, heading]) => (
        <div key={key}>
          <div className="work-journal__ro-heading">{heading}</div>
          {sections[key].map((row, index) => (
            <div className="work-journal__block" key={row.id}>
              <div className="work-journal__block-head">
                <span className="work-journal__ro-bullet">●</span>
                {editing ? (
                  <>
                    <Input
                      value={row.text}
                      onChange={(event) => patchList(key, (list) => list.map((item, i) => (i === index ? { ...item, text: event.target.value, manually_edited: true } : item)))}
                    />
                    <RowActions
                      index={index}
                      total={sections[key].length}
                      onMove={(from, offset) => patchList(key, (list) => move(list, from, offset))}
                      onRemove={(from) => patchList(key, (list) => list.filter((_, i) => i !== from))}
                    />
                  </>
                ) : (
                  <span>{row.text}</span>
                )}
              </div>
            </div>
          ))}
          {editing ? (
            <Button size="small" icon={<PlusOutlined />} style={{ marginBottom: 12 }} onClick={() => patchList(key, (list) => [...list, { id: newId(), text: '', source_refs: [], manually_edited: true }])}>
              添加条目
            </Button>
          ) : null}
        </div>
      ))}
    </>
  );
}

function DailyBody({ sections, editing, onPatch, isV1 = false }) {
  function patchList(key, updater) {
    onPatch((current) => ({ ...current, [key]: updater(current[key]) }));
  }
  const listKeys = [
    ['blockers', '风险与阻碍', '影响、待确认事项、所需支持'],
    ['next_plan', '明日计划', '下一工作日准备推进的事项'],
  ];
  return (
    <>
      <div className="work-journal__ro-heading">今日事项</div>
      {sections.items.map((item, index) => (
        <div className="work-journal__block" key={item.item_id}>
          <div className="work-journal__block-head">
            <span className="work-journal__block-index">{chineseIndex(index + 1)}</span>
            {editing ? (
              <RowActions
                index={index}
                total={sections.items.length}
                onMove={(from, offset) => patchList('items', (list) => move(list, from, offset))}
                onRemove={(from) => patchList('items', (list) => list.filter((_, i) => i !== from))}
              />
            ) : (
              <Tag color={item.status === 'completed' ? 'green' : item.status === 'blocked' ? 'orange' : 'blue'}>
                {PROGRESS_LABELS[item.status] || '进行中'} · {item.progress_percent ?? '—'}%
              </Tag>
            )}
          </div>
          {editing ? (
            isV1 ? (
              <>
                <Input value={item.name || ''} placeholder="事项名称" style={{ marginBottom: 6 }}
                  onChange={(event) => patchList('items', (list) => list.map((row, i) => (i === index ? { ...row, name: event.target.value } : row)))} />
                <Input.TextArea className="work-journal__textarea" value={item.progress || ''} autoSize={{ minRows: 2, maxRows: 5 }} placeholder="进展" style={{ marginBottom: 6 }}
                  onChange={(event) => patchList('items', (list) => list.map((row, i) => (i === index ? { ...row, progress: event.target.value } : row)))} />
                <Input.TextArea className="work-journal__textarea" value={item.result || ''} autoSize={{ minRows: 2, maxRows: 5 }} placeholder="结果"
                  onChange={(event) => patchList('items', (list) => list.map((row, i) => (i === index ? { ...row, result: event.target.value } : row)))} />
              </>
            ) : (
              <ItemFields
                item={item}
                onChange={(next) => patchList('items', (list) => list.map((row, i) => (i === index ? next : row)))}
              />
            )
          ) : (
            isV1 ? (
              <>
                <div className="work-journal__ro-name">{item.name}</div>
                <div className="work-journal__ro-line"><span className="work-journal__ro-bullet">●</span>进展：{item.progress || '未填写'}</div>
                <div className="work-journal__ro-line"><span className="work-journal__ro-bullet">●</span>结果：{item.result || '结果待确认'}</div>
              </>
            ) : <ItemRead item={item} />
          )}
        </div>
      ))}
      {editing ? (
        <Button
          size="small"
          icon={<PlusOutlined />}
          style={{ marginBottom: 12 }}
          onClick={() => patchList('items', (list) => [...list, isV1
            ? { item_id: newId(), name: '', progress: '', result: '', status: 'in_progress', source_refs: [] }
            : { item_id: newId(), content: '', status: 'in_progress', progress_percent: null, source_refs: [] }])}
        >
          添加事项
        </Button>
      ) : null}

      {listKeys.map(([key, heading, placeholder]) => (
        <div key={key}>
          <div className="work-journal__ro-heading">{heading}</div>
          {sections[key].map((row, index) => (
            <div className="work-journal__block" key={row.id}>
              <div className="work-journal__block-head">
                <span className="work-journal__ro-bullet">●</span>
                {editing ? (
                  <>
                    <Input
                      value={row.text}
                      placeholder={placeholder}
                      onChange={(event) => patchList(key, (list) => list.map((item, i) => (i === index ? { ...item, text: event.target.value } : item)))}
                    />
                    <RowActions
                      index={index}
                      total={sections[key].length}
                      onMove={(from, offset) => patchList(key, (list) => move(list, from, offset))}
                      onRemove={(from) => patchList(key, (list) => list.filter((_, i) => i !== from))}
                    />
                  </>
                ) : (
                  <span>{row.text}</span>
                )}
              </div>
            </div>
          ))}
          {!sections[key].length ? <div className="work-journal__hint">未填写</div> : null}
          {editing ? (
            <Button size="small" icon={<PlusOutlined />} style={{ marginBottom: 12 }} onClick={() => patchList(key, (list) => [...list, { id: newId(), text: '', item_id: '', resolved: false }])}>
              添加条目
            </Button>
          ) : null}
        </div>
      ))}
    </>
  );
}
