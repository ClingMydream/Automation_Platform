# test-objects 测试对象

这个模块对应测试平台分层中的“测试对象层”，用于沉淀平台到底要测什么。

- `TestObjectPanel.jsx`：页面、表单、筛选和表格。
- `testObjectFeature.js`：对象类型、表单数据转换和接口调用。
- 后端入口：`backend/app/modules/test_objects/router.py`。

第一批改造只新增旁路能力，不强制接口用例和 UI 用例立即绑定测试对象。
