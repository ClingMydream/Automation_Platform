# 问题定位页面

本页面对应后端 `problem_diagnosis` 模块，用来把失败结果沉淀成可跟踪的问题定位记录。

- `ProblemDiagnosisPanel.jsx`：页面 UI，左侧展示失败结果，右侧展示问题定位记录。
- `problemDiagnosisFeature.js`：状态、严重级别和表单 payload 的纯函数配置。

后续改造建议：

- 接入缺陷平台时，在本模块新增“提交缺陷”按钮，不要直接改结果中心。
- 增加 AI 分析时，建议只读取失败证据，不执行用户输入脚本。
