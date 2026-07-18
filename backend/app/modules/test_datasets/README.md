# test_datasets 测试数据

维护变量集、测试账号和参数化数据池。

- `router.py`：测试数据 CRUD。
- `schemas.py`：测试数据请求/响应模型。
- `service.py`：生成校验位正确的合成身份证、格式手机号、Twilio API 模拟号码，或读取受控短信接收号码。

真实短信接收号码不会随机生成。请在服务端设置 `TEST_SMS_PHONE_NUMBERS`（逗号分隔的 E.164 自有/已租用号码），再选择“自有/已租用接收号码”模式。
