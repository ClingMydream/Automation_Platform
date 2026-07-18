# 开发说明

## 本地验证

```bash
python -m pytest backend/tests -q
python -m compileall -q backend/app
cd frontend
npm run build
```

## 目录边界

- `frontend/src/modules/`：登录、效率工具和系统配置页面。
- `frontend/src/shared/`：API 客户端与通用工具函数。
- `backend/app/modules/`：认证、数据生成、文件、图片、集成、用户和健康检查。
- `deploy/`：Nginx 与部署脚本。

不要重新引入测试任务、执行器、结果中心或 Worker；新功能应当是独立、低耦合的效率工具。
