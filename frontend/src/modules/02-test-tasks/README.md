# test-tasks 测试任务

维护可复用的测试任务，并为每次运行创建独立执行批次。

- API 任务配置：`{"api_case_ids":[1,2]}`
- 性能任务配置：`{"performance_scenario_ids":[1]}`
- 性能任务标签配置：`{"performance_tags":["smoke"],"performance_tag_match":"any"}`
- JMeter 元数据配置：`{"jmeter":{"jmx_path":"tests/login.jmx","report_dir":"reports/login","jtl_path":"reports/login.jtl","variables":{"threads":10}}}`
- 页面已提供“接口用例集合”、“性能场景集合”、“性能标签选择”和 JMeter 元数据控件，保存时会自动写入任务配置 JSON。
- JMeter 字段只保存给 CI/JMeter 外部执行器读取，平台当前不会直接执行本地脚本。
- 执行后会进入结果中心和测试报告。
