import React,{useEffect,useMemo,useState} from 'react';
import {Button,Card,Col,Form,Input,Modal,Popconfirm,Row,Select,Space,Table,Tag,Typography,Upload,message} from 'antd';
import {CopyOutlined,DeleteOutlined,EditOutlined,ExportOutlined,ImportOutlined,PlusOutlined} from '@ant-design/icons';
import './api-workspace.css';

const {Title,Text,Paragraph}=Typography;
const BASE='/v1/api-workspace';
const METHODS=['GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS'];
const COLORS={GET:'green',POST:'blue',PUT:'orange',PATCH:'gold',DELETE:'red',HEAD:'purple',OPTIONS:'cyan'};
const QUICK=[
  {name:'API 文档',method:'DOCS',url:`${window.location.origin}/booker/apidoc/index.html`,note:'查看自建接口的全部参数和示例'},
  {name:'Booking 列表',method:'GET',url:`${window.location.origin}/booker/booking`,note:'快速确认自建服务是否可用'},
  {name:'获取 Token',method:'POST',url:`${window.location.origin}/booker/auth`,note:'更新和删除接口需要鉴权'},
];

export function ApiWorkspacePanel({client}){
  const [rows,setRows]=useState([]),[loading,setLoading]=useState(false),[query,setQuery]=useState(''),[editing,setEditing]=useState(null),[form]=Form.useForm();
  async function reload(){setLoading(true);try{setRows(await client.get(`${BASE}/records?q=${encodeURIComponent(query)}`))}catch(e){message.error(e.message)}finally{setLoading(false)}}
  useEffect(()=>{reload()},[query]);
  function openEditor(item=null){setEditing(item||{});form.setFieldsValue(item?{...item,custom_fields:Object.entries(item.custom_fields||{}).map(([key,value])=>({key,value}))}:{method:'GET',tags:[],custom_fields:[]})}
  async function save(){const value=await form.validateFields();const payload={...value,custom_fields:Object.fromEntries((value.custom_fields||[]).filter(x=>x?.key).map(x=>[x.key,x.value||'']))};editing?.id?await client.put(`${BASE}/records/${editing.id}`,payload):await client.post(`${BASE}/records`,payload);message.success('接口记录已保存');setEditing(null);reload()}
  async function remove(id){await client.delete(`${BASE}/records/${id}`);message.success('已删除');reload()}
  async function copy(text){await navigator.clipboard.writeText(text);message.success('地址已复制')}
  const columns=useMemo(()=>[
    {title:'接口',dataIndex:'name',render:(value,row)=><div><b>{value}</b><div className="api-url" title={row.url}>{row.url}</div></div>},
    {title:'方式',dataIndex:'method',width:90,render:value=><Tag color={COLORS[value]}>{value}</Tag>},
    {title:'标签',dataIndex:'tags',width:170,render:tags=><Space wrap size={4}>{(tags||[]).map(x=><Tag key={x}>{x}</Tag>)}</Space>},
    {title:'自定义字段',dataIndex:'custom_fields',width:210,render:fields=><Text type="secondary">{Object.entries(fields||{}).slice(0,2).map(([k,v])=>`${k}: ${v}`).join(' · ')||'—'}</Text>},
    {title:'操作',width:150,render:(_,row)=><Space><Button type="text" icon={<CopyOutlined/>} onClick={()=>copy(row.url)}/><Button type="text" icon={<EditOutlined/>} onClick={()=>openEditor(row)}/><Popconfirm title="删除这条接口记录？" onConfirm={()=>remove(row.id)}><Button type="text" danger icon={<DeleteOutlined/>}/></Popconfirm></Space>},
  ],[]);
  return <div className="api-workspace"><div className="api-heading"><div><Text>调试与积累</Text><Title level={2}>🧪 接口工作台</Title></div><Button type="primary" icon={<PlusOutlined/>} onClick={()=>openEditor()}>记录接口</Button></div>
    <Row gutter={[14,14]} className="quick-grid">{QUICK.map(item=><Col xs={24} md={8} key={item.name}><Card className="quick-api" hoverable><Space><Tag color={COLORS[item.method]||'purple'}>{item.method}</Tag><b>{item.name}</b></Space><Paragraph type="secondary">{item.note}</Paragraph><div className="quick-url">{item.url}</div><Space><Button icon={<CopyOutlined/>} onClick={()=>copy(item.url)}>复制</Button><Button icon={<ExportOutlined/>} onClick={()=>window.open(item.url,'_blank','noopener,noreferrer')}>打开</Button>{item.method!=='DOCS'&&<Button type="link" onClick={()=>openEditor({name:`Restful Booker · ${item.name}`,method:item.method,url:item.url,description:item.note,tags:['学习','Restful Booker'],custom_fields:{}})}>保存到记录</Button>}</Space></Card></Col>)}</Row>
    <Card className="record-card" title="接口记录" extra={<Space><Input.Search allowClear placeholder="搜索名称、地址或说明" onSearch={setQuery}/><Upload accept=".json,.csv" showUploadList={false} customRequest={async({file,onSuccess,onError})=>{const data=new FormData();data.append('file',file);try{const result=await client.post(`${BASE}/imports`,data);message.success(`成功导入 ${result.created} 条，失败 ${result.failed.length} 条`);reload();onSuccess()}catch(e){message.error(e.message);onError(e)}}}><Button icon={<ImportOutlined/>}>导入 JSON/CSV/Postman</Button></Upload></Space>}><Table rowKey="id" loading={loading} columns={columns} dataSource={rows} pagination={{pageSize:10}} scroll={{x:900}}/></Card>
    <Modal open={!!editing} title={editing?.id?'编辑接口':'记录新接口'} onCancel={()=>setEditing(null)} onOk={save} width={720} okText="保存"><Form form={form} layout="vertical"><Row gutter={12}><Col span={16}><Form.Item name="name" label="接口名称" rules={[{required:true}]}><Input placeholder="例如：查询订单详情"/></Form.Item></Col><Col span={8}><Form.Item name="method" label="请求方式" rules={[{required:true}]}><Select options={METHODS.map(value=>({value,label:value}))}/></Form.Item></Col></Row><Form.Item name="url" label="请求地址" rules={[{required:true,type:'url'}]}><Input placeholder="https://api.example.com/orders/{id}"/></Form.Item><Form.Item name="description" label="说明"><Input.TextArea rows={3} placeholder="用途、鉴权方式、注意事项……"/></Form.Item><Form.Item name="tags" label="标签"><Select mode="tags" placeholder="输入后回车，例如：工作、订单、学习"/></Form.Item><div className="custom-title"><b>自定义字段</b><Text type="secondary">可以记录负责人、环境、请求头、请求体示例等</Text></div><Form.List name="custom_fields">{(fields,{add,remove})=><>{fields.map(field=><Space key={field.key} className="custom-row" align="baseline"><Form.Item {...field} name={[field.name,'key']} rules={[{required:true,message:'请输入字段名'}]}><Input placeholder="字段名"/></Form.Item><Form.Item {...field} name={[field.name,'value']}><Input placeholder="字段值"/></Form.Item><Button danger type="text" icon={<DeleteOutlined/>} onClick={()=>remove(field.name)}/></Space>)}<Button type="dashed" block icon={<PlusOutlined/>} onClick={()=>add()}>添加自定义字段</Button></>}</Form.List></Form></Modal>
  </div>
}
