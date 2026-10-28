import dayjs from 'dayjs';
// File purpose: 工作手记模块入口。包含工作日志 / 日报 / 周报三个页签与左右两栏布局。
// How to change: 交互与布局改这里；表单细节在 JournalEditor / ReportEditor / ReportSourcePreview。

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert, Button, DatePicker, Empty, Input, Modal, Segmented, Select, Space, Tag, message,
} from 'antd';
import {
  CalendarOutlined, DeleteOutlined, FormOutlined, LeftOutlined,
  ReloadOutlined, RightOutlined, SearchOutlined, UndoOutlined,
} from '@ant-design/icons';
import { JournalEditor } from './JournalEditor.jsx';
import { ReportEditor } from './ReportEditor.jsx';
import { ReportSourcePreview } from './ReportSourcePreview.jsx';
import {
  CATEGORIES, PROGRESS_LABELS, PROGRESS_TONES, STATUS_LABELS, calendarGrid, dateLabel,
  monthOf, shiftMonth, shanghaiToday, summaryOf, weekEndOf, weekStartOf, WEEKDAYS,
} from './workJournalUtils.js';
import './work-journal.css';

const API = '/v1/work-journal';
const TABS = [
  { value: 'logs', label: '工作日志' },
  { value: 'daily', label: '日报' },
  { value: 'weekly', label: '周报' },
];

function readParams() {
  const params = new URLSearchParams(window.location.search);
  const tab = params.get('journal_tab');
  const day = params.get('journal_date');
  return {
    tab: TABS.some((item) => item.value === tab) ? tab : 'logs',
    date: /^\d{4}-\d{2}-\d{2}$/.test(day || '') ? day : shanghaiToday(),
  };
}

