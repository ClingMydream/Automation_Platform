# test-capabilities 测试能力

维护 API 场景、Mock 规则、性能场景和 Runner 执行机。

当前版本只保存配置和调度接入信息，不执行任意脚本，避免形成远程代码执行入口。

- Mock 规则配置后可通过 `/api/mock/{path}` 公开访问。
- 例如规则路径 `/api/demo` 的访问地址是 `/api/mock/api/demo`。
- 性能场景可被测试任务通过 `performance_scenario_ids` 引用。
