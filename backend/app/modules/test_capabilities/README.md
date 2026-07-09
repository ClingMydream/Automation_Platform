# test_capabilities 测试能力

维护测试平台“怎么测”的配置层：

- API 场景编排：变量、用例顺序、场景断言、前后置脚本说明。
- Mock 规则：保存 Mock 路径、方法、响应和延迟。
- 性能场景：并发、持续时间、升压时间、P95 和错误率阈值。
- Runner 管理：执行机类型、能力、状态和心跳。

当前版本以配置和调度接入为主，不在后端执行任意脚本，避免形成远程代码执行入口。

- Mock 规则维护接口在 `router.py`。
- Mock 公开响应出口在 `backend/app/modules/mock_service/`。
- 性能场景可被测试任务引用并由 worker 的 `performance_automation` 执行。
