# 开发说明

## 本地验证

```bash
python -m pytest backend/tests -q
python -m compileall -q backend/app
cd frontend
npm run build
```

## 目录边界

- `frontend/src/modules/`：登录、个人成长、效率工具、Emote 工程和系统配置页面。
- `frontend/src/shared/`：API 客户端与通用工具函数。
- `backend/app/modules/`：按功能拆分的 FastAPI 路由、服务和数据模型。
- `deploy/ui-runner/`：隔离的 Playwright 执行器，负责 Emote UI 自动化录屏、截图和 Trace。
- `deploy/jenkins/`：Emote 在线预览与 APK 构建流水线。
- `deploy/`：Nginx、Compose 辅助脚本和容器构建文件。

新增菜单时同时更新 `backend/app/core/menu.py`、前端入口、后端权限守卫和用户管理可分配权限。涉及 Emote 自动化时，不要把账号、密码、验证码或 Token 写入数据库日志、提交记录或普通错误提示。
