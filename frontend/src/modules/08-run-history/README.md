# run-history 执行记录

- `RunsPanel.jsx`：执行记录列表。
- `RunDetail.jsx`：执行详情抽屉，展示日志、截图、UI 录屏、DOM 快照、性能指标和结果附件。
- `runHistoryFeature.js`：执行记录统计、按 ID 查找。
- 后端入口：`backend/app/modules/runs/router.py`。
- 批量任务沉淀到结果中心后，后端会返回 `result_id`，详情抽屉可按 `result_id` 上传或下载日志、截图、录屏、HAR、性能报告等附件。
