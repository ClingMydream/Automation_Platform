# auth

认证入口：`backend/app/modules/auth/router.py`；令牌解析和菜单权限校验位于 `backend/app/core/auth.py`。

所有管理接口应复用现有认证依赖，不要在业务路由中自行解析令牌。