export function WorkJournalPanel({ client }) {
  const initial = useRef(readParams());
  const [tab, setTab] = useState(initial.current.tab);
  const [date, setDate] = useState(initial.current.date);
  const [month, setMonth] = useState(monthOf(initial.current.date));

  const [entries, setEntries] = useState([]);
  const [reports, setReports] = useState([]);
  const [calendar, setCalendar] = useState(null);
  const [summary, setSummary] = useState(null);
  const [filters, setFilters] = useState({ projects: [], tags: [] });
  const [query, setQuery] = useState('');
  const [project, setProject] = useState();
  const [tag, setTag] = useState();
  const [status, setStatus] = useState();
  const [category, setCategory] = useState();
  const [trash, setTrash] = useState(false);

  const [selectedEntry, setSelectedEntry] = useState(null);
  const [selectedReport, setSelectedReport] = useState(null);
  const reportSelectionVersion = useRef(0);
  const [loading, setLoading] = useState(false);
  const [dirty, setDirty] = useState(false);
  const saveHandler = useRef(null);

  const [sourceOpen, setSourceOpen] = useState(false);
  const [sourceLoading, setSourceLoading] = useState(false);
  const [preview, setPreview] = useState(null);
  const [includeDraft, setIncludeDraft] = useState(false);

  const weekStart = weekStartOf(date);
  const weekEnd = weekEndOf(date);

  const syncUrl = useCallback((nextTab, nextDate) => {
    const params = new URLSearchParams(window.location.search);
    params.set('module', 'work_journal');
    params.set('journal_tab', nextTab);
    params.set('journal_date', nextDate);
    window.history.pushState({}, '', `${window.location.pathname}?${params.toString()}`);
  }, []);

  // 浏览器前进后退要能恢复页签与日期。
  useEffect(() => {
    function onPop() {
      const next = readParams();
      setTab(next.tab);
      setDate(next.date);
      setMonth(monthOf(next.date));
    }
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  const loadList = useCallback(async () => {
    setLoading(true);
    try {
      if (tab === 'logs') {
        const params = new URLSearchParams({ page: '1', page_size: '100' });
        if (query.trim()) params.set('q', query.trim());
        if (project) params.set('project', project);
        if (tag) params.set('tag', tag);
        if (status) params.set('progress_status', status);
        if (category) params.set('category', category);
        if (trash) params.set('deleted', 'true');
        const data = await client.get(`${API}/entries?${params.toString()}`);
        setEntries(data.items);
      } else {
        const params = new URLSearchParams({ page: '1', page_size: '60', report_type: tab === 'daily' ? 'daily' : 'weekly' });
        if (query.trim()) params.set('q', query.trim());
        if (trash) params.set('deleted', 'true');
        const data = await client.get(`${API}/reports?${params.toString()}`);
        setReports(data.items);
      }
    } catch (error) {
      message.error(error.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }, [client, tab, query, project, tag, status, category, trash]);

  const loadContext = useCallback(async () => {
    try {
      const [cal, sum, fil] = await Promise.all([
        client.get(`${API}/calendar?month=${month}`),
        client.get(`${API}/summary`),
        client.get(`${API}/filters`),
      ]);
      setCalendar(cal);
      setSummary(sum);
      setFilters(fil);
    } catch (error) {
      // 摘要与日历失败不影响主列表使用
    }
  }, [client, month]);

  useEffect(() => { loadList(); }, [loadList]);
  useEffect(() => { loadContext(); }, [loadContext]);

  // 切换日期时，日报/周报自动定位到对应周期的记录。
  useEffect(() => {
    if (tab === 'logs') return;
    const selectionVersion = reportSelectionVersion.current;
    let cancelled = false;
    (async () => {
      try {
        const periodStart = tab === 'daily' ? date : weekStart;
        const params = new URLSearchParams({ report_type: tab, date_from: periodStart, date_to: periodStart, page_size: '1' });
        const data = await client.get(`${API}/reports?${params.toString()}`);
        if (!cancelled && selectionVersion === reportSelectionVersion.current) setSelectedReport(data.items[0] || null);
      } catch (error) {
        if (!cancelled && selectionVersion === reportSelectionVersion.current) setSelectedReport(null);
      }
    })();
    return () => { cancelled = true; };
  }, [client, tab, date, weekStart]);

  function chooseReport(value) {
    // An older automatic lookup must not replace a newly created or chosen report.
    reportSelectionVersion.current += 1;
    setSelectedReport(value);
  }

  function guard(action) {
    if (!dirty) {
      action();
      return;
    }
    Modal.confirm({
      title: '当前内容还没有保存',
      content: '离开会丢失未保存的修改。',
      okText: '保存后离开',
      cancelText: '留在当前页',
      onOk: async () => {
        if (!(await saveHandler.current?.())) throw new Error('保存未完成，请重试或留在当前记录');
        setDirty(false);
        action();
      },
      onCancel: () => {},
    });
  }

  function changeTab(next) {
    guard(() => {
      setTab(next);
      setSelectedEntry(null);
      syncUrl(next, date);
    });
  }

  function changeDate(next) {
    guard(() => {
      setDate(next);
      setMonth(monthOf(next));
      setSelectedEntry(null);
      syncUrl(tab, next);
    });
  }

  async function newEntry() {
    guard(() => {
      setSelectedEntry({
        id: null, work_date: date, title: '', body_markdown: '', project: '', category: '测试执行',
        progress_status: 'in_progress', duration_minutes: null, tags: [], outcome_markdown: '',
        blocker_markdown: '', next_step_markdown: '', revision: 1,
      });
    });
  }

  async function createReport(reportType) {
    const periodStart = reportType === 'daily' ? date : weekStart;
    try {
      const created = await client.post(`${API}/reports`, { report_type: reportType, period_start: periodStart });
      chooseReport(created);
      await loadList();
      return created;
    } catch (error) {
      const text = String(error?.message || '');
      if (text.includes('已存在') || text.includes('409')) {
        const params = new URLSearchParams({ report_type: reportType, date_from: periodStart, date_to: periodStart, page_size: '1' });
        const data = await client.get(`${API}/reports?${params.toString()}`);
        const existing = data.items[0];
        if (existing) {
          Modal.confirm({
            title: '这个周期已经有报告了',
            content: existing.deleted_at ? '该报告在回收站中，恢复后可继续编辑。' : '是否打开已有报告继续编辑？',
            okText: existing.deleted_at ? '恢复并打开' : '打开',
            cancelText: '取消',
            onOk: async () => {
              const restored = existing.deleted_at
                ? await client.post(`${API}/reports/${existing.id}/restore`)
                : existing;
              chooseReport(restored);
              await loadList();
            },
          });
          return null;
        }
      }
      message.error(text || '创建失败');
      return null;
    }
  }

  async function openSources() {
    setSourceOpen(true);
    setSourceLoading(true);
    setPreview(null);
    try {
      const periodStart = tab === 'daily' ? date : weekStart;
      const payload = {
        report_type: tab,
        period_start: periodStart,
        include_draft_reports: includeDraft,
        report_id: selectedReport?.id ?? null,
      };
      const data = await client.post(`${API}/assemble-preview`, payload);
      setPreview(data);
    } catch (error) {
      message.error(error.message || '整理失败');
      setSourceOpen(false);
    } finally {
      setSourceLoading(false);
    }
  }

  async function adopt(mode) {
    if (!selectedReport) {
      const created = await createReport(tab === 'daily' ? 'daily' : 'weekly');
      if (!created) return;
    }
    try {
      const reportId = selectedReport?.id ?? (await currentReportId());
      await client.post(`${API}/reports/${reportId}/assemble?mode=${mode}&include_draft_reports=${includeDraft}`, {});
      const refreshed = await client.get(`${API}/reports/${reportId}`);
      chooseReport(refreshed);
      setSourceOpen(false);
      setPreview(null);
      setDirty(false);
      await loadList();
      message.success(mode === 'append' ? '已追加到当前内容' : '已替换为整理的草稿');
    } catch (error) {
      message.error(error.message || '采纳失败');
    }
  }

  async function currentReportId() {
    const periodStart = tab === 'daily' ? date : weekStart;
    const params = new URLSearchParams({ report_type: tab, date_from: periodStart, date_to: periodStart, page_size: '1' });
    const data = await client.get(`${API}/reports?${params.toString()}`);
    return data.items[0]?.id;
  }

  async function restoreEntry(entry) {
    try {
      await client.post(`${API}/entries/${entry.id}/restore`);
      await loadList();
      await loadContext();
    } catch (error) {
      message.error(error.message || '恢复失败');
    }
  }

  async function restoreReport(report) {
    try {
      const restored = await client.post(`${API}/reports/${report.id}/restore`);
      chooseReport(restored);
      setTrash(false);
      await loadList();
    } catch (error) {
      message.error(error.message || '恢复失败');
    }
  }

  const grid = useMemo(() => (calendar ? calendarGrid(calendar.month) : []), [calendar]);
  const marks = useMemo(() => {
    const map = {};
    (calendar?.days || []).forEach((day) => { map[day.date] = day; });
    return map;
  }, [calendar]);

  const grouped = useMemo(() => {
    const buckets = new Map();
    entries.forEach((entry) => {
      const key = entry.work_date;
      if (!buckets.has(key)) buckets.set(key, []);
      buckets.get(key).push(entry);
    });
    return [...buckets.entries()];
  }, [entries]);

  return (
    <div className="work-journal">
      <div className="work-journal__head">
        <div>
          <h2 className="work-journal__title">工作手记</h2>
          <div className="work-journal__tagline">记录工作里的进展，也留住自己的成长</div>
        </div>
        <div className="work-journal__head-actions">
          <Button icon={<FormOutlined />} onClick={newEntry}>记一笔</Button>
          <Button icon={<CalendarOutlined />} onClick={() => { changeTab('daily'); createReport('daily'); }}>写日报</Button>
          <Button type="primary" icon={<CalendarOutlined />} onClick={() => { changeTab('weekly'); createReport('weekly'); }}>写周报</Button>
        </div>
      </div>

      <Segmented
        value={tab}
        onChange={changeTab}
        options={TABS}
        style={{ marginBottom: 10 }}
      />

      <div className="work-journal__summary">
        <span className="work-journal__chip">本周记录 <strong>{summary?.week_entry_count ?? '—'}</strong> 条</span>
        <span className="work-journal__chip">已完成日报 <strong>{summary?.completed_daily_count ?? '—'}</strong> 份</span>
        <span className="work-journal__chip">
          本周周报 <strong>{summary?.weekly_status ? STATUS_LABELS[summary.weekly_status] : '未创建'}</strong>
        </span>
        {trash ? <Tag color="red">回收站模式</Tag> : null}
      </div>

      <div className="work-journal__grid">
        <aside className="work-journal__side">
          <div className="work-journal__side-tools">
            <DatePicker aria-label="工作日期" value={dayjs(date)} allowClear={false} onChange={value=>value && changeDate(value.format('YYYY-MM-DD'))} style={{width:'100%'}}/>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="搜索标题和正文"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onPressEnter={loadList}
            />
            <details className="work-journal__filters"><summary>日历与筛选{project || status || tag || category ? ' · 已筛选' : ''}</summary>
            <Space>
              <Button size="small" icon={<LeftOutlined />} onClick={() => setMonth(shiftMonth(month, -1))} />
              <strong>{month.replace('-', ' 年 ')} 月</strong>
              <Button size="small" icon={<RightOutlined />} onClick={() => setMonth(shiftMonth(month, 1))} />
              <Button size="small" icon={<ReloadOutlined />} onClick={() => { loadList(); loadContext(); }} />
            </Space>
            <div className="work-journal__calendar">
              {WEEKDAYS.map((label) => (
                <div key={label} className="work-journal__calendar-head">{label}</div>
              ))}
              {grid.map((day) => {
                const inMonth = day.startsWith(month);
                const mark = marks[day];
                const inWeek = tab === 'weekly' && day >= weekStart && day <= weekEnd;
                return (
                  <button
                    key={day}
                    type="button"
                    className={[
                      'work-journal__day',
                      inMonth ? '' : 'is-outside',
                      day === shanghaiToday() ? 'is-today' : '',
                      day === date ? 'is-selected' : '',
                      inWeek ? 'is-in-week' : '',
                    ].filter(Boolean).join(' ')}
                    onClick={() => changeDate(day)}
                  >
                    {Number(day.slice(8))}
                    <div>
                      {mark?.entry_count ? <span className="work-journal__dot" /> : null}
                      {mark?.daily_status === 'completed' ? <span className="work-journal__dot work-journal__dot--done" /> : null}
                      {mark?.daily_status === 'draft' ? <span className="work-journal__dot work-journal__dot--draft" /> : null}
                    </div>
                  </button>
                );
              })}
            </div>
            {tab === 'logs' ? (
              <>
                <Space.Compact style={{ width: '100%' }}>
                  <Select
                    allowClear
                    placeholder="项目"
                    value={project}
                    style={{ width: '50%' }}
                    onChange={setProject}
                    options={(filters.projects || []).map((item) => ({ value: item, label: item }))}
                  />
                  <Select
                    allowClear
                    placeholder="状态"
                    value={status}
                    style={{ width: '50%' }}
                    onChange={setStatus}
                    options={Object.entries(PROGRESS_LABELS).map(([value, label]) => ({ value, label }))}
                  />
                </Space.Compact>
                <Space.Compact style={{ width: '100%' }}>
                  <Select
                    allowClear
                    placeholder="标签"
                    value={tag}
                    style={{ width: '50%' }}
                    onChange={setTag}
                    options={(filters.tags || []).map((item) => ({ value: item, label: item }))}
                  />
                  <Select
                    allowClear
                    placeholder="类型"
                    value={category}
                    style={{ width: '50%' }}
                    onChange={setCategory}
                    options={CATEGORIES.map((item) => ({ value: item, label: item }))}
                  />
                </Space.Compact>
              </>
            ) : null}
            </details>
          </div>

          <div className="work-journal__side-scroll">
            {loading ? <div className="work-journal__empty">加载中…</div> : null}
            {!loading && tab === 'logs' && !grouped.length ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={trash ? '回收站是空的' : '还没有记录'}
              >
                {!trash ? <Button type="primary" size="small" onClick={newEntry}>记下今天第一件事</Button> : null}
              </Empty>
            ) : null}
            {!loading && tab === 'logs'
              ? grouped.map(([day, rows]) => (
                <div key={day}>
                  <div className="work-journal__group">{dateLabel(day)}</div>
                  {rows.map((entry) => (
                    <button
                      key={entry.id}
                      type="button"
                      className={`work-journal__item ${selectedEntry?.id === entry.id ? 'is-active' : ''}`}
                      onClick={() => guard(() => setSelectedEntry(entry))}
                    >
                      <span className="work-journal__item-title">{entry.title}</span>
                      <span className="work-journal__item-meta">
                        <Tag color={PROGRESS_TONES[entry.progress_status]} style={{ marginInlineEnd: 0 }}>
                          {PROGRESS_LABELS[entry.progress_status]}
                        </Tag>
                        <span>{entry.category}</span>
                        {entry.project ? <span>{entry.project}</span> : null}
                        {entry.duration_minutes != null ? <span>{entry.duration_minutes} 分钟</span> : null}
                      </span>
                      <span className="work-journal__item-body">{summaryOf(entry.body_markdown) || '（无内容）'}</span>
                    </button>
                  ))}
                </div>
              ))
              : null}

            {!loading && tab !== 'logs'
              ? (reports.length ? reports.map((report) => (
                <button
                  key={report.id}
                  type="button"
                  className={`work-journal__item ${selectedReport?.id === report.id ? 'is-active' : ''}`}
                  onClick={() => guard(() => (trash ? restoreReport(report) : chooseReport(report)))}
                >
                  <span className="work-journal__item-title">
                    {tab === 'daily' ? report.period_start : `${report.period_start} ～ ${report.period_end}`}
                  </span>
                  <span className="work-journal__item-meta">
                    <Tag color={report.status === 'completed' ? 'green' : 'orange'} style={{ marginInlineEnd: 0 }}>
                      {STATUS_LABELS[report.status]}
                    </Tag>
                    {report.deleted_at ? <span>已删除</span> : null}
                  </span>
                </button>
              )) : (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={trash ? '回收站是空的' : `还没有${tab === 'daily' ? '日报' : '周报'}`}>
                  {!trash ? (
                    <Button type="primary" size="small" onClick={() => createReport(tab)}>
                      {tab === 'daily' ? '写今天日报' : '写本周周报'}
                    </Button>
                  ) : null}
                </Empty>
              ))
              : null}
          </div>

          <div className="work-journal__side-foot">
            <span>{tab === 'logs' ? `${entries.length} 条记录` : `${reports.length} 份报告`}</span>
            <Button size="small" type="link" onClick={() => { setTrash(!trash); setSelectedEntry(null); chooseReport(null); }}>
              {trash ? <><UndoOutlined /> 返回</> : <><DeleteOutlined /> 回收站</>}
            </Button>
          </div>
        </aside>

        <main className="work-journal__main">
          {tab === 'logs' ? (
            selectedEntry ? (
              <JournalEditor
                key={selectedEntry.editorKey ?? selectedEntry.id ?? `new-${date}`}
                client={client}
                entry={selectedEntry}
                workDate={date}
                onDirtyChange={setDirty}
                onRegisterSave={(save) => { saveHandler.current = save; }}
                onSaved={(saved) => {
                  setSelectedEntry((current) => (current ? { ...current, ...saved, editorKey: current.editorKey ?? current.id ?? `new-${date}` } : saved));
                  loadList();
                  loadContext();
                }}
                onDeleted={() => { setSelectedEntry(null); loadList(); loadContext(); }}
              />
            ) : (
              <div className="work-journal__card">
                <div className="work-journal__empty">
                  <p>{dateLabel(date)}</p>
                  <Space wrap>
                    <Button type="primary" onClick={newEntry}>记下今天第一件事</Button>
                    <Button onClick={() => { changeTab('daily'); createReport('daily'); }}>写今天日报</Button>
                  </Space>
                </div>
              </div>
            )
          ) : selectedReport ? (
            <ReportEditor
              key={selectedReport.id}
              client={client}
              report={selectedReport}
              onDirtyChange={setDirty}
              onRegisterSave={(save) => { saveHandler.current = save; }}
              onOpenSources={() => guard(openSources)}
              onSaved={(saved) => { chooseReport(saved); loadList(); }}
              onDeleted={() => { chooseReport(null); loadList(); }}
            />
          ) : (
            <div className="work-journal__card">
              <Alert
                type="info"
                showIcon
                style={{ marginBottom: 12 }}
                message={
                  tab === 'daily'
                    ? '这天还没有日报，可以先记录日志再一键整理。'
                    : `本周（${weekStart} ～ ${weekEnd}）还没有周报。`
                }
              />
              <Space wrap>
                <Button type="primary" onClick={() => createReport(tab)}>
                  {tab === 'daily' ? '新建今天日报' : '新建本周周报'}
                </Button>
                {tab === 'logs' ? null : <Button onClick={() => { setTab('logs'); syncUrl('logs', date); }}>去记日志</Button>}
              </Space>
            </div>
          )}
        </main>
      </div>

      <ReportSourcePreview
        open={sourceOpen}
        loading={sourceLoading}
        preview={preview}
        reportType={tab}
        includeDraft={includeDraft}
        hasExistingContent={Boolean(selectedReport && (
          selectedReport.sections?.items?.length
          || selectedReport.sections?.p_items?.length
          || selectedReport.sections?.body
          || String(selectedReport.template_version || '').includes('legacy')
        ))}
        onToggleDraft={(value) => {
          setIncludeDraft(value);
          setSourceLoading(true);
          client.post(`${API}/assemble-preview`, {
            report_type: tab,
            period_start: tab === 'daily' ? date : weekStart,
            include_draft_reports: value,
            report_id: selectedReport?.id ?? null,
          }).then(setPreview).catch((error) => { setPreview(null); message.error(error.message || '来源整理失败，请重试'); }).finally(() => setSourceLoading(false));
        }}
        onAdopt={adopt}
        onCancel={() => { setSourceOpen(false); setPreview(null); }}
      />
    </div>
  );
}
