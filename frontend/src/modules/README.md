# frontend/src/modules

这里是真正的前端业务模块目录。每个文件夹对应左侧菜单里的一个功能模块。

当前约定：

- `XxxPanel.jsx`：模块 UI 入口，负责页面布局、表格、表单和按钮。
- 纯算法和通用功能不要放在模块里，放到 `frontend/src/shared/`。
- 如果某个模块后续变复杂，可以在该模块目录内继续新增：
  - `components/`：只属于本模块的小组件。
  - `services.js`：只属于本模块的接口调用封装。
  - `constants.js`：只属于本模块的字段、选项、示例。
  - `README.md`：本模块改造说明。

模块列表：

- `auth/`：登录。
- `projects/`：项目管理。
- `apiTesting/`：接口测试用例页面。
- `uiTesting/`：UI 测试用例页面。
- `fileTransfer/`：文件快传后台页和手机扫码页。
- `imageTools/`：图片生成、裁剪和格式转换。
- `jsonTools/`：JSON 格式化和对比。
- `codec/`：通用转码。
- `runs/`：执行记录和执行详情。
- `reports/`：测试报告。
- `users/`：用户管理。
- `liveRun/`：UI 自动化实时执行窗口。
