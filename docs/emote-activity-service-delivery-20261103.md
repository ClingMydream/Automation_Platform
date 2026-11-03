# 独立 AI 模拟用户服务交付

代码与交付文件已推送，应用版本 `ce3df4b`。

交付文件：

- `deliverables/emote_activity_service.py`：内置页面操作和脱敏模块源码的单文件服务入口，不依赖 Cling 后端或 Runner Token。
- `deliverables/emote_activity_service.zip`：Python 文件、示例配置、requirements、systemd unit 和部署说明。
- `deliverables/emote_activity_checksums.json`：Python 文件与压缩包的 SHA256。
- `deploy/activity-service/README.md`：详细安装、单次运行、常驻启动和停止方式。

服务器副本：`/opt/cling-artifacts/emote-activity/ce3df4b/`。该目录是交付物存放位置；未安装或启用新的常驻活跃服务，也未复制平台真实账号密码到示例配置。

功能包括专用 AI 账号池、随机动作权重、运行时段和随机间隔、每组每日会话上限、SQLite 额度台账、单实例锁、24 小时登录态、AI 内容生成、私密发帖、日行一善、点赞/评论/收藏本人测试帖、小秘书聊天、签到/浇水、头像与明确开启的公开互评。公开内容标记 AI 模拟身份，所有记录保留，不提供删除动作或自动批量注册。

默认仅检查配置；`--execute` 才操作账号，`--serve --execute` 才持续调度。账号和 AI Key 通过环境变量提供。默认每天 09:00–21:00，每组最多 3 次会话，间隔 20–60 分钟。一次互评会话包含多次业务写入，具体数量见部署说明。

验证：26 项脚本及打包相关测试通过；单文件复制到仓库外可以独立检查配置；Linux 容器中直接运行交付文件的配置检查通过、未执行操作；服务器文件 SHA256 与交付校验文件一致。平台执行器仅抽取了 AI 提供方方法用于复用，重构相关回归通过，已备份后发布，服务健康。

限制：Emote 测试 API 仍返回 502，未进行独立服务真实业务及长期稳定性验收。平台 AI 调用历史验证成功不等于独立服务长期运行通过。目标 UI 版本升级后可能需要重新适配和打包。
