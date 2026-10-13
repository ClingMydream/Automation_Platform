// File purpose: 汇总来源选择与候选预览弹窗（日报"从当日日志整理"、周报"根据日报生成"共用）。
// How to change: 只负责展示候选与选择；真正写库由父组件调用 assemble 接口完成。

import { Alert, Button, Checkbox, Empty, Modal, Space, Tag } from 'antd';
import { chineseIndex, PROGRESS_LABELS, STATUS_LABELS } from './workJournalUtils.js';

// 阅读态统一用 React 元素渲染，绝不注入 HTML，避免执行报告里的原始标签和危险链接。
function DailyPreview({ sections }) {
  const items = sections?.items || [];
  return (
    <div className="work-journal__text">
      <div className="work-journal__label">今日完成</div>
      {items.length ? (
        items.map((item, index) => (
          <div key={item.item_id || index} className="work-journal__ro-item">
            <div className="work-journal__ro-name">
              事项{chineseIndex(index + 1)}：{item.name}
              {item.project ? <span className="work-journal__flag">{item.project}</span> : null}
            </div>
            <div className="work-journal__ro-line">
              <span className="work-journal__ro-bullet">●</span>进展：{item.progress || '未填写'}
            </div>
            <div className="work-journal__ro-line">
              <span className="work-journal__ro-bullet">●</span>结果：{item.result || '结果待确认'}
            </div>
            <div className="work-journal__sub">状态：{PROGRESS_LABELS[item.status] || item.status || '未填写'}</div>
          </div>
        ))
      ) : (
        <div className="work-journal__hint">当天没有可整理的日志</div>
      )}
      <div className="work-journal__label">测试与质量</div>
      <div>{sections?.quality || '未填写'}</div>
      <div className="work-journal__label">风险与阻碍</div>
      <div>{(sections?.blockers || []).map((row) => row.text).join('；') || '未填写'}</div>
      <div className="work-journal__label">明日计划</div>
      <div>{(sections?.next_plan || []).map((row) => row.text).join('；') || '未填写'}</div>
      <div className="work-journal__label">成长与复盘</div>
      <div>{sections?.reflection || '未填写'}</div>
    </div>
  );
}

function WeeklyPreview({ sections }) {
  const pItems = sections?.p_items || [];
  const rItems = sections?.r_items || [];
  const oItems = sections?.o_items || [];
  return (
    <div className="work-journal__text">
      <div className="work-journal__ro-heading"># P-核心进展与结果:</div>
      {pItems.length ? (
        pItems.map((item, index) => (
          <div key={item.item_id || index} className="work-journal__ro-item">
            <div className="work-journal__ro-name">
              事项{chineseIndex(index + 1)}：{item.name}
              {item.project ? <span className="work-journal__flag">{item.project}</span> : null}
              {item.result_conflict ? <span className="work-journal__flag">结果存在差异</span> : null}
            </div>
            <div className="work-journal__ro-line">
              <span className="work-journal__ro-bullet">●</span>进展：{item.progress || '未填写'}
            </div>
            <div className="work-journal__ro-line">
              <span className="work-journal__ro-bullet">●</span>结果：{item.result || '结果待确认'}
            </div>
          </div>
        ))
      ) : (
        <div className="work-journal__hint">本周没有可归并的事项</div>
      )}
      <div className="work-journal__ro-heading"># R-需要关注的风险与问题:</div>
      {rItems.map((item, index) => (
        <div key={item.id || index} className="work-journal__ro-line">
          <span className="work-journal__ro-bullet">●</span>
          {item.text}
        </div>
      ))}
      <div className="work-journal__ro-heading"># O-下周核心目标与计划:</div>
      {oItems.map((item, index) => (
        <div key={item.id || index} className="work-journal__ro-line">
          <span className="work-journal__ro-bullet">●</span>
          {item.text}
        </div>
      ))}
    </div>
  );
}

export function ReportSourcePreview({
  open, loading, preview, reportType, includeDraft, onToggleDraft, onAdopt, onCancel, hasExistingContent,
}) {
  const refs = preview?.source_refs || [];
  const already = new Set(preview?.already_referenced || []);
  return (
    <Modal
      open={open}
      title={reportType === 'daily' ? '从当日日志整理' : '根据日报生成周报'}
      onCancel={onCancel}
      width={860}
      footer={
        <Space wrap>
          <Button onClick={onCancel}>取消</Button>
          <Button onClick={() => onAdopt('append')} disabled={!preview}>
            {hasExistingContent ? '追加到当前内容' : '采纳为草稿'}
          </Button>
          <Button type="primary" danger onClick={() => onAdopt('replace')} disabled={!preview || !hasExistingContent}>
            替换为此草稿
          </Button>
        </Space>
      }
      styles={{ body: { maxHeight: 'calc(100vh - 240px)', overflowY: 'auto', overflowX: 'hidden' } }}
      destroyOnHidden
    >
      {loading ? <div className="work-journal__empty">正在整理…</div> : null}
      {!loading && !preview ? <Empty description="暂无来源" /> : null}
      {!loading && preview ? (
        <>
          <Space wrap style={{ marginBottom: 10 }}>
            <Tag color="purple">来源 {preview.source_count} 份</Tag>
            <Tag>依据日期 {preview.period_start} ～ {preview.period_end}</Tag>
            {preview.totals?.duration_minutes != null ? <Tag>合计工时 {preview.totals.duration_minutes} 分钟</Tag> : null}
            {reportType === 'weekly' ? (
              <Checkbox checked={includeDraft} onChange={(event) => onToggleDraft(event.target.checked)}>
                纳入草稿日报
              </Checkbox>
            ) : null}
          </Space>

          {(preview.warnings || []).map((text) => (
            <Alert key={text} type="warning" showIcon message={text} style={{ marginBottom: 8 }} />
          ))}
          {preview.missing_dates?.length ? (
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 8 }}
              message={`缺少日报的日期：${preview.missing_dates.join('、')}`}
            />
          ) : null}
          {preview.as_of ? <Alert type="info" showIcon style={{ marginBottom: 8 }} message={`截至 ${preview.as_of}`} /> : null}

          <div className="work-journal__label">候选正文预览</div>
          <div className="work-journal__block" style={{ background: '#fff' }}>
            {preview.report_type === 'daily' ? <DailyPreview sections={preview.sections} /> : <WeeklyPreview sections={preview.sections} />}
          </div>

          <div className="work-journal__label" style={{ marginTop: 12 }}>来源明细</div>
          {refs.length ? (
            refs.map((ref, index) => {
              const key = ref.report_id ?? ref.entry_id ?? index;
              const used = already.has(ref.entry_id) || already.has(ref.report_id);
              return (
                <div key={`${key}-${index}`} className="work-journal__source">
                  <div className="work-journal__source-head">
                    <Tag color={ref.status === 'draft' ? 'orange' : 'green'}>
                      {ref.kind === 'entry' ? '日志' : STATUS_LABELS[ref.status] || '日报'}
                    </Tag>
                    <span>{ref.work_date}</span>
                    <span>{ref.title}</span>
                    {used ? <Tag color="blue">已引用</Tag> : null}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="work-journal__hint">没有来源</div>
          )}
        </>
      ) : null}
    </Modal>
  );
}
