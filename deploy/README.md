# 部署说明

The production directory is `/opt/automation-platform`.

首次部署：

```bash
bash deploy/scripts/init_server.sh
cp .env.example .env
vi .env
bash deploy/scripts/deploy.sh
```

主要服务包括 MySQL、后端、前端、Jenkins、Emote 在线预览和独立 UI 自动化 Runner。命名卷保存数据库、学习附件、测试包、Jenkins 数据、在线预览产物和自动化证据；部署不会主动删除这些持久化数据。

在线预览构建会只读拉取 Emote 分支，并在构建产物中注入测试后端 `https://www.inxpiration.cn/emote-test/api`。它不会修改或推送 Emote 源仓库。

Only TCP `22` and `80` should be open on the server and in the cloud security group.

如果 OpenCloudOS 仓库没有 `fail2ban`，初始化脚本仍会启用 `firewalld`；需要 SSH 封禁策略时可后续配置兼容的 EPEL 仓库。
