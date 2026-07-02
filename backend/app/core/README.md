# backend/app/core

这里放后端通用能力，不直接承载某个页面的业务表单。

文件说明：

- `auth.py`：登录 token、密码哈希、当前用户、菜单权限校验。
- `config.py`：读取 `.env` 配置。
- `menu.py`：后台菜单权限注册表，新增菜单优先改这里。
- `target_guard.py`：测试目标地址安全校验，阻止访问 localhost、内网和云元数据地址。

修改建议：

- 新增菜单权限时改 `menu.py`。
- 新增认证规则时改 `auth.py`。
- 新增安全拦截规则时改 `target_guard.py`。
- 不要在业务接口里复制权限列表，统一引用 `menu.py`。
