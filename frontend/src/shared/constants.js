// File purpose: Shared constants and examples used across pages.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

// 前端通用常量。
// 业务模块需要示例文案或默认值时，从这里 import，避免散落在页面代码里。

export const API_BASE = '/api';
export const DEFAULT_UI_STEPS = '[{"action":"goto","value":"https://example.com"},{"action":"assert_text","value":"Example Domain"},{"action":"screenshot"}]';
export const AUTH_EXPIRED_EVENT = 'automation-auth-expired';

export const API_JSON_EXAMPLE = `请求头 JSON 示例：
{
  "Content-Type": "application/json",
  "Authorization": "Bearer 你的token"
}

POST 请求体示例：
{
  "username": "admin",
  "password": "123456"
}

JSON 路径断言示例：
响应：{"data":{"name":"张三"}}
JSON 路径：$.data.name
JSON 期望值：张三`;

export const UI_STEPS_EXAMPLE = `[
  { "action": "goto", "value": "https://example.com" },
  { "action": "click", "selector": "text=登录" },
  { "action": "fill", "selector": "#username", "value": "admin" },
  { "action": "wait", "value": "1000" },
  { "action": "assert_text", "value": "欢迎" },
  { "action": "screenshot" }
]`;
