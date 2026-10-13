// File purpose: 日报与周报编辑器。日报为五段结构，周报固定 P / R / O 三段。
// How to change: 周报标题与「● 进展 / ● 结果」标签是用户指定格式，不要改动；其它展示文案可调整。

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert, Button, Dropdown, Input, Select, Space, Tag, Tooltip, message,
} from 'antd';
import {
  ArrowDownOutlined, ArrowUpOutlined, CheckOutlined, CopyOutlined, DeleteOutlined,
  DownloadOutlined, EditOutlined, MoreOutlined, PlusOutlined, SaveOutlined, ThunderboltOutlined,
} from '@ant-design/icons';
import {
  PROGRESS_LABELS, chineseIndex, copyText, formatClock, newId, saveBlob,
} from './workJournalUtils.js';

const API = '/v1/work-journal';
const AUTOSAVE_DELAY = 1500;

function normalizeSections(report) {
  const raw = report?.sections || {};
  if (report?.report_type === 'daily') {
    return {
      items: (raw.items || []).map((item) => ({ ...item, item_id: item.item_id || newId() })),
      quality: raw.quality || '',
      blockers: (raw.blockers || []).map((row) => ({ ...row, id: row.id || newId() })),
      next_plan: (raw.next_plan || []).map((row) => ({ ...row, id: row.id || newId() })),
      reflection: raw.reflection || '',
    };
  }
  return {
    p_items: (raw.p_items || []).map((item) => ({ ...item, item_id: item.item_id || newId() })),
    r_items: (raw.r_items || []).map((row) => ({ ...row, id: row.id || newId() })),
    o_items: (raw.o_items || []).map((row) => ({ ...row, id: row.id || newId() })),
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
      // 复制与导出共用后端同一个格式化函数，保证格式一致。
      const { blob } = await client.download(`${API}/reports/${report.id}/export?body_only=true`);
      const text = await blob.text();
      if (await copyText(text)) message.success(editing ? '已复制已保存的正文' : '已复制正文');
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

  const gap = useMemo(() => {
    if (report?.report_type === 'daily') {
      return sections.items.some((item) => item.name?.trim() && item.progress?.trim())
        ? null
        : '请至少在「今日完成」中填写一个事项的名称与进展';
    }
    return sections.p_items.some((item) => item.name?.trim() && item.progress?.trim() && item.result?.trim())
      ? null
      : '请至少填写一个核心事项的名称、进展与结果（结果未定可写「结果待确认」）';
  }, [sections, report?.report_type]);

  const stateText =
    saveState === 'saving' ? '保存中…'
      : saveState === 'dirty' ? '有未保存修改'
        : saveState === 'error' ? '保存失败，请重试'
          : `已保存 ${formatClock(savedAt.toISOString())}`;

  const isWeekly = report?.report_type === 'weekly';

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
              {isWeekly ? '根据日报生成周报' : '从当日日志整理'}
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

      {isWeekly ? (
        <WeeklyBody
          sections={sections}
          editing={editing}
          onPatch={patchSections}
        />
      ) : (
        <DailyBody
          sections={sections}
          editing={editing}
          onPatch={patchSections}
        />
      )}
    </div>
  );
}

