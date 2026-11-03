# Emote AI 模拟用户服务

交付单文件：`deliverables/emote_activity_service.py`。页面操作来自当前平台同一套 UI 脚本，内置依赖模块源码，运行时无需 Cling 后端、数据库、Runner Token 或仓库。仍需 Python 3.11+、Chromium、Playwright、httpx 和 tzdata。目标部署系统为 Linux。

支持浏览、AI 私密发帖、AI 私密日行一善、给本人测试帖点赞/评论/收藏、向霖感小秘书发送测试消息、签到与浇水、切换头像，以及明确开启后的 AI 公开任务帖互评。全部仅面向配置的专用 AI 账号；公开内容带“AI模拟用户”和时间戳，不伪装真人。没有删除好友、删除帖子或删除评论动作。

## 安装与运行

将 Python 文件、requirements.txt 和 config.example.json 上传至自有服务器，例如 `/opt/emote-activity`。为运行用户建立虚拟环境：

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

安装系统 Chromium 及中文/Emoji 字体，并将实际路径填写到配置 `chromium_path`。Debian/Ubuntu 示例（需管理员执行）：

```bash
apt-get update
apt-get install -y chromium fonts-noto-cjk fonts-noto-color-emoji
```

复制示例配置为 `config.json`，填写本人控制的站点地址和账号池的环境变量名称。凭据只通过服务器环境变量或权限为 600 的环境文件提供：

- `AI_ACCOUNT_A`、`AI_PASSWORD_A`、`AI_ACCOUNT_B`、`AI_PASSWORD_B`
- `DEEPSEEK_API_KEY`（AI 内容生成需要）
- `ACTIVITY_AI_MODEL`（可选，默认 `deepseek-flash`）

不要将实际密码或 API Key 写入配置、提交仓库或发送到聊天。多组账号使用不同变量名，每个真实账号只属于一组。

```bash
# 仅检查配置，不读取密码、不启动浏览器、不执行操作
.venv/bin/python emote_activity_service.py --config config.json

# 在配置时段内执行最多一个模拟会话
.venv/bin/python emote_activity_service.py --config config.json --data-dir ./activity-data --execute

# 按时段、随机间隔持续运行
.venv/bin/python emote_activity_service.py --config config.json --data-dir ./activity-data --serve --execute
```

默认 09:00–21:00，每 20–60 分钟检查一次，每组账号每天最多 3 次会话。一次会话选择一个动作；互评动作包含两篇帖子、两条评论，不等于一次写入。默认不包含公开互评：需要时设 `allow_public_interaction: true`，并在 `action_weights` 增加 `"mutual_comment": 1`。这些是权重，不是固定执行顺序。账号无当日额度或当前不在时段时不执行；单次模式直接退出。

可选动作键：`browse`、`post`、`kindness`、`water`、`mutual_comment`、`avatar`、`like`、`comment`、`favorite`、`chat`、`daily_tasks`。点赞/评论/收藏会先创建本人的 AI 私密测试帖，连同互动记录保留；聊天仅发往霖感小秘书，不向随机真人发送消息。账号需要提前准备，服务不会自动批量注册。

配置上限最大允许每组每天 100 次会话，间隔最短 60 秒。应按站点容量自行设置，服务不会自动扩大账号规模或提高频率。

## systemd

仓库提供 `emote-activity.service`。部署管理员先创建 `emote-activity` 专用系统用户、可写的 `/var/lib/emote-activity`，并让它可读 `/opt/emote-activity`；将配置安装为 `/etc/emote-activity.json`，凭据文件安装为 `/etc/emote-activity.env` 并限制权限。凭据文件只在服务器编辑。

安装 unit 到 `/etc/systemd/system/emote-activity.service`，核对路径和用户后：

```bash
systemctl daemon-reload
systemctl enable --now emote-activity
journalctl -u emote-activity -f
systemctl stop emote-activity
```

## 运行记录与恢复

- 数据目录使用独占锁，同一目录不允许启动两份服务。
- SQLite 台账在操作前预留当天额度。进程异常中断、部分写入或失败均计入额度，不自动重放写入。
- 登录态保留最多 24 小时；普通复用不延长期限，数据目录及环境文件必须妥善保护。
- 每次会话保存独立 `report.json`；失败时保留脱敏异常请求和截图。可用 `record_video: true` 开启录屏，会额外消耗资源。
- 标准输出仅包含会话摘要、Base URL 和失败原因。服务重启保留额度和登录态；不要删除数据目录来重置额度。
- SIGTERM/SIGINT 停止后续调度，等待当前 UI 动作结束；systemd 允许最长 180 秒收尾。

## 构建和验收边界

在仓库运行 `python scripts/build_emote_activity.py` 重新生成单文件，文件头保留源码 SHA256。修改平台页面定位后应重新打包；脚本不能保证未适配的未来 UI 版本仍可运行。

当前 Emote 测试后端返回 502，因此本次仅对配置校验、额度与时间段逻辑、打包一致性和入口进行离线验证；原平台的 AI 服务已真实调用通过。尚未在脱离平台的服务器上长期运行，也未将新服务启动为常驻进程。部署后应先用专用测试账号进行单次验收，再开启常驻模式。
