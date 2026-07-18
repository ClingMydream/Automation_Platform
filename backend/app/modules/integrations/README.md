# integrations

维护通用 Webhook、钉钉、企微和飞书地址，支持连通性测试与可选环境变量密钥。

- `router.py`：配置 CRUD 和测试发送接口。
- `service.py`：安全请求头、平台格式适配和短超时发送。
- `schemas.py`：请求与响应模型。
