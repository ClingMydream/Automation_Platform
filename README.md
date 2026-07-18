# Toolbox

一个轻量的团队效率工具工作台，只保留效率工具与系统配置。

## 功能

- 数据生成：手机号格式、受控短信号码、合成身份证，支持复制和 JSON/CSV 导出。
- 文件快传：临时上传、二维码分享、手机回传。
- 图片工具：图片生成、裁剪、缩放、压缩、文字叠加和格式转换。
- JSON 工具：格式化、对比和差异查看。
- 转码工具：Base64、URL、Unicode 等常用转换。
- 集成配置：Webhook、钉钉、企微和飞书连通测试。
- 用户管理：账号、状态和菜单权限。

## 技术栈

React + Vite、FastAPI、MySQL、Nginx，通过 Docker Compose 部署。项目不再包含自动化测试 Worker、Redis、测试任务、执行记录或报告中心。

## 启动

```bash
cp .env.example .env
docker compose up -d --build
```

打开 `http://localhost`，使用 `.env` 中配置的管理员账号登录。

更多说明见 [docs/工具箱说明.md](docs/工具箱说明.md)。
