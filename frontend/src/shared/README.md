# frontend/src/shared

这里放前端通用代码。判断标准很简单：如果一段逻辑不依赖某个页面的状态，就优先放到这里。

文件说明：

- `codec.js`：通用转码算法。
- `jsonTools.js`：JSON 格式化和对比算法。
- `fileTransfer.jsx`：文件快传的类型识别、预览和下载。
- `formatters.js`：时间、耗时、文件大小、状态颜色格式化。
- `html.js`：HTML 转义。
- `reportExport.js`：HTML 测试报告导出模板。

修改建议：

- 新增通用函数时，先看是否能归到现有文件。
- 页面组件不要直接复制算法，应该从这里 import。
- 这里的函数尽量保持输入输出简单，方便以后写测试。
