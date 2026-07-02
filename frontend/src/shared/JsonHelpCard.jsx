// File purpose: Shared JSON help card component used by API and UI test pages.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

import React from 'react';
import { Card, Typography } from 'antd';

const { Paragraph, Text } = Typography;

// JSON 输入说明卡片。接口测试和 UI 测试共用。
// Shared helper block: exported helpers below are reused by multiple modules.
export function JsonHelpCard({ title, tips, example }) {
  // Render block: JSX below describes what the user sees on this page.
  return (
    <Card className="json-help-card" title={title} size="small">
      <ul>
        {tips.map((tip) => <li key={tip}>{tip}</li>)}
      </ul>
      <pre className="json-help-code">{example}</pre>
      <Text type="secondary">提示：JSON 必须使用英文双引号，不能写注释，最后一项后面不能有逗号。</Text>
    </Card>
  );
}
