# live-run 实时执行窗口

- `LiveRunWindow.jsx`：UI 自动化新窗口，轮询展示执行过程和最新截图。
- 数据来源：`backend/app/modules/runs/router.py`。
- UI 自动化完成后会展示 worker 写入 report 的 WebM 录屏。
- 录屏字段：`recording_url`、`recording_name`、`recording_error`。
- 失败定位字段：`dom_snapshot`、`dom_snapshot_error`、`failure_advice`。
