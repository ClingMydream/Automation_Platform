import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Alert, Button, Card, Checkbox, Col, DatePicker, Empty, Form, Input, InputNumber, List, Modal, Progress, Row, Select, Space, Statistic, Tabs, Tag, Typography, Upload, message } from 'antd';
import { DeleteOutlined, FolderAddOutlined, PlusOutlined, PushpinFilled, SaveOutlined, UploadOutlined } from '@ant-design/icons';
import Editor from '@toast-ui/editor';
import '@toast-ui/editor/dist/toastui-editor.css';
import dayjs from 'dayjs';
import './learning.css';
import './learning-refinement.css';
import { getLearningGuide } from './learningGuides.js';

const { Text, Title, Paragraph } = Typography;
const API='/v1/learning';

function MarkdownEditor({value,onChange,onImage}) {
  const host=useRef(null), editor=useRef(null), onChangeRef=useRef(onChange);
  useEffect(()=>{onChangeRef.current=onChange},[onChange]);
  useEffect(()=>{
    editor.current=new Editor({el:host.current,height:'560px',initialEditType:'wysiwyg',previewStyle:'vertical',initialValue:value||'',usageStatistics:false,
      hooks:{addImageBlobHook:async(blob,callback)=>{const url=await onImage(blob); callback(url,blob.name||'图片')}}});
    editor.current.on('change',()=>onChangeRef.current(editor.current.getMarkdown()));
    return()=>editor.current?.destroy();
  },[]);
  return <div ref={host}/>;
}

function explainCodeLine(line) {
  const text=line.trim();
  if(!text)return '空行：把不同代码段分开，便于阅读。';
  if(text.startsWith('#'))return '注释：只用于解释代码，Python 不会执行这一行。';
  if(text.startsWith('import ')||text.startsWith('from '))return '导入：使用其他模块已经提供的功能。';
  if(text.startsWith('class '))return '定义类：把相关的数据和方法放进一个可复用的客户端模板。';
  if(text.startsWith('def '))return '定义方法：以后调用这个名字，就会执行下面缩进的代码。';
  if(text.startsWith('@pytest.fixture'))return '装饰器：告诉 pytest，下面的方法用于准备测试资源。';
  if(text.startsWith('self.'))return '保存到当前客户端对象中，其他方法可以继续使用这个值。';
  if(text.startsWith('if '))return '条件判断：只有条件成立时才执行下面缩进的代码。';
  if(text.startsWith('yield '))return '先把资源交给测试使用；测试结束后继续执行 yield 后面的清理代码。';
  if(text.startsWith('return '))return '返回结果：把这一行得到的数据交给调用它的位置。';
  if(text.startsWith('assert '))return '断言：检查实际结果是否符合预期，不符合时用例失败。';
  if(text.includes('requests.Session'))return '创建 Session：复用连接，并统一保存公共请求头。';
  if(text.includes('kwargs.setdefault'))return '如果调用时没有单独传 timeout，就使用客户端的默认超时。';
  if(text.includes('session.request'))return '真正发送 HTTP 请求；method 决定 GET、POST、PUT 或 DELETE。';
  if(text.includes('headers.update'))return '把公共请求头保存到 Session，后续请求自动携带。';
  if(text.includes('response.json'))return '把服务器返回的 JSON 文本转换成 Python 数据。';
  if(text.startsWith('pytest '))return '在终端执行 pytest，并显示测试结果。';
  if(text.startsWith('python '))return '在终端执行 Python 命令；不要写进 .py 文件。';
  return '执行这一行，并观察它使用了哪些变量、产生了什么结果。';
}

