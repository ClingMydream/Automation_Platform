# frontend/src/modules

这里按左侧菜单的含义组织代码，但目录名使用英文，避免中文路径在 Git、Docker、脚本和远程服务器里出现编码问题。

每个模块固定分两类：

```text
api-testing/
  feature/   放功能实现、数据转换、接口调用、校验逻辑
  ui/        放页面、表格、表单、按钮、弹窗等 UI 代码
```

改造原则：

- 改页面长什么样：进对应模块的 `ui/`。
- 改保存、删除、执行、统计、筛选等功能：进对应模块的 `feature/`。
- 多个模块都会用到的工具仍放在 `frontend/src/shared/`，不要在每个模块里重复复制。

当前模块：

```text
auth/             登录
projects/         项目
api-testing/      接口测试
ui-testing/       UI 测试
file-transfer/    文件快传
image-tools/      图片工具
json-tools/       JSON 工具
codec-tools/      转码工具
run-history/      执行记录
test-reports/     测试报告
user-management/  用户管理
live-run/         实时执行窗口
```
