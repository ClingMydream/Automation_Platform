# test-reports 测试报告

- `ReportsPanel.jsx`：测试报告列表、筛选、导出入口。
- `testReportFeature.js`：报告筛选、统计、按 ID 查找。
- 后端入口：`backend/app/modules/reports/router.py`。
- HTML 导出模板：`frontend/src/shared/reportExport.js`。
- 单次 UI 报告会展示截图、录屏、失败建议和 DOM 快照。
- 单次性能报告会展示平均响应、P95、P99、TPS、错误率、样本数等指标。
- 批次报告会展示批次统计、性能摘要和结果明细。
