# integrations 集成开放

维护 Webhook、钉钉、企微、飞书等外部集成配置。

- `router.py`：Webhook CRUD 和配置测试。
- `schemas.py`：Webhook 请求/响应模型。
- `service.py`：Webhook 发送、事件过滤、批次通知载荷、钉钉/企微/飞书文本消息格式。

当前支持事件：

- `webhook_test`：点击“测试”按钮时发送。
- `batch_finished`：执行批次完成时发送。
- `task_failed`：执行批次失败时发送。
- `quality_risk`：执行批次存在失败结果时发送。