function commentPrefix(line) {
  const text=line.trim().toUpperCase();
  if(/^(SELECT|INSERT|UPDATE|DELETE FROM|CREATE TABLE|ALTER TABLE|EXPLAIN)/.test(text))return '--';
  if(/^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+\//.test(text))return '#';
  return '#';
}

function BeginnerCode({code}) {
  const commented=String(code).split('\n').flatMap(line=>{
    if(!line.trim())return [''];
    if(line.trim().startsWith('#')||line.trim().startsWith('--'))return [line];
    return [`${commentPrefix(line)} ${explainCodeLine(line)}`,line];
  }).join('\n');
  return <pre className="guide-code inline-comment-code"><code>{commented}</code></pre>;
}

const PRACTICE_PROJECTS = [
  ['酒店预约前台', 'https://automationintesting.online/', '像普通用户一样浏览房间、填写资料并完成预约'],
  ['酒店管理后台', 'https://automationintesting.online/#/admin', '观察房间、预约、消息等后台业务；练习站默认账号可在页面底部查看'],
  ['Restful Booker API 文档', 'https://restful-booker.herokuapp.com/apidoc/index.html', '查看纯 API 的地址、方法、参数和响应示例'],
];

const DOCUMENT_LESSONS = {
  1: {
    idea: '先把自己当成订房用户。今天不写代码，只认识业务页面和一条完整预约流程。',
    steps: ['打开“酒店预约前台”', '从房间列表选择一个可预订房间', '选择入住和离店日期', '填写姓名、邮箱和电话', '提交预约并保存成功或失败截图'],
    expected: '能说清楚自己输入了哪些数据、点击了什么按钮、页面最后返回了什么。',
    fill: '我选择的房间是____；入住日期是____；提交后页面显示____。',
    exercise: '故意漏填一个必填项再提交，记录页面如何提示，并判断这个校验发生在前端还是后端。',
  },
  2: {
    idea: '前端是你看到和操作的页面，后端处理业务，数据库保存房间和预约数据。',
    steps: ['再次完成一笔预约', '写下页面收集的字段', '画出“页面→接口→后端→数据库”的箭头', '刷新页面观察数据是否仍存在'],
    expected: '能够不用术语堆砌，用订房例子解释前端、后端和数据库。',
    fill: '用户在____输入资料，____接收请求并处理，最后把数据保存到____。',
    exercise: '假设页面显示成功但数据库没有预约，分别列出前端、接口和数据库可能出现的问题。',
  },
  3: {
    idea: 'API 可以理解为前端和后端约定好的“办事窗口”：前端按格式提交，后端按格式回答。',
    steps: ['打开纯 API 的 Booking 列表地址', '观察浏览器显示的 JSON', '找到 bookingid 字段', '对比酒店页面和纯接口页面的区别'],
    expected: '能解释请求、响应、接口地址和 JSON 分别是什么。',
    fill: '浏览器向____发送请求，服务器返回____，其中 bookingid 表示____。',
    exercise: '把接口地址最后加上一个真实 bookingid，预测结果后再打开验证。',
  },
  4: {
    idea: '请求方法表示想对数据做什么：GET 查询、POST 新增、PUT 修改、DELETE 删除。',
    steps: ['打开 API 文档', '分别找到 GetBookingIds 和 CreateBooking', '记录它们的方法和路径', '用自己的话描述四种方法'],
    expected: '看到业务动作时，能选择大致正确的 HTTP 请求方法。',
    fill: '查询使用____；新增使用____；整体修改使用____；删除使用____。',
    exercise: '为“查询房间、创建预约、修改姓名、取消预约”分别选择请求方法。',
  },
  5: {
    idea: 'Network 是浏览器的请求记录本，可以看到点击按钮后页面实际调用了什么接口。',
    steps: ['在酒店前台按 F12', '选择 Network / 网络', '刷新页面', '筛选 Fetch/XHR', '点击一条请求查看 Headers、Payload 和 Response'],
    expected: '能在 Network 中找到请求地址、方法、状态码和响应内容。',
    fill: '我观察的请求方法是____，地址是____，状态码是____。',
    exercise: '提交 Contact 表单，找到对应请求并截图标出 Request URL 和 Status Code。',
  },
};

function DocumentLesson({task}) {
  const [step,setStep]=useState(0);
  const lesson=DOCUMENT_LESSONS[task.day_number]||{
    idea:task.details,
    steps:['阅读今天的概念说明并写一句自己的理解','按示例完整跟做一次','对照预期结果检查','修改一个输入再次运行','把错误和解决过程保存到学习笔记'],
    expected:task.acceptance_criteria,
    fill:'今天要解决的问题是____；我的输入是____；得到的结果是____。',
    exercise:`不看示例重新完成“${task.title}”，再主动改变一个条件并解释结果。`,
  };
  const pages=[
    ['先理解',<><Tag color="green">今天不要求背诵</Tag><Title level={4}>{task.title}</Title><Paragraph>{lesson.idea}</Paragraph><Alert type="info" showIcon title="先理解业务，再学习工具，最后才写自动化代码。"/></>],
    ['打开练习项目',<Row gutter={[12,12]}>{PRACTICE_PROJECTS.map(([name,url,note])=><Col xs={24} md={8} key={name}><Card size="small" title={name}><Paragraph>{note}</Paragraph><Button type="primary" href={url} target="_blank">打开项目 ↗</Button></Card></Col>)}</Row>],
    ['跟着操作',<ol className="daily-actions">{lesson.steps.map((item,index)=><li key={item}><span>{index+1}</span><div><b>{item}</b><small>只完成当前一步，完成后再继续；结果与说明不同也要截图保存。</small></div></li>)}</ol>],
    ['对照结果',<><div className="acceptance-box"><b>预期结果</b><Paragraph>{lesson.expected}</Paragraph></div><Paragraph>不要只看“成功还是失败”，还要写下输入、操作、实际结果三部分。</Paragraph></>],
    ['填空练习',<><Paragraph>先不看前面的文字，补全下面的学习记录：</Paragraph><pre className="guide-code"><code>{lesson.fill}</code></pre><Paragraph type="secondary">不会时允许返回上一页查找，找到答案后再用自己的话重写。</Paragraph></>],
    ['独立小题',<><div className="practice-level"><Tag color="orange">现在关闭答案</Tag><Paragraph>{lesson.exercise}</Paragraph></div><Alert type="warning" showIcon title="卡住 15 分钟后再看提示；报错内容本身也是学习材料。"/></>],
    ['验收与复盘',<><div className="acceptance-box"><b>完成标准</b><Paragraph>{task.acceptance_criteria}</Paragraph></div><Paragraph>保存一个操作结果、一张关键截图和一段自己的解释，然后勾选今日任务并完成打卡。</Paragraph></>],
  ];
  return <Card className="guide-card" title={`📖 第 ${task.day_number} 天文档课 · ${task.title}`}><div className="guide-steps">{pages.map((item,index)=><button key={item[0]} className={step===index?'active':''} onClick={()=>setStep(index)}><span>{index+1}</span>{item[0]}</button>)}</div><div className="guide-content">{pages[step][1]}<Space><Button disabled={!step} onClick={()=>setStep(step-1)}>上一步</Button><Button type="primary" disabled={step===pages.length-1} onClick={()=>setStep(step+1)}>下一步</Button></Space></div></Card>;
}

function DayOneGuide() {
  const [step, setStep] = useState(0);
  const steps = [
    { title: '确认练习接口', body: <><Paragraph>Restful Booker 是专门练习接口测试的公开服务，不需要注册。</Paragraph><a href="https://restful-booker.herokuapp.com/apidoc/index.html" target="_blank" rel="noreferrer">打开 API 文档 ↗</a><div className="endpoint-box"><code>GET https://restful-booker.herokuapp.com/booking</code></div><Paragraph type="secondary">先访问这个地址；看到 bookingid 列表就说明接口可用。</Paragraph></> },
    { title: '配置 Python', body: <><Paragraph>安装 Python 3.11 或 3.12，并勾选 Add Python to PATH。打开 PowerShell，逐行执行并对照右侧说明：</Paragraph><BeginnerCode code={`python --version\nmkdir restful-booker-tests\ncd restful-booker-tests\npython -m venv .venv\n.\\.venv\\Scripts\\Activate.ps1\npython -m pip install pytest requests`}/><Paragraph type="secondary">若 PowerShell 阻止激活，先执行：<code>Set-ExecutionPolicy -Scope CurrentUser RemoteSigned</code></Paragraph></> },
    { title: '配置 Postman', body: <><Paragraph><Tag color="orange">使用英文界面</Tag>Postman 官方目前没有简体中文，不需要安装第三方汉化包。按照下面的英文按钮操作即可：</Paragraph><ol className="postman-steps"><li>点击 <b>New（新建）</b></li><li>选择 <b>HTTP Request（HTTP 请求）</b></li><li>请求方法选择 <b>GET（查询）</b></li><li>在地址栏粘贴下面的 URL</li><li>点击 <b>Send（发送）</b></li></ol><div className="endpoint-box"><code>https://restful-booker.herokuapp.com/booking/1</code></div><Paragraph><b>验收：</b>在下方 <b>Response（响应）</b>区域看到 <b>Status: 200 OK（状态码成功）</b>，Body 中包含 firstname、lastname 和 bookingdates。若 ID 1 不存在，先请求 <code>/booking</code> 列表并换一个 ID。</Paragraph><div className="postman-glossary"><Tag>Params 参数</Tag><Tag>Authorization 认证</Tag><Tag>Headers 请求头</Tag><Tag>Body 请求体</Tag><Tag>Tests 测试脚本</Tag><Tag>Save 保存</Tag></div></> },
    { title: '首个 pytest 用例', body: <><Paragraph>在项目目录创建 <code>test_booking.py</code>，逐行输入并理解右侧说明：</Paragraph><BeginnerCode code={`import requests\n\nBASE_URL = "https://restful-booker.herokuapp.com"\n\ndef test_get_booking_list():\n    response = requests.get(f"{BASE_URL}/booking", timeout=10)\n    assert response.status_code == 200\n    bookings = response.json()\n    assert isinstance(bookings, list)\n    assert len(bookings) > 0\n    assert "bookingid" in bookings[0]`}/><Paragraph>执行 <code>pytest -v</code>。看到 <Tag color="green">1 passed</Tag> 即完成，并把结果与三个断言的含义写进学习笔记。</Paragraph></> },
  ];
  const item = steps[step];
  return <Card className="guide-card" title="🧭 第 1 天执行引导" extra={<Text type="secondary">60–90 分钟</Text>}><div className="guide-steps">{steps.map((x,i)=><button key={x.title} className={i===step?'active':''} onClick={()=>setStep(i)}><span>{i+1}</span>{x.title}</button>)}</div><div className="guide-content"><Title level={4}>{step+1}. {item.title}</Title>{item.body}<Space><Button disabled={!step} onClick={()=>setStep(step-1)}>上一步</Button><Button type="primary" disabled={step===steps.length-1} onClick={()=>setStep(step+1)}>下一步</Button></Space></div></Card>;
}

function ClientWrapperGuide({task}) {
  const [step,setStep]=useState(0);
  const pages=[
    {title:'搭建项目结构',body:<><Paragraph>目标不是简单写一个函数，而是把“HTTP 通用能力”和“Restful Booker 业务接口”集中到客户端中，让测试用例只表达测试意图。</Paragraph><pre className="guide-code"><code>{`restful-booker-tests/
├─ api/
│  ├─ __init__.py
│  └─ booker_client.py
├─ tests/
│  ├─ __init__.py
│  ├─ conftest.py
│  └─ test_booking.py
└─ requirements.txt`}</code></pre><Paragraph>PowerShell 创建目录：</Paragraph><pre className="guide-code"><code>{`mkdir api, tests
New-Item api/__init__.py, tests/__init__.py -ItemType File
New-Item api/booker_client.py, tests/conftest.py, tests/test_booking.py -ItemType File`}</code></pre></>},
    {title:'封装通用请求层',body:<><Paragraph>在 <code>api/booker_client.py</code> 中先统一处理 Base URL、Session、超时和请求入口：</Paragraph><pre className="guide-code"><code>{`import requests


class BookerClient:
    def __init__(self, base_url="https://restful-booker.herokuapp.com", timeout=10, headers=None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        default_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if headers:
            default_headers.update(headers)
        self.session.headers.update(default_headers)

    def request(self, method, path, **kwargs):
        """所有接口统一从这里发送，后续可集中添加日志和重试。"""
        url = f"{self.base_url}/{path.lstrip('/')}"
        kwargs.setdefault("timeout", self.timeout)
        return self.session.request(method, url, **kwargs)

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def put(self, path, **kwargs):
        return self.request("PUT", path, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)

    def close(self):
        self.session.close()`}</code></pre><div className="explain-box"><b>为什么这样封装？</b><ul><li><code>Session</code> 复用连接和公共请求头。</li><li><code>rstrip/lstrip</code> 防止地址出现双斜杠。</li><li>统一 <code>timeout</code>，避免请求无限等待。</li><li>这里不调用 <code>raise_for_status()</code>，因为异常状态码也是接口测试需要断言的结果。</li></ul></div></>},
    {title:'封装业务接口',body:<><Paragraph>继续在 <code>BookerClient</code> 类中添加业务方法。测试用例以后不再手工拼 URL：</Paragraph><pre className="guide-code"><code>{`    def get_bookings(self, **params):
        return self.get("/booking", params=params)

    def get_booking(self, booking_id):
        return self.get(f"/booking/{booking_id}")

    def create_booking(self, payload):
        return self.post("/booking", json=payload)

    def create_token(self, username, password):
        response = self.post(
            "/auth",
            json={"username": username, "password": password},
        )
        assert response.status_code == 200
        return response.json()["token"]

    def update_booking(self, booking_id, payload, token):
        return self.put(
            f"/booking/{booking_id}", json=payload,
            headers={"Cookie": f"token={token}"},
        )

    def delete_booking(self, booking_id, token):
        return self.delete(
            f"/booking/{booking_id}",
            headers={"Cookie": f"token={token}"},
        )`}</code></pre><Paragraph type="secondary">这里的方法名表达业务动作；请求方式、路径、鉴权细节由客户端管理。</Paragraph></>},
    {title:'重写已有用例',body:<><Paragraph>下面是同一个查询用例封装前后的对比。先看旧写法：</Paragraph><pre className="guide-code"><code>{`# 旧写法：每个用例都要重复导入 requests、拼地址、写 timeout
import requests


def test_get_booking_list():
    base_url = "https://restful-booker.herokuapp.com"
    response = requests.get(
        f"{base_url}/booking",
        headers={"Accept": "application/json"},
        timeout=10,
    )
    assert response.status_code == 200`}</code></pre><Paragraph>再改成客户端写法：</Paragraph><pre className="guide-code"><code>{`# 新写法：用例只关心“查询预订列表”和结果
from api.booker_client import BookerClient


def test_get_booking_list():
    client = BookerClient()
    response = client.get_bookings()

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    client.close()`}</code></pre><div className="explain-box"><b>具体删掉和替换了什么？</b><ol><li>删除测试文件里的 <code>import requests</code>。</li><li>删除重复的 <code>base_url</code>、<code>headers</code> 和 <code>timeout</code>。</li><li>把 <code>requests.get(...)</code> 换成 <code>client.get_bookings()</code>。</li><li>断言保留在测试用例中，因为“预期结果”属于测试，不属于客户端。</li></ol></div><Paragraph type="secondary"><code>**kwargs</code> 可以先理解为“把额外参数原样继续传下去”。例如 <code>params</code>、<code>json</code>、<code>headers</code> 都能经过它传给 requests。</Paragraph></>},
    {title:'完整代码逐行看',body:<><Paragraph>把下面完整内容放进 <code>api/booker_client.py</code>。右侧是每一行的中文解释，先照着写，再逐行对照。</Paragraph><BeginnerCode code={`import requests

class BookerClient:
    def __init__(self, base_url="https://restful-booker.herokuapp.com", timeout=10, headers=None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        default_headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if headers:
            default_headers.update(headers)
        self.session.headers.update(default_headers)

    def request(self, method, path, **kwargs):
        url = f"{self.base_url}/{path.lstrip('/')}"
        kwargs.setdefault("timeout", self.timeout)
        return self.session.request(method, url, **kwargs)

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def put(self, path, **kwargs):
        return self.request("PUT", path, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)

    def get_bookings(self, **params):
        return self.get("/booking", params=params)

    def get_booking(self, booking_id):
        return self.get(f"/booking/{booking_id}")

    def create_booking(self, payload):
        return self.post("/booking", json=payload)

    def close(self):
        self.session.close()`}/><Paragraph type="secondary">注意：Python 使用缩进表示代码属于哪个方法。类里面的方法缩进 4 个空格，方法里的内容再缩进 4 个空格。</Paragraph></>},
    {title:'模仿、思考和小题',body:<><div className="practice-level"><Tag color="green">第 1 轮：照着模仿</Tag><Paragraph>不要改代码，逐行输入完整客户端，然后运行原有查询用例。目标是熟悉文件位置、缩进和调用方式。</Paragraph></div><div className="practice-level"><Tag color="blue">第 2 轮：带着思考改</Tag><Paragraph>把默认 <code>timeout=10</code> 改成 <code>timeout=15</code>。思考：为什么测试用例不需要跟着修改？再添加公共请求头 <code>X-Student: cling</code>，观察它应该写在哪一处。</Paragraph></div><div className="practice-level"><Tag color="orange">第 3 轮：自己完成小题</Tag><Paragraph>不看上面的答案，自己添加一个 <code>patch</code> 方法，并添加业务方法 <code>partial_update_booking</code>。要求测试文件里不能出现 <code>requests.patch</code> 和完整 Base URL。</Paragraph><div className="acceptance-box"><b>参考验收</b><Paragraph><code>patch</code> 方法调用 <code>self.request("PATCH", path, **kwargs)</code>；业务方法调用 <code>self.patch(...)</code>，测试仍然只负责准备数据和断言。</Paragraph></div></div></>},
    {title:'Fixture 与运行验收',body:<><Paragraph>手动创建和关闭客户端仍会重复，因此在 <code>tests/conftest.py</code> 中使用 Fixture：</Paragraph><pre className="guide-code"><code>{`import pytest
from api.booker_client import BookerClient


@pytest.fixture
def booker_client():
    client = BookerClient()
    yield client
    client.close()`}</code></pre><Paragraph>在 <code>tests/test_booking.py</code> 中使用客户端：</Paragraph><pre className="guide-code"><code>{`def test_get_booking_list(booker_client):
    response = booker_client.get_bookings()

    assert response.status_code == 200
    bookings = response.json()
    assert isinstance(bookings, list)
    assert len(bookings) > 0
    assert "bookingid" in bookings[0]


def test_unknown_booking(booker_client):
    response = booker_client.get_booking(999999999)
    assert response.status_code == 404`}</code></pre><pre className="guide-code"><code>pytest -v --tb=short</code></pre><div className="acceptance-box"><b>验收标准</b><Paragraph>两个用例通过；测试文件里没有 Base URL、Session 和重复的 requests.get；你能解释 request 通用层与 get_booking 业务方法各自负责什么。</Paragraph></div></>},
  ];
  const page=pages[step];
  return <Card className="guide-card" title={`🧭 第 ${task.day_number} 天执行引导 · Python 请求封装`} extra={<Text type="secondary">建议 3–4 小时</Text>}><div className="guide-steps">{pages.map((item,index)=><button key={item.title} className={index===step?'active':''} onClick={()=>setStep(index)}><span>{index+1}</span>{item.title}</button>)}</div><div className="guide-content"><Title level={4}>{step+1}. {page.title}</Title>{page.body}<Space><Button disabled={!step} onClick={()=>setStep(step-1)}>上一步</Button><Button type="primary" disabled={step===pages.length-1} onClick={()=>setStep(step+1)}>下一步</Button></Space></div></Card>;
}

function DailyExecutionGuide({task}) {
  const [step,setStep]=useState(0);
  if(task.category==='文档实操')return <DocumentLesson task={task}/>;
  if(task.day_number===1)return <DayOneGuide/>;
  if(task.day_number===3)return <ClientWrapperGuide task={task}/>;
  const guide=getLearningGuide(task.day_number);
  const pages=[
    {title:'1. 先理解概念',body:<><Tag color="green">不要求提前会代码</Tag><Paragraph className="beginner-lead">本节主题：{guide.topic}</Paragraph><Paragraph>学完要做到：{guide.outcome}</Paragraph><div className="daily-goal"><Tag color="purple">第 {task.day_number} 天</Tag><Tag color="blue">{task.phase}</Tag><Tag>{task.expected_minutes} 分钟</Tag></div><div className="explain-box"><b>学习方法</b><Paragraph>第一遍只要求看懂输入和输出；第二遍照着做；第三遍再尝试修改。遇到陌生词先记到笔记，不需要强行背诵。</Paragraph></div></>},
    {title:'2. 准备环境和文件',body:<><Paragraph>开始前先准备工作目录、练习文件和当天需要的工具。按顺序检查：</Paragraph><ol className="daily-actions">{guide.actions.slice(0,2).map((action,index)=><li key={action}><span>{index+1}</span><div><b>{action}</b><small>完成后保留文件或截图，确认准备工作真实完成。</small></div></li>)}</ol><Paragraph type="secondary">如果今天不是编码课程，就新建一篇同名学习笔记，用来保存操作步骤、结果和问题。</Paragraph></>},
    {title:'3. 一步一步操作',body:<ol className="daily-actions">{guide.actions.map((action,index)=><li key={action}><span>{index+1}</span><div><b>{action}</b><small>只做当前一步；执行前预测结果，执行后对比实际结果，报错时保留完整错误文字。</small></div></li>)}</ol>},
    {title:'4. 带注释完整示例',body:<><Paragraph>注释已经直接写进代码块，可以连同代码一起复制。Python 和命令使用 <code>#</code>，SQL 使用 <code>--</code>：</Paragraph><BeginnerCode code={guide.commands.join('\n')}/><Paragraph type="secondary">注释不会改变程序运行结果。第一次保留注释练习，熟练后再尝试删掉注释独立完成。</Paragraph></>},
    {title:'5. 拆开理解和改写',body:<><div className="explain-box"><b>逐步拆解</b><ol>{guide.actions.map((action,index)=><li key={action}><b>第 {index+1} 步：</b>{action}。思考它接收什么输入、产生什么输出，以及下一步为什么需要它。</li>)}</ol></div><Paragraph><b>改写要求：</b>用自己的变量名、文件名或业务例子重新写一遍，但保持执行顺序和核心逻辑不变。改完后与原示例对比，不要只看是否报错。</Paragraph></>},
    {title:'6. 第一轮照着模仿',body:<><div className="practice-level"><Tag color="green">允许看答案</Tag><Paragraph>完整照着示例输入并运行。不要整段无脑粘贴：每输入一行，先读它的注释，再说出这一行大概做什么。</Paragraph></div><div className="acceptance-box"><b>本轮目标</b><Paragraph>得到与示例一致的结果，并在笔记中保存完整操作过程。失败也要记录，因为排错过程也是学习成果。</Paragraph></div></>},
    {title:'7. 思考和独立小题',body:<><div className="practice-level"><Tag color="blue">思考题</Tag><Paragraph>如果删除第一个准备步骤，后续可能在哪里失败？如果改变一个输入或参数，结果可能怎样变化？先写预测，再运行验证。</Paragraph></div><div className="practice-level"><Tag color="orange">独立小题</Tag><Paragraph>关闭当前示例，不看答案重新完成核心流程；然后主动修改一个变量、筛选条件、请求参数或命令选项，形成第二个不同结果。</Paragraph></div></>},
    {title:'8. 验收和复盘',body:<><div className="acceptance-box"><b>完成标准</b><Paragraph>{guide.acceptance}</Paragraph></div><Paragraph><b>必须留下：</b>可运行文件或操作结果、关键截图、错误与解决办法、一篇用自己的话写的复盘。完成后勾选任务并填写学习分钟、收获和问题。</Paragraph></>},
  ];
  const page=pages[step];
  return <Card className="guide-card" title={`🧭 第 ${task.day_number} 天执行引导 · ${guide.topic}`} extra={<Text type="secondary">按步骤完成</Text>}><div className="guide-steps">{pages.map((item,index)=><button key={item.title} className={index===step?'active':''} onClick={()=>setStep(index)}><span>{index+1}</span>{item.title}</button>)}</div><div className="guide-content"><Title level={4}>{step+1}. {page.title}</Title>{page.body}<Space><Button disabled={!step} onClick={()=>setStep(step-1)}>上一步</Button><Button type="primary" disabled={step===pages.length-1} onClick={()=>setStep(step+1)}>下一步</Button></Space></div></Card>;
}

export function LearningPanel({client}) {
  const [overview,setOverview]=useState(null),[tasks,setTasks]=useState([]),[plans,setPlans]=useState([]),[stats,setStats]=useState(null);
  const [month,setMonth]=useState(dayjs()),[checkin,setCheckin]=useState({actual_minutes:0,gains:'',blockers:'',tomorrow_focus:''});
  const [folders,setFolders]=useState([]),[notes,setNotes]=useState([]),[note,setNote]=useState(null),[query,setQuery]=useState(''),[trash,setTrash]=useState(false);
  const [saveState,setSaveState]=useState('已保存'), timer=useRef(), currentNote=useRef(null), editVersion=useRef(0);
  const [taskModal,setTaskModal]=useState(null),[reviewTask,setReviewTask]=useState(null),[form]=Form.useForm();
  async function load(){await client.post(`${API}/schedule/reconcile`,{}); const [o,t,f,p]=await Promise.all([client.get(`${API}/overview`),client.get(`${API}/tasks`),client.get(`${API}/note-folders`),client.get(`${API}/plans`)]); setOverview(o);setTasks(t);setFolders(f);setPlans(p); if(o.latest_checkin?.checkin_date===String(o.today)) setCheckin(o.latest_checkin);}
  async function loadStats(value=month){setStats(await client.get(`${API}/stats?month=${value.format('YYYY-MM')}`))}
  async function loadNotes(){setNotes(await client.get(`${API}/notes?q=${encodeURIComponent(query)}&trash=${trash}`))}
  useEffect(()=>{load().catch(e=>message.error(e.message))},[]); useEffect(()=>{loadStats().catch(()=>{})},[month]); useEffect(()=>{loadNotes().catch(()=>{})},[query,trash]);
  async function toggle(task,checked){await client.put(`${API}/tasks/${task.id}`,{...task,status:checked?'completed':'pending'});await Promise.all([load(),loadStats()])}
  async function saveCheckin(){await client.put(`${API}/checkins/${overview.today}`,checkin);message.success('今日打卡已保存');await Promise.all([load(),loadStats()])}
  function updateNote(noteId,patch){if(currentNote.current?.id!==noteId)return;const next={...currentNote.current,...patch};currentNote.current=next;setNote(next);setSaveState('保存中…');const version=++editVersion.current;clearTimeout(timer.current);timer.current=setTimeout(()=>saveNote(next,version),1000)}
  async function saveNote(value=currentNote.current,version=editVersion.current){if(!value)return;try{const saved=await client.put(`${API}/notes/${value.id}`,value);setNotes(rows=>rows.map(row=>row.id===saved.id?saved:row));if(currentNote.current?.id===saved.id&&version===editVersion.current){currentNote.current=saved;setNote(saved);setSaveState('已保存')}}catch(e){if(currentNote.current?.id===value.id)setSaveState('保存失败');message.error(e.message)}}
  async function selectNote(next){clearTimeout(timer.current);const previous=currentNote.current;if(previous&&saveState==='保存中…')await saveNote(previous,editVersion.current);editVersion.current+=1;currentNote.current=next;setNote(next);setSaveState('已保存')}
  async function newNote(){const created=await client.post(`${API}/notes`,{title:'未命名笔记',content_markdown:'',tags:[],is_pinned:false});setNotes(rows=>[created,...rows]);await selectNote(created)}
  async function uploadImage(noteId,blob){const fd=new FormData();fd.append('file',blob);const result=await client.post(`${API}/notes/${noteId}/attachments`,fd);return result.url}
  async function submitTask(){const values=await form.validateFields(); const body={...values,planned_date:values.planned_date.format('YYYY-MM-DD'),original_planned_date:taskModal?.original_planned_date||values.planned_date.format('YYYY-MM-DD')}; taskModal?.id?await client.put(`${API}/tasks/${taskModal.id}`,body):await client.post(`${API}/tasks`,body);setTaskModal(null);await load()}
  function confirmRestart(){Modal.confirm({title:'从第 1 天重新开始学习？',width:560,okText:'确认重新开始',cancelText:'暂不重置',content:<div><Paragraph>系统会创建一份从今天开始的 40 天零基础文档课程。</Paragraph><Alert type="success" showIcon title="旧计划只会归档；以前的任务、打卡和学习笔记都不会删除。"/><Paragraph style={{marginTop:12}}>新课程先认识酒店业务和接口，再学习 Postman、Python、Requests、pytest 和请求封装。</Paragraph></div>,onOk:async()=>{const result=await client.post(`${API}/restart`,{start_date:dayjs().format('YYYY-MM-DD'),title:`第 ${plans.length+1} 期 · 零基础文档训练营`,confirm:true});message.success(result.message);setCheckin({actual_minutes:0,gains:'',blockers:'',tomorrow_focus:''});await Promise.all([load(),loadStats()]);}})}
  const phases=useMemo(()=>Object.entries(tasks.reduce((a,t)=>{(a[`${t.planned_date} · 第 ${t.day_number} 天 · ${t.phase}`]??=[]).push(t);return a},{})),[tasks]);
  if(!overview)return <Card loading/>;
  const tabs=[
    {key:'restart',label:'🔄 重新开始',children:<><Card className="section-card" title="从第 1 天重新开始"><Paragraph>创建一份从今天开始的 40 天零基础文档课程。旧计划会进入历史记录，原来的任务、打卡和学习笔记都不会删除。</Paragraph><Space wrap><Tag color="purple">当前：{overview.plan.title}</Tag><Tag>已保存计划 {plans.length} 期</Tag><Button danger type="primary" onClick={confirmRestart}>重新开始学习</Button></Space></Card><Card className="section-card" title="历史学习计划"><List dataSource={plans} renderItem={plan=><List.Item><List.Item.Meta title={<Space><b>{plan.title}</b><Tag color={plan.status==='active'?'green':'default'}>{plan.status==='active'?'学习中':'已归档'}</Tag></Space>} description={`${plan.original_start_date} — ${plan.projected_end_date}`}/></List.Item>}/></Card></>},
    {key:'today',label:'🌱 今日学习',children:<div className="learning-today"><Row gutter={[16,16]}><Col xs={24} lg={16}><Card className="hero-card"><Text>现在最重要的一步</Text><Title level={2}>{overview.next_task?.title||'40 天计划已完成 🎉'}</Title><Paragraph>{overview.next_task?.details}</Paragraph><Progress percent={overview.progress}/></Card>{overview.next_task&&<DailyExecutionGuide key={overview.next_task.id} task={overview.next_task}/>}<Card title={`今日任务 · ${overview.today}`} className="section-card"><List dataSource={overview.today_tasks} locale={{emptyText:'今天没有任务'}} renderItem={t=><List.Item><Checkbox checked={t.status==='completed'} onChange={e=>toggle(t,e.target.checked)}><b>{t.title}</b><div><Text type="secondary">{t.details} · {t.expected_minutes} 分钟</Text></div><div><Tag>{t.category}</Tag>验收：{t.acceptance_criteria}</div></Checkbox></List.Item>}/></Card></Col><Col xs={24} lg={8}><Card title="📝 每日复盘"><Form layout="vertical"><Form.Item label="实际学习分钟"><InputNumber min={0} max={1440} value={checkin.actual_minutes} onChange={v=>setCheckin({...checkin,actual_minutes:v||0})}/></Form.Item>{[['gains','今日收获'],['blockers','遇到的问题'],['tomorrow_focus','明日重点']].map(([k,l])=><Form.Item label={l} key={k}><Input.TextArea rows={3} value={checkin[k]} onChange={e=>setCheckin({...checkin,[k]:e.target.value})}/></Form.Item>)}<Button type="primary" block onClick={saveCheckin}>完成今日打卡</Button></Form></Card></Col></Row></div>},
    {key:'plan',label:'🗺️ 学习计划',children:<><Space className="plan-toolbar"><Tag color="blue">原计划 {overview.plan.original_start_date} — {overview.plan.original_end_date}</Tag><Tag color={overview.deadline_risk?'red':'green'}>预计结束 {overview.plan.projected_end_date}</Tag><Button icon={<PlusOutlined/>} onClick={()=>{setTaskModal({});form.resetFields()}}>新增任务</Button></Space><div className="plan-list">{phases.map(([label,rows])=><Card size="small" title={label} key={label}>{rows.map(t=><div className="plan-task" key={t.id}><Checkbox checked={t.status==='completed'} onClick={e=>e.stopPropagation()} onChange={e=>toggle(t,e.target.checked)}/><span>{t.category==='复盘'?'✍️':'🧪'} {t.title}</span><Text type="secondary">{t.expected_minutes}m</Text><Button size="small" type="primary" ghost onClick={()=>setReviewTask(t)}>学习 / 复习</Button><Button size="small" onClick={()=>{setTaskModal(t);form.setFieldsValue({...t,planned_date:dayjs(t.planned_date)})}}>编辑</Button></div>)}</Card>)}</div><Modal open={!!reviewTask} title={reviewTask?`第 ${reviewTask.day_number} 天 · ${reviewTask.title}`:''} footer={null} width={1100} onCancel={()=>setReviewTask(null)} destroyOnHidden><DailyExecutionGuide key={reviewTask?.id} task={reviewTask||{day_number:1}}/></Modal></>},
    {key:'calendar',label:'📅 打卡日历',children:<><Space className="stats-row"><DatePicker picker="month" value={month} onChange={setMonth}/><Statistic title="打卡天数" value={stats?.checkin_days||0} suffix="天"/><Statistic title="连续打卡" value={stats?.current_streak||0} suffix="天"/><Statistic title="总时长" value={Math.round((stats?.total_minutes||0)/60*10)/10} suffix="小时"/><Statistic title="任务完成率" value={stats?.task_completion_rate||0} suffix="%"/></Space><CalendarGrid month={month} stats={stats}/></>},
    {key:'notes',label:'📒 学习笔记',children:<div className="notes-layout"><aside><Space><Button icon={<FolderAddOutlined/>} onClick={async()=>{const name=prompt('文件夹名称');if(name){await client.post(`${API}/note-folders`,{name});setFolders(await client.get(`${API}/note-folders`))}}}>文件夹</Button><Button type="primary" icon={<PlusOutlined/>} onClick={newNote}>笔记</Button></Space><Input.Search placeholder="搜索标题和正文" allowClear onSearch={setQuery}/><Button type="text" onClick={()=>setTrash(!trash)}>{trash?'返回笔记':'🗑️ 回收站'}</Button>{folders.map(f=><div className="folder" key={f.id}>📁 {f.name}</div>)}</aside><section className="note-list"><List dataSource={notes} locale={{emptyText:<Empty description="还没有笔记"/>}} renderItem={n=><List.Item className={note?.id===n.id?'selected':''} onClick={()=>selectNote(n)}><List.Item.Meta title={<>{n.is_pinned&&<PushpinFilled/>} {n.title}</>} description={(n.content_markdown||'空白笔记').slice(0,70)}/></List.Item>}/></section><main className="note-editor">{note?<><Space className="editor-head"><Input variant="borderless" value={note.title} onChange={e=>updateNote(note.id,{title:e.target.value})}/><Text type={saveState==='保存失败'?'danger':'secondary'}>{saveState}</Text><Button icon={<SaveOutlined/>} onClick={()=>saveNote()}>保存</Button><Upload showUploadList={false} customRequest={async({file,onSuccess,onError})=>{try{await uploadImage(note.id,file);onSuccess()}catch(e){onError(e)}}}><Button icon={<UploadOutlined/>}>附件</Button></Upload><Button danger icon={<DeleteOutlined/>} onClick={async()=>{clearTimeout(timer.current);await client.delete(`${API}/notes/${note.id}`);currentNote.current=null;setNote(null);loadNotes()}}/></Space><MarkdownEditor key={note.id} value={note.content_markdown} onChange={v=>updateNote(note.id,{content_markdown:v})} onImage={blob=>uploadImage(note.id,blob)}/></>:<Empty description="选择或新建一篇笔记"/>}</main><Upload accept=".zip" showUploadList={false} customRequest={async({file,onSuccess,onError})=>{const fd=new FormData();fd.append('file',file);try{const r=await client.post(`${API}/imports/youdao`,fd);message.success(`导入 ${r.success.length}，重复 ${r.duplicates.length}`);loadNotes();onSuccess()}catch(e){message.error(e.message);onError(e)}}}><Button className="import-btn">导入有道 ZIP</Button></Upload></div>}
  ];
  return <div className="learning-space"><div className="learning-heading"><div><Text>个人成长</Text><Title level={2}>📚 学习空间</Title></div><Tag color="purple">{overview.current_phase}</Tag></div><Tabs items={tabs}/><Modal open={!!taskModal} title={taskModal?.id?'编辑任务':'新增任务'} onCancel={()=>setTaskModal(null)} onOk={submitTask}><Form form={form} layout="vertical"><Form.Item name="title" label="任务名称" rules={[{required:true}]}><Input/></Form.Item><Row gutter={12}><Col span={12}><Form.Item name="phase" label="阶段" rules={[{required:true}]}><Input/></Form.Item></Col><Col span={12}><Form.Item name="category" label="分类" initialValue="实操"><Input/></Form.Item></Col></Row><Form.Item name="details" label="操作说明"><Input.TextArea/></Form.Item><Form.Item name="acceptance_criteria" label="验收标准"><Input.TextArea/></Form.Item><Row gutter={12}><Col span={8}><Form.Item name="day_number" label="第几天" rules={[{required:true}]}><InputNumber/></Form.Item></Col><Col span={8}><Form.Item name="expected_minutes" label="分钟" initialValue={60}><InputNumber/></Form.Item></Col><Col span={8}><Form.Item name="planned_date" label="日期" rules={[{required:true}]}><DatePicker/></Form.Item></Col></Row><Form.Item name="status" hidden initialValue="pending"><Input/></Form.Item></Form></Modal></div>;
}

function CalendarGrid({month,stats}){const start=month.startOf('month'),days=month.daysInMonth(),blanks=(start.day()+6)%7;return <div className="calendar"><div className="weekdays">{['一','二','三','四','五','六','日'].map(x=><b key={x}>{x}</b>)}</div><div className="calendar-grid">{Array(blanks).fill(0).map((_,i)=><i key={`b${i}`}/>)}{Array.from({length:days},(_,i)=>{const key=month.date(i+1).format('YYYY-MM-DD'),d=stats?.days?.[key];return <div key={key} className={d?.checked_in?'checked':''} title={d?.checked_in?'已打卡':''}><b>{i+1}</b><span>{d?.checked_in?`✓ ${d.minutes}m`:'—'}</span><small>{d?.total?`${d.completed}/${d.total}`:''}</small></div>})}</div></div>}
