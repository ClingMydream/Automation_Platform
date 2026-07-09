# Automation Platform

自动化测试平台第一版，支持接口测试和低代码 UI 测试。项目使用 React + Vite、FastAPI、MySQL、Redis、Playwright Worker 和 Nginx，通过 Docker Compose 部署。

## 快速开始

```bash
cp .env.example .env
docker compose up -d --build
```

打开 `http://localhost`，使用 `.env` 中配置的管理员账号登录。

完整部署和使用说明见 `docs/小白部署与使用手册.md`。

## 同步改造进度

如果你需要在不同电脑之间同步开发进度，先看：

- `docs/改造进度同步记录.md`
- `CONTRIBUTING.md`
- `项目总说明.md`

## 参与代码改造

如果你想自己参与编写和改造代码，先看：

- `项目总说明.md`
- `docs/代码改造指南.md`
- `docs/模块化架构说明.md`
- `frontend/src/modules/README.md`
- `frontend/src/shared/README.md`
- `backend/app/modules/README.md`
- `worker/app/modules/README.md`
- `backend/app/core/README.md`
