import React from 'react';
import { Card, Typography } from 'antd';

const { Paragraph, Text } = Typography;

// JSON 输入说明卡片。接口测试和 UI 测试共用。
export function JsonHelpCard({ title, tips, example }) {
  return (
    <Card size="small" title={title} className="help-card">
      {tips.map((tip) => <Paragraph key={tip}>{tip}</Paragraph>)}
      <pre>{example}</pre>
      <Text type="secondary">提示：JSON 必须使用英文双引号，不能写注释，最后一项后面不能有逗号。</Text>
    </Card>
  );
}
