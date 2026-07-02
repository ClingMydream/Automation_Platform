# backend/app/modules

这里是后端业务模块目录。

当前每个业务模块都有自己的 `router.py`，`backend/app/api/routes.py` 只负责 include 这些模块 router。

- `auth/`：登录、退出、当前用户。
- `users/`：用户管理和菜单权限。
- `projects/`：项目与环境。
- `api_testing/`：接口测试用例。
- `ui_testing/`：UI 测试用例。
- `file_transfer/`：文件快传。
- `image_tools/`：图片生成、裁剪、格式转换。
- `runs/`：执行任务。
- `reports/`：测试报告。

继续改造规则：

- `router.py`：只放 FastAPI 路由、权限依赖和请求响应。
- `service.py`：放业务逻辑。
- `schemas.py`：放只属于本模块的请求/响应模型。
- `README.md`：写本模块改造说明。

已经独立出来的公共配置和公共 helper：

- 菜单权限：`backend/app/core/menu.py`
- 登录鉴权：`backend/app/core/auth.py`
- 地址安全校验：`backend/app/core/target_guard.py`
- 路由公共 helper：`backend/app/modules/common.py`
