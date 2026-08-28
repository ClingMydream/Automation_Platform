# cling

面向测试工程师的个人工作与成长平台。它把学习计划、测试数据、接口调试、在线预览、APK 构建和 Emote Web UI 自动化集中在一个受权限控制的站点中。

## 当前功能

- 个人成长：Python、HTTP 与接口自动化能力关卡，包含逐行讲解、掌握门槛、学习计时、卡点和自动关卡笔记。
- 测试工作台：测试数据生成、接口记录与调试、Restful Booker 中文练习项目、命令手册。
- 效率工具：文件快传、测试包二维码下载、图片处理、JSON 与文本转码、临时效果页。
- Emote 工程：分支在线预览、Jenkins Debug APK 构建、构建产物下载。
- Emote UI 自动化：结构化用例、测试数据集、桌面/390×844 手机视口、录屏、截图、Trace 和失败接口诊断。
- 系统配置：集成配置、用户与菜单权限管理。

## 技术栈

React + Vite、FastAPI、MySQL、Nginx、Jenkins 和独立 Playwright Runner，通过 Docker Compose 部署。

## 关键访问路径

- 主站：`/`
- Emote 在线预览：`/emote-preview/`
- Emote UI 自动化：`/emote-ui-automation`
- Jenkins：`/jenkins/`

## 启动

```bash
cp .env.example .env
docker compose up -d --build
```

打开 `http://localhost`，使用 `.env` 中配置的管理员账号登录。

部署与环境配置见 [deploy/README.md](deploy/README.md)，开发验证见 [CONTRIBUTING.md](CONTRIBUTING.md)。
