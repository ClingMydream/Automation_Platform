// File purpose: Image tools page. Generate, crop, resize, annotate, and convert images.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

import React, { useEffect, useState } from 'react';
import { Alert, App as AntApp, Button, Card, Col, Form, Input, Row, Select, Space, Upload } from 'antd';
import { InboxOutlined, PictureOutlined } from '@ant-design/icons';
import { apiClient } from '../../shared/apiClient';
import { API_BASE } from '../../shared/constants';
import { downloadBlob } from '../../shared/fileTransfer.jsx';

const { TextArea } = Input;
const { Dragger } = Upload;

// Image tool page: generates, crops, resizes, annotates, and converts images.
export function ImageToolPanel({ token }) {
  // State block: values here control loading, selection, form state, and visible page data.
  const [formats, setFormats] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [sourceFile, setSourceFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const { message } = AntApp.useApp();
  const formatOptions = formats.length > 0 ? formats.map((item) => ({ value: item.value, label: item.label })) : [
    { value: 'png', label: 'PNG' },
    { value: 'jpeg', label: 'JPEG' },
    { value: 'webp', label: 'WEBP' },
    { value: 'gif', label: 'GIF' },
    { value: 'bmp', label: 'BMP' },
    { value: 'tiff', label: 'TIFF' },
    { value: 'svg', label: 'SVG' },
  ];

  // Effect block: code here reacts to token, route, or polling changes.
  useEffect(() => {
    apiClient(token).get('/image-tools/formats').then(setFormats).catch(() => {});
  }, [token]);

  // Read the download filename from response headers.
  function filenameFromResponse(res, fallback) {
    const disposition = res.headers.get('content-disposition') || '';
    const match = disposition.match(/filename="?([^"]+)"?/i);
    return match?.[1] || fallback;
  }

  // Call an image endpoint and return the resulting blob metadata.
  async function fetchImage(path, options, fallbackName) {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      },
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      if (res.status === 401) {
        notifyAuthExpired();
        throw authExpiredError();
      }
      throw new Error(data.detail || '图片处理失败');
    }
    const blob = await res.blob();
    return { blob, filename: filenameFromResponse(res, fallbackName), type: res.headers.get('content-type') || blob.type };
  }

  // Preview the generated image and trigger download.
  function showResult(result) {
    if (preview?.url) URL.revokeObjectURL(preview.url);
    const nextUrl = URL.createObjectURL(result.blob);
    setPreview({ url: nextUrl, type: result.type, name: result.filename });
    downloadBlob(result.blob, result.filename);
  }

  // Generate a new image from the form settings.
  async function generate(values) {
    setGenerating(true);
    try {
      const result = await fetchImage('/image-tools/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          width: Number(values.width),
          height: Number(values.height),
          background_color: values.background_color,
          text: values.text || '',
          text_color: values.text_color,
          font_size: Number(values.font_size),
          format: values.format,
          quality: Number(values.quality),
          max_kb: values.max_kb ? Number(values.max_kb) : null,
        }),
      }, 'generated-image.png');
      showResult(result);
      message.success('图片已生成并下载');
    } catch (err) {
      message.error(err.message);
    } finally {
      setGenerating(false);
    }
  }

  // Process an uploaded image with crop, resize, text, and format settings.
  async function process(values) {
    if (!sourceFile) {
      message.warning('请先上传需要裁剪或转换的图片');
      return;
    }
    setProcessing(true);
    try {
      const body = new FormData();
      body.append('file', sourceFile);
      ['crop_x', 'crop_y', 'crop_width', 'crop_height', 'output_width', 'output_height', 'text', 'text_color', 'font_size', 'format', 'quality', 'max_kb'].forEach((key) => {
        const value = values[key];
        if (value !== undefined && value !== null && value !== '') body.append(key, value);
      });
      const result = await fetchImage('/image-tools/process', { method: 'POST', body }, 'processed-image.png');
      showResult(result);
      message.success('图片已处理并下载');
    } catch (err) {
      message.error(err.message);
    } finally {
      setProcessing(false);
    }
  }

  // Render block: JSX below describes what the user sees on this page.
  return (
    <Space direction="vertical" size={16} className="full-width">
      <Alert type="info" showIcon message="支持 PNG、JPEG、WEBP、GIF、BMP、TIFF、SVG。JPEG/WEBP 可按目标 KB 尽量压缩，SVG 适合生成文案矢量图。" />
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={12}>
          <Card title="生成图片">
            <Form layout="vertical" onFinish={generate} initialValues={{ width: 1080, height: 1080, background_color: '#ffffff', text_color: '#17202a', font_size: 72, format: 'png', quality: 92 }}>
              <Row gutter={12}>
                <Col span={12}><Form.Item label="宽度 px" name="width" rules={[{ required: true }]}><Input type="number" min={32} max={8192} /></Form.Item></Col>
                <Col span={12}><Form.Item label="高度 px" name="height" rules={[{ required: true }]}><Input type="number" min={32} max={8192} /></Form.Item></Col>
              </Row>
              <Form.Item label="图片文案" name="text"><TextArea rows={4} placeholder="例如：新品上线&#10;限时优惠" /></Form.Item>
              <Row gutter={12}>
                <Col span={12}><Form.Item label="背景颜色" name="background_color"><Input type="color" /></Form.Item></Col>
                <Col span={12}><Form.Item label="文字颜色" name="text_color"><Input type="color" /></Form.Item></Col>
              </Row>
              <Row gutter={12}>
                <Col span={8}><Form.Item label="字号" name="font_size"><Input type="number" min={8} max={512} /></Form.Item></Col>
                <Col span={8}><Form.Item label="格式" name="format"><Select options={formatOptions} /></Form.Item></Col>
                <Col span={8}><Form.Item label="质量" name="quality"><Input type="number" min={1} max={100} /></Form.Item></Col>
              </Row>
              <Form.Item label="目标大小 KB" name="max_kb"><Input type="number" placeholder="可不填" /></Form.Item>
              <Button type="primary" htmlType="submit" loading={generating} icon={<PictureOutlined />}>生成并下载</Button>
            </Form>
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card title="裁剪 / 缩放 / 转格式">
            <Form layout="vertical" onFinish={process} initialValues={{ crop_x: 0, crop_y: 0, format: 'png', quality: 92, text_color: '#17202a', font_size: 48 }}>
              <Form.Item label="上传原图">
                <Dragger
                  multiple={false}
                  beforeUpload={(file) => { setSourceFile(file); return false; }}
                  onRemove={() => setSourceFile(null)}
                  maxCount={1}
                  accept="image/*"
                >
                  <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                  <p className="ant-upload-text">点击或拖拽图片到这里</p>
                  <p className="ant-upload-hint">支持常见图片，填写裁剪区域后可输出为指定格式。</p>
                </Dragger>
              </Form.Item>
              <Row gutter={12}>
                <Col span={12}><Form.Item label="裁剪 X" name="crop_x"><Input type="number" min={0} /></Form.Item></Col>
                <Col span={12}><Form.Item label="裁剪 Y" name="crop_y"><Input type="number" min={0} /></Form.Item></Col>
                <Col span={12}><Form.Item label="裁剪宽度" name="crop_width"><Input type="number" placeholder="不填为剩余宽度" /></Form.Item></Col>
                <Col span={12}><Form.Item label="裁剪高度" name="crop_height"><Input type="number" placeholder="不填为剩余高度" /></Form.Item></Col>
              </Row>
              <Row gutter={12}>
                <Col span={12}><Form.Item label="输出宽度" name="output_width"><Input type="number" placeholder="可不填" /></Form.Item></Col>
                <Col span={12}><Form.Item label="输出高度" name="output_height"><Input type="number" placeholder="可不填" /></Form.Item></Col>
              </Row>
              <Form.Item label="追加文案" name="text"><TextArea rows={3} placeholder="可不填，填写后居中叠加到图片上" /></Form.Item>
              <Row gutter={12}>
                <Col span={8}><Form.Item label="文字颜色" name="text_color"><Input type="color" /></Form.Item></Col>
                <Col span={8}><Form.Item label="字号" name="font_size"><Input type="number" min={8} max={512} /></Form.Item></Col>
                <Col span={8}><Form.Item label="格式" name="format"><Select options={formatOptions} /></Form.Item></Col>
              </Row>
              <Row gutter={12}>
                <Col span={12}><Form.Item label="质量" name="quality"><Input type="number" min={1} max={100} /></Form.Item></Col>
                <Col span={12}><Form.Item label="目标大小 KB" name="max_kb"><Input type="number" placeholder="可不填" /></Form.Item></Col>
              </Row>
              <Button type="primary" htmlType="submit" loading={processing} icon={<PictureOutlined />}>处理并下载</Button>
            </Form>
          </Card>
        </Col>
      </Row>
      {preview && (
        <Card title={`处理结果：${preview.name}`}>
          {preview.type.includes('svg') ? (
            <iframe className="image-tool-preview-frame" src={preview.url} title="image-preview" />
          ) : (
            <img className="image-tool-preview" src={preview.url} alt={preview.name} />
          )}
        </Card>
      )}
    </Space>
  );
}

// Image tools module: calls backend image APIs for generation, cropping, and format conversion.
