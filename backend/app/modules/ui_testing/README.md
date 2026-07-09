# ui_testing

UI 测试模块负责维护低代码 UI 自动化用例。

- 接口入口：`backend/app/modules/ui_testing/router.py`
- 执行入口：`worker/app/modules/ui_automation/`
- 录屏能力：worker 使用 Playwright 录制 WebM，并把 `recording_url` 写入执行 report。
- 失败定位：worker 在步骤失败时采集 `dom_snapshot`，并生成 `failure_advice`。
- 注意事项：短录屏直接内嵌 report；长录屏后续建议升级为结果中心附件。
