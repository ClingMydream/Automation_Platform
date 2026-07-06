# frontend/src/modules

这里按左侧菜单顺序组织代码。目录名使用“编号 + 英文”，既能在文件管理器里按平台顺序排列，也能避免中文路径在 Git、Docker、脚本和远程服务器里出现编码问题。

每个模块现在采用单层结构：

```text
02-api-testing/
  ApiCasePanel.jsx     页面、表格、表单、按钮、弹窗等 UI 代码
  apiCaseFeature.js    功能实现、数据转换、接口调用、校验逻辑
  README.md            模块说明
```

改造原则：

- 改页面长什么样：改模块里的 `*Panel.jsx`、`Login.jsx`、`LiveRunWindow.jsx` 等页面文件。
- 改保存、删除、执行、统计、筛选等功能：改模块里的 `*Feature.js`。
- 多个模块都会用到的工具仍放在 `frontend/src/shared/`，不要在每个模块里重复复制。

平台菜单与代码目录一一对应：

```text
01-projects/          项目
01-test-objects/      测试对象
02-api-testing/       接口测试
03-ui-testing/        UI 测试
04-file-transfer/     文件快传
05-image-tools/       图片工具
06-json-tools/        JSON 工具
07-codec-tools/       转码工具
08-run-history/       执行记录
09-test-reports/      测试报告
10-user-management/   用户管理
```

辅助页面不直接显示在左侧菜单里，但仍按编号放在首尾：

```text
00-auth/              登录
90-live-run/          UI 自动化实时执行窗口
```
