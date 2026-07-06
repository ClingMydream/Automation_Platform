// File purpose: Shared page guide component that renders usage tips for the active menu.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

import React from 'react';
import { Card, Space, Tag, Typography } from 'antd';
import { RocketOutlined } from '@ant-design/icons';

const { Title, Paragraph } = Typography;

// Render the operation guide for the active menu tab.
// Shared helper block: exported helpers below are reused by multiple modules.
export function PageGuide({ tab }) {
  const guides = {
    projects: {
      title: '项目管理',
      description: '项目是用例的归属空间。可以先使用示例项目，也可以创建自己的业务项目。',
      steps: ['新建项目', '在接口或 UI 页面选择项目', '必要时修改或删除项目'],
    },
    test_objects: {
      title: '测试对象',
      description: '测试对象用来沉淀平台到底要测什么，例如接口、页面、脚本、性能场景、设备或环境。',
      steps: ['创建唯一编号', '选择对象类型和所属项目', '用标签标记核心链路'],
    },
    capabilities: {
      title: '测试能力',
      description: '测试能力用来维护怎么测，包括接口场景编排、Mock、性能场景和 Runner 执行机。',
      steps: ['选择能力标签页', '保存配置', 'Runner 可发送心跳'],
    },
    test_tasks: {
      title: '测试任务',
      description: '测试任务用来描述什么时候测、由谁测、怎么跑；每次执行都会生成独立批次。',
      steps: ['创建任务', '关联测试对象', '点击执行生成批次'],
    },
    results: {
      title: '结果中心',
      description: '结果中心统一沉淀执行证据，包括批次、状态、耗时、日志、错误、断言和性能指标。',
      steps: ['查看执行批次', '点击结果行查看证据', '外部脚本可通过 API 回传'],
    },
    diagnosis: {
      title: '问题定位',
      description: '问题定位把失败结果整理成可跟踪记录，补充根因、复现步骤、责任人、处理建议和证据 JSON。',
      steps: ['从失败结果生成定位', '补充根因和责任人', '处理完成后改为已修复'],
    },
    quality: {
      title: '质量分析',
      description: '基于结果中心计算通过率、失败分布、耗时指标和执行批次趋势，辅助判断发布风险。',
      steps: ['查看通过率', '关注失败分类', '观察最近批次趋势'],
    },
    datasets: {
      title: '测试数据',
      description: '维护变量集、测试账号和参数化数据池，供接口测试、UI 自动化、脚本和 JMeter 复用。',
      steps: ['创建变量 JSON', '维护数据行数组', '在任务配置中引用'],
    },
    api: {
      title: '接口测试',
      description: '填写请求地址、方法、请求头和断言条件，保存后即可执行。',
      steps: ['URL 填 https://example.com', '状态码填 200', '响应文本填 Example Domain'],
    },
    ui: {
      title: 'UI 自动化',
      description: '用低代码 JSON 描述页面步骤。执行时会打开独立的实时执行窗口。',
      steps: ['使用默认步骤 JSON', '保存 UI 用例', '点击执行查看实时窗口'],
    },
    runs: {
      title: '执行记录',
      description: '查看任务状态、耗时、执行时间、接口断言、UI 步骤和截图。',
      steps: ['点击详情查看报告', '运行中自动刷新', '失败时查看错误信息'],
    },
    reports: {
      title: '测试报告',
      description: '汇总接口和 UI 自动化的执行结果，查看通过率、失败原因、断言明细、UI 步骤和截图。',
      steps: ['筛选报告', '查看详情', '导出 HTML 报告'],
    },
    integrations: {
      title: '集成配置',
      description: '维护 CI、脚本仓库、钉钉、企微、飞书或通用 Webhook 的开放集成配置。',
      steps: ['新增 Webhook', '订阅事件', '后续接入通知 worker'],
    },
    files: {
      title: '文件快传',
      description: '上传临时文件并生成二维码，手机扫码免登录下载，也可以从手机回传文件到电脑端列表。',
      steps: ['上传临时文件', '手机扫码下载', '手机页面可回传文件'],
    },
    images: {
      title: '图片工具',
      description: '自定义生成图片，也可以上传图片后裁剪尺寸、缩放大小、叠加文案并转换格式。',
      steps: ['填写尺寸和文案生成图片', '上传原图裁剪或缩放', '选择格式并下载结果'],
    },
    json_tools: {
      title: 'JSON 工具',
      description: '格式化、压缩、校验 JSON，并对比两段 JSON 的字段和值差异。',
      steps: ['粘贴 JSON', '格式化或压缩', '左右对比查看差异'],
    },
    codec: {
      title: '转码工具',
      description: '提供 URL、Base64、Unicode、HTML 实体、Hex、JSON 字符串等常用编码转换。',
      steps: ['选择转码类型', '输入原文', '转换后复制结果'],
    },
    users: {
      title: '用户管理',
      description: '管理员可以添加登录人员，并为每个人配置可操作菜单。普通用户不会看到本模块。',
      steps: ['新增登录账号', '勾选可操作菜单', '保存后让用户重新登录'],
    },
  };
  const guide = guides[tab] || guides.projects;
  // Render block: JSX below describes what the user sees on this page.
  return (
    <Card className="guide-card" size="small">
      <Space align="start" size={14}>
        <div className="guide-icon"><RocketOutlined /></div>
        <div>
          <Title level={5}>{guide.title}</Title>
          <Paragraph>{guide.description}</Paragraph>
          <Space wrap>{guide.steps.map((step, index) => <Tag key={step} color="cyan">{index + 1}. {step}</Tag>)}</Space>
        </div>
      </Space>
    </Card>
  );
}
