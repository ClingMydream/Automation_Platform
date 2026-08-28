# users

用户管理与菜单权限入口：`backend/app/modules/users/router.py`。

新增平台菜单后，必须在 `backend/app/core/menu.py` 注册，再由本模块分配给用户；未授权用户不应看到菜单，也不能调用对应接口。
