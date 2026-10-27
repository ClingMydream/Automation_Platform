# 平台隔离自测

只允许在本机隔离环境运行。脚本固定访问 `127.0.0.1:3104`，使用 `audit-admin` 测试账号；禁止改成生产地址。数据、附件均保存在 `output/platform-audit-20261026`，外部执行器地址不可达，Webhook 投递与 AI 评分使用模拟响应，不会发送真实消息。

1. 在项目根目录运行 `.venv/Scripts/python.exe scripts/run_platform_audit_backend.py`，后端监听 8001，使用独立 SQLite 数据库。现有本地后端占用 8001 时先停止它。
2. 在 frontend 目录运行 `npm run dev -- --port 3104`。若要重复完整测试，使用新的隔离目录/数据库，不要清理生产存储。
3. 使用 Playwright CLI 打开本机页面，使用脚本中公开的隔离账号登录，或先执行 `account-progress.js` 初始化登录状态。该脚本专门验证账号切换与旧进度归属。
4. 按顺序通过 `playwright-cli run-code --filename` 执行 `core-flows.js`、`extended-flows.js`、`error-flows.js`。最后一个脚本验证 401 后会退出登录；重新执行 account-progress.js 可恢复隔离管理员。
5. `inventory.js` 遍历含工作台的 19 个功能视图及 1440、1280、768、390、320px，检查页面宽度、可见按钮与未处理页面异常。组合入口内各页签通过原 URL 分别检查。
6. `populated-history.js` 额外模拟 32 条用例、历史执行、超长分支和网址，检查五档布局及用例区独立滚动。它补充空数据检查覆盖不到的最小内容宽度问题。
7. `workspace-design.js` 验证新工作台搜索、键盘末项滚动、访问记录、前进后退、手机抽屉和权限过滤。CLI 脚本保留单个函数表达式，末尾不要添加分号。
8. `password-target.js` 验证登录密码显隐、输入保留、五档按钮尺寸及页面宽度。
9. `lightweight-entry.js` 验证公开登录按需加载工作框架、登录和退出、刷新恢复、更新提示保留输入，以及仅会话存储的登录恢复和退出清理。
10. `public-entries.js` 验证无效分享链接与公开测试包的异常恢复，不依赖已登录框架。
11. `login-errors.js` 使用模拟 503 验证登录错误可见、输入保留、记住选项传递、重复点击保护和重试。
12. `cleanup-flows.js` 验证下线接口 404、合并权限不扩散、旧 URL、简洁日志和折叠历史字段保存。酒店和审批独立地址的 410 在部署后验证。

每个流程的结果为 `passed` / `failed`，必须检查全部 results 和 errors；CLI 退出码本身不能证明所有业务流程通过。失败重跑只针对原失败项，保留首次失败与修复记录。

自考主观题使用现有 `tests/self-study-written-smoke.html`，脚本 `self-study-written-browser-check.js` 的本机端口改为 3104；自动化专项入口使用 `tests/emote192-smoke.html` 与现有 `emote192-browser-check.js`，需要先打开对应 fixture。二者均为模拟外部依赖的组件检查。

真实钉钉扫码/在线表格写入、Jenkins 构建发布、Emote 业务端运行、真实 DeepSeek 服务可用性，需要各自独立验收。模拟通过不得记录为这些真实链路通过。
