# test_tasks 测试任务

维护可复用的测试任务，并为每次运行生成独立执行批次。

- `router.py`：任务 CRUD、启动任务、查询最近状态。
- `schemas.py`：任务和批次请求/响应模型。
- `service.py`：任务关系校验、编号唯一性、批次创建。
- API 任务会读取 `config.api_case_ids` 并创建接口执行记录。
- 性能任务会读取 `config.performance_scenario_ids` 并创建性能执行记录。
- 性能任务也支持读取 `config.performance_tags` 和 `config.performance_tag_match`，按标签自动选择启用中的性能场景。
