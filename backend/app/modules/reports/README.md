# reports 测试报告

把执行记录 `test_runs` 和执行批次 `execution_batches` 汇总成前端可查看、可导出的测试报告。

- `router.py`：提供 `/api/reports`、`/api/reports/{run_id}`、`/api/reports/batches/{batch_id}`。
- `service.py`：负责解析用例名称、统计断言/步骤/截图数量、汇总批次结果和性能摘要。
- 单次报告会返回 `result_id`，前端可据此查询结果中心附件。
- 性能执行记录会从 `performance_scenarios` 解析名称，避免显示成“已删除用例”。
