# mock_service

公开 Mock 响应服务。

- 配置入口：`backend/app/modules/test_capabilities/router.py` 的 `/v1/mock-rules`
- 响应入口：`/api/mock/{path}`
- 鉴权：公开访问，不需要登录，方便被接口调试或前端页面直接调用
- 匹配规则：请求方法 + 路径，路径会自动补 `/`
