# backend/app/modules

这里是后端业务模块目录。

当前每个业务模块都有自己的 `router.py`，`backend/app/api/routes.py` 只负责 include 这些模块 router。业务逻辑继续向模块内的 `service.py` 拆，模块专属请求模型继续向 `schemas.py` 拆。

- `auth/`：登录、退出、当前用户。
- `users/`：用户管理和菜单权限。
- `projects/`：项目与环境。
- `test_objects/`：测试对象层，沉淀平台要测什么。
- `test_tasks/`：测试任务和执行批次。
- `result_center/`：结果中心、结果回传和附件。
- `quality_analysis/`：质量指标、质量趋势和任务质量报告。
- `test_datasets/`：测试变量、账号和参数化数据池。
- `api_testing/`：接口测试用例。
- `ui_testing/`：UI 测试用例。
- `file_transfer/`：文件快传。
- `image_tools/`：图片生成、裁剪、格式转换。
- `runs/`：执行任务。
- `reports/`：测试报告。
- `integrations/`：Webhook 和外部系统集成配置。

继续改造规则：

- `router.py`：只放 FastAPI 路由、权限依赖和请求响应。
- `service.py`：放业务逻辑。
- `schemas.py`：放只属于本模块的请求/响应模型。
- `README.md`：写本模块改造说明。

已经独立出来的公共配置和模块服务：

- 菜单权限：`backend/app/core/menu.py`
- 登录鉴权：`backend/app/core/auth.py`
- 地址安全校验：`backend/app/core/target_guard.py`
- 用户管理业务：`backend/app/modules/users/service.py`
- 测试报告业务：`backend/app/modules/reports/service.py`
- 测试对象业务：`backend/app/modules/test_objects/service.py`
- 测试对象请求模型：`backend/app/modules/test_objects/schemas.py`
- 测试任务业务：`backend/app/modules/test_tasks/service.py`
- 结果中心业务：`backend/app/modules/result_center/service.py`
- 文件快传业务：`backend/app/modules/file_transfer/service.py`
- 图片工具业务：`backend/app/modules/image_tools/service.py`
- 图片工具请求模型：`backend/app/modules/image_tools/schemas.py`
