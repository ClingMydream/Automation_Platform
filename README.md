# Automation Platform

自动化测试平台第一版，支持接口测试和低代码 UI 测试。项目使用 React + Vite、FastAPI、MySQL、Redis、Playwright Worker 和 Nginx，通过 Docker Compose 部署。

## 快速开始

```bash
cp .env.example .env
docker compose up -d --build
```

打开 `http://localhost`，使用 `.env` 中配置的管理员账号登录。

完整部署和使用说明见 `docs/小白部署与使用手册.md`。
