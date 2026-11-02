export const firstUnit = {
  id: "geekbang-python-01",
  title: "01｜配置 Python 开发环境",
  course: "零基础学 Python（新版）",
  url: "https://time.geekbang.org/course/detail/100310001-600294",
  body: '# 01｜配置 Python 开发环境\n\n课程：零基础学 Python（新版） · 尹会生 · 极客时间\n\n原课：[打开原视频](https://time.geekbang.org/course/detail/100310001-600294)\n\n依据：已登录课程页面的本节字幕、摘要及课后习题。以下为学习归纳，代码与测试练习是补充设计；不是课程逐字稿。\n\n## 学完应该能做什么\n\n解释解释器的作用，判断终端正在调用哪一个 Python，并成功运行一个脚本。\n\n## 课程核心归纳\n\nPython 程序需要解释器执行。安装前先确认操作系统，并从 Python 官网选择匹配的安装包。安装完成后通过终端检查版本，不能仅凭安装界面判断成功。机器上可能同时存在多个版本，命令指向的解释器与预期不同，会造成运行环境问题。课程以 macOS 演示；Windows 命令需要按本机环境调整。\n\n## Windows 补充实操\n\n先执行以下命令；某个命令不存在时保留错误信息，不代表电脑一定没有安装 Python：\n\n```powershell\npy --version\npython --version\nGet-Command python -All\n```\n\n运行代码，核对解释器路径：\n\n```python\nimport sys\n\nprint("Python 环境检查")\nprint(sys.version)\nprint(sys.executable)\nprint(2 + 3)\n```\n\n保存为 `environment_check.py`，执行 `py environment_check.py`；若本机使用的是 `python`，则执行 `python environment_check.py`。\n\n## 自己动手\n\n1. 记录安装前后版本命令的输出，完成原课习题。\n2. 运行脚本，确认最后一行输出为 `5`。\n3. 比较终端与 IDE 中 `sys.executable` 的输出。\n4. 用自己的话解释：安装了 Python，为什么仍可能提示命令不存在？\n\n## 参考答案（练习时先自己回答）\n\n命令查找依赖当前终端环境与 PATH；命令入口和解释器安装不是同一件事。也可能存在多版本，或 IDE 使用不同解释器。应结合版本与可执行文件路径判断，不能直接反复重装。\n\n## 与测试工作的联系\n\n遇到“在 IDE 能运行，终端却失败”时，先记录解释器路径、版本、工作目录和错误，再定位环境差异。本单元不要求安装所有测试依赖，也不把运行示例等同于完成自动化测试。\n\n## 验收与复习\n\n- 能独立运行脚本并解释关键输出。\n- 能说清自己使用的解释器，而非只背安装步骤。\n- 次日不看答案，重新运行并解释 `sys.executable`。\n\n学习记录：实际命令、输出、遇到的问题、解决方法和仍不理解的内容。\n',
  group: "第一章 非计算机专业学习编程的第一道门槛 (7讲)",
};
import catalog from "./pythonCourseCatalog.json";
export const learningUnits = catalog;
const loaders = import.meta.glob("./python-units/*.json", {
  import: "default",
});
export async function loadLearningUnit(id) {
  const loader = loaders["./python-units/" + id + ".json"];
  if (!loader) throw new Error("学习单元不存在");
  return loader();
}
