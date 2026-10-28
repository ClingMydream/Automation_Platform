# Cling 订单与库存测试工程

这是一个供 Python、接口、UI 和性能练习使用的业务系统。前端在平台的“实践实验室”，独立业务页面为 `/practice-app`；API 文档为 `/api/practice/docs`。

## 数据与角色

每个平台账号有独立 SQLite 数据库，包含 users、products、orders、audit、meta 表。与平台 MySQL、Emote 业务数据隔离。

练习管理员 `lab_admin`、普通用户 `learner` 的固定练习密码均为 `Practice123!`。它们不具备平台管理员权限。平台登录后进入实践实验室获取练习会话，Token 一小时有效；重置后旧会话失效。

固定商品：NOTE-001 手账本 2900 分、20 件；LAMP-002 阅读灯 12900 分、5 件；BAG-003 通勤包 8900 分、0 件。金额采用整数分。管理员可新增商品和按版本调整库存。

## 业务规则

1. 普通用户只能查看自己的订单；管理员能查看全部练习订单和审计日志。
2. 下单必须带唯一 `request_key`。相同编号与相同请求体返回同一订单；编号被不同请求体复用时返回 409。
3. 库存在数据库事务内条件扣减，不允许负库存。
4. 重复取消只恢复一次库存；取消后保留订单与操作记录。
5. 库存编辑需要读取时的 `version`，过期版本返回409。
6. 重置只作用于本人练习数据，测试运行中不允许重置；平台笔记、待办和测试报告保留。

## 本地运行测试

安装 `requirements.txt`，通过环境变量提供以下信息（不要写进源文件或提交到仓库）：

```text
PRACTICE_API_URL=https://你的平台域名/api/practice/v1
PRACTICE_ADMIN_TOKEN=练习管理员Token
PRACTICE_CUSTOMER_TOKEN=练习普通用户Token
PRACTICE_UI_URL=https://你的平台域名/practice-app
CHROMIUM_PATH=Chromium可执行文件路径
```

```bash
python -m pytest tests/test_reference_python.py tests/test_api.py -q
python -m pytest tests/test_ui.py -q
python -m locust -f locustfile.py --headless -u 1 -r 1 --run-time 10s --host "$PRACTICE_API_URL"
```

Windows 可用 PowerShell 的 `$env:变量名` 配置环境变量，执行时将 host 参数改为 `$env:PRACTICE_API_URL`。浏览器测试需要 Chromium；平台提供的执行容器已安装浏览器。

接口与 UI 用例会在个人练习空间新增 AUTO / UI 商品，并保留订单与审计记录。只针对练习子项目运行，不要将目标改为实际业务生产系统。性能脚本只查询商品，平台限制最多5用户、30秒；结果用于学习指标，不用于推断生产容量。

## 建议练习顺序

先运行基础 Python 示例，再查询商品、手动下单与取消，随后阅读接口断言、幂等和并发用例。最后运行 UI 链路及小规模只读性能场景，比较请求数、错误率、RPS 与 P95，并将结果关联到学习记录。
