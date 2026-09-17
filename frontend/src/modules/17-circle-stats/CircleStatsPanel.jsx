import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, DatePicker, Form, InputNumber, Space, Table, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
const { Paragraph, Text, Title } = Typography;

const STATUS = { queued:'排队中', running:'执行中', waiting_login:'等待扫码', prepared:'待确认', completed:'已完成', failed:'失败' };

export function CircleStatsPanel({ client }) {
  const [form] = Form.useForm(); const [run,setRun]=useState(null); const [busy,setBusy]=useState(false); const [qr,setQr]=useState('');
  async function refresh(id=run?.id){ if(!id)return; try{const value=await client.get(`/v1/circle-stats/runs/${id}`);setRun(value);if(value.login_screenshot){const f=await client.download(`/v1/circle-stats/runs/${id}/login.png`);setQr(old=>{if(old)URL.revokeObjectURL(old);return URL.createObjectURL(f.blob)})}}catch{} }
  useEffect(()=>{if(!run?.id||['prepared','completed','failed'].includes(run.status))return;const timer=setInterval(()=>refresh(run.id),2000);return()=>clearInterval(timer)},[run?.id,run?.status]);
  async function prepare(values){setBusy(true);try{const [start,end]=values.range;setRun(await client.post('/v1/circle-stats/runs',{start:start.format('YYYY-MM-DD'),end:end.format('YYYY-MM-DD'),row:values.row,max_rows:values.max_rows||null}))}finally{setBusy(false)}}
  async function write(){setBusy(true);try{setRun(await client.post(`/v1/circle-stats/runs/${run.id}/write`,{}))}finally{setBusy(false)}}
  const columns=[{title:'表格行',dataIndex:'target_row',render:(v,_,i)=>v||i+form.getFieldValue('row')},{title:'图片',dataIndex:'images',render:n=>n?`${n} 张`:'无'},{title:'提出人',dataIndex:'author'},{title:'提出时间',dataIndex:'date'},{title:'描述',dataIndex:'description'}];
  return <div className="circle-stats-page">
    <Card className="feature-hero"><Text type="secondary">钉钉协作效率 · 登录状态持久保存</Text><Title level={2}>🫧 全员圈统计</Title><Paragraph>按日期采集全员圈主帖及图片，先预览，再确认写入“全员圈统计”表。多张图片会合成一张后写入 D 列，评论不会被统计。</Paragraph></Card>
    <Card title="创建统计任务">
      <Form form={form} layout="vertical" initialValues={{range:[dayjs().subtract(7,'day'),dayjs()],row:2}} onFinish={prepare}>
        <Space wrap align="end"><Form.Item name="range" label="统计日期" rules={[{required:true}]}><DatePicker.RangePicker disabledDate={d=>d&&d>dayjs().endOf('day')} /></Form.Item><Form.Item name="row" label="表格起始行" rules={[{required:true}]}><InputNumber min={2}/></Form.Item><Form.Item name="max_rows" label="最多可用行（可选）"><InputNumber min={1}/></Form.Item><Form.Item><Button type="primary" htmlType="submit" loading={busy} disabled={run&&!['completed','failed'].includes(run.status)}>采集并预览</Button></Form.Item></Space>
      </Form>
      {run&&<Alert showIcon type={run.status==='failed'?'error':run.status==='completed'?'success':'info'} message={<Space><Tag>{STATUS[run.status]||run.status}</Tag>{run.message}</Space>} />}
      {run?.status==='waiting_login'&&qr&&<div className="circle-login"><img src={qr} alt="钉钉登录二维码"/><div><Title level={4}>请用钉钉扫码</Title><Paragraph>扫码完成后无需刷新，任务会自动继续。</Paragraph></div></div>}
    </Card>
    {run?.preview&&<Card title={`写入预览（${run.preview.length} 条）`} extra={<Button type="primary" danger onClick={write} loading={busy} disabled={run.status!=='prepared'}>确认写入在线表格</Button>}><Alert type="warning" showIcon message="点击确认写入会修改在线表格；系统会检查空白单元格并逐格回读。"/><Table rowKey={(_,i)=>i} columns={columns} dataSource={run.preview} pagination={{pageSize:10}} scroll={{x:720}} /></Card>}
  </div>;
}