function WeeklyBody({ sections, editing, onPatch }) {
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
            <>
              <Input
                value={item.name}
                placeholder="事项名称"
                style={{ marginBottom: 6 }}
                onChange={(event) => patchList('p_items', (list) => list.map((row, i) => (i === index ? { ...row, name: event.target.value, manually_edited: true } : row)))}
              />
              <Input
                value={item.project}
                placeholder="项目（选填，同名不同项目不会自动合并）"
                style={{ marginBottom: 6 }}
                onChange={(event) => patchList('p_items', (list) => list.map((row, i) => (i === index ? { ...row, project: event.target.value, manually_edited: true } : row)))}
              />
              <Input.TextArea
                className="work-journal__textarea"
                value={item.progress}
                autoSize={{ minRows: 2, maxRows: 6 }}
                placeholder="进展"
                style={{ marginBottom: 6 }}
                onChange={(event) => patchList('p_items', (list) => list.map((row, i) => (i === index ? { ...row, progress: event.target.value, manually_edited: true } : row)))}
              />
              <Input.TextArea
                className="work-journal__textarea"
                value={item.result}
                autoSize={{ minRows: 2, maxRows: 6 }}
                placeholder="结果（未定可写「结果待确认」）"
                onChange={(event) => patchList('p_items', (list) => list.map((row, i) => (i === index ? { ...row, result: event.target.value, manually_edited: true } : row)))}
              />
            </>
          ) : (
            <>
              <div className="work-journal__ro-name">
                事项{chineseIndex(index + 1)}：{item.name}
                {item.project ? <span className="work-journal__flag">{item.project}</span> : null}
                {item.result_conflict ? <span className="work-journal__flag">结果存在差异</span> : null}
              </div>
              <div className="work-journal__ro-line"><span className="work-journal__ro-bullet">●</span>进展：{item.progress || '未填写'}</div>
              <div className="work-journal__ro-line"><span className="work-journal__ro-bullet">●</span>结果：{item.result || '结果待确认'}</div>
            </>
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
          onClick={() => patchList('p_items', (list) => [...list, { item_id: newId(), name: '', project: '', progress: '', result: '', source_item_refs: [], manually_edited: true }])}
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

function DailyBody({ sections, editing, onPatch }) {
  function patchList(key, updater) {
    onPatch((current) => ({ ...current, [key]: updater(current[key]) }));
  }
  const textKeys = [
    ['quality', '测试与质量', '测试范围、执行结果、已知问题或缺陷链接'],
    ['reflection', '成长与复盘', '经验、学习收获、可改进的地方'],
  ];
  const listKeys = [
    ['blockers', '风险与阻碍', '影响、待确认事项、所需支持'],
    ['next_plan', '明日计划', '下一工作日准备推进的事项'],
  ];
  return (
    <>
      <div className="work-journal__ro-heading">今日完成</div>
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
              <Select
                size="small"
                value={item.status || 'in_progress'}
                style={{ width: 110 }}
                disabled
                options={Object.entries(PROGRESS_LABELS).map(([value, label]) => ({ value, label }))}
              />
            )}
          </div>
          {editing ? (
            <>
              <Input
                value={item.name}
                placeholder="事项名称"
                style={{ marginBottom: 6 }}
                onChange={(event) => patchList('items', (list) => list.map((row, i) => (i === index ? { ...row, name: event.target.value } : row)))}
              />
              <Space wrap style={{ marginBottom: 6 }}>
                <Input
                  value={item.project}
                  placeholder="项目（选填）"
                  style={{ width: 200 }}
                  onChange={(event) => patchList('items', (list) => list.map((row, i) => (i === index ? { ...row, project: event.target.value } : row)))}
                />
                <Select
                  value={item.status || 'in_progress'}
                  style={{ width: 120 }}
                  options={Object.entries(PROGRESS_LABELS).map(([value, label]) => ({ value, label }))}
                  onChange={(value) => patchList('items', (list) => list.map((row, i) => (i === index ? { ...row, status: value } : row)))}
                />
              </Space>
              <Input.TextArea
                className="work-journal__textarea"
                value={item.progress}
                autoSize={{ minRows: 2, maxRows: 5 }}
                placeholder="进展（必填）"
                style={{ marginBottom: 6 }}
                onChange={(event) => patchList('items', (list) => list.map((row, i) => (i === index ? { ...row, progress: event.target.value } : row)))}
              />
              <Input.TextArea
                className="work-journal__textarea"
                value={item.result}
                autoSize={{ minRows: 2, maxRows: 5 }}
                placeholder="结果（可为空）"
                onChange={(event) => patchList('items', (list) => list.map((row, i) => (i === index ? { ...row, result: event.target.value } : row)))}
              />
            </>
          ) : (
            <>
              <div className="work-journal__ro-name">
                {item.name}
                {item.project ? <span className="work-journal__flag">{item.project}</span> : null}
                <Tag color={item.status === 'completed' ? 'green' : item.status === 'blocked' ? 'orange' : 'blue'} style={{ marginLeft: 6 }}>
                  {PROGRESS_LABELS[item.status] || '进行中'}
                </Tag>
              </div>
              <div className="work-journal__ro-line"><span className="work-journal__ro-bullet">●</span>进展：{item.progress || '未填写'}</div>
              <div className="work-journal__ro-line"><span className="work-journal__ro-bullet">●</span>结果：{item.result || '结果待确认'}</div>
            </>
          )}
        </div>
      ))}
      {editing ? (
        <Button
          size="small"
          icon={<PlusOutlined />}
          style={{ marginBottom: 12 }}
          onClick={() => patchList('items', (list) => [...list, { item_id: newId(), name: '', project: '', progress: '', result: '', status: 'in_progress', source_refs: [] }])}
        >
          添加事项
        </Button>
      ) : null}

      {textKeys.map(([key, heading, placeholder]) => (
        <div key={key}>
          <div className="work-journal__ro-heading">{heading}</div>
          {editing ? (
            <Input.TextArea
              className="work-journal__textarea"
              value={sections[key]}
              autoSize={{ minRows: 3, maxRows: 8 }}
              placeholder={placeholder}
              onChange={(event) => onPatch((current) => ({ ...current, [key]: event.target.value }))}
            />
          ) : (
            <div className="work-journal__text">{sections[key] || '未填写'}</div>
          )}
        </div>
      ))}

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
