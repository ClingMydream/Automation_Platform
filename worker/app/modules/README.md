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
- UI 录屏会优先生成短视频预览；录屏文件也会复制到共享附件目录，批量任务完成后自动绑定到结果中心附件。

技术栈：

```text
Python 3 + pytest + Playwright + allure
```

后续要新增 UI 步骤，例如选择下拉框、悬停、上传文件、键盘操作，优先改：

```text
worker/app/modules/ui_automation/runtime.py
```

常用配置：

```text
UI_RECORD_VIDEO=true
UI_RECORD_VIDEO_MAX_MB=25
RESULT_ATTACHMENT_DIR=/tmp/automation-platform-attachments
RESULT_ATTACHMENT_MAX_MB=200
```

## performance_automation

性能自动化模块：

- `runner.py`：性能场景执行入口。
- `runtime.py`：轻量性能执行实现，使用 `requests` 并发采样公网 URL。

技术栈：

```text
Python 3 + requests + ThreadPoolExecutor
```

后续要接入 JMeter、Locust 或 PTS，优先在这个模块下新增适配器，不要把性能执行逻辑塞进前端页面。
