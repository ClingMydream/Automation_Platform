# worker/app/modules

这里是自动化执行模块，和前端页面解耦。

## api_automation

接口自动化模块：

- `runner.py`：pytest 调度入口，创建临时测试文件并运行 pytest。
- `runtime.py`：接口测试真实实现，使用 `requests` 发请求，使用 `allure` 记录请求和响应附件。

技术栈：

```text
Python 3 + pytest + requests + allure
```

后续要新增接口断言，例如响应时间断言、Header 断言、JSON Schema 断言，优先改：

```text
worker/app/modules/api_automation/runtime.py
```

## ui_automation

UI 自动化模块：

- `runner.py`：pytest 调度入口，创建临时测试文件并运行 pytest。
- `runtime.py`：UI 测试真实实现，使用 Playwright 操作浏览器，使用 `allure.step` 和截图附件记录过程。

技术栈：

```text
Python 3 + pytest + Playwright + allure
```

后续要新增 UI 步骤，例如选择下拉框、悬停、上传文件、键盘操作，优先改：

```text
worker/app/modules/ui_automation/runtime.py
```
