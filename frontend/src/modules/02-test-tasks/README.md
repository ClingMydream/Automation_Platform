# test-tasks 测试任务

维护可复用的测试任务，并为每次运行创建独立执行批次。

- API 任务配置：`{"api_case_ids":[1,2]}`
- 性能任务配置：`{"performance_scenario_ids":[1]}`
- 性能任务标签配置：`{"performance_tags":["smoke"],"performance_tag_match":"any"}`
- 页面已提供“接口用例集合”、“性能场景集合”和“性能标签选择”控件，保存时会自动写入任务配置 JSON。
- 执行后会进入结果中心和测试报告。
