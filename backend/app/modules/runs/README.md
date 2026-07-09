# runs 执行记录

负责创建单次自动化执行任务，并查询 worker 回写的执行状态和报告内容。

- `POST /api/runs`：创建接口或 UI 自动化执行任务，并推入 Redis 队列。
- `GET /api/runs`：查询最近执行记录。
- `GET /api/runs/{run_id}`：查询单条执行详情。
- 批量任务执行完成后，worker 会把结果沉淀到 `test_results`，本模块会额外返回 `result_id`，方便前端关联结果中心附件。
