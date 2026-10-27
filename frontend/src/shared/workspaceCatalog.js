export const SECTION_META = {
  testing: {
    number: "01",
    english: "QUALITY & CONFIDENCE",
    title: "让每一次发布，更有把握。",
    tone: "violet",
  },
  growth: {
    number: "02",
    english: "LEARN & BECOME",
    title: "小小的积累，也会闪光。",
    tone: "sage",
  },
  tools: {
    number: "03",
    english: "MAKE ROOM FOR FOCUS",
    title: "琐事交给工具，专注留给你。",
    tone: "peach",
  },
  settings: {
    number: "04",
    english: "CONNECTED & ORGANIZED",
    title: "一切就绪，工作自然顺畅。",
    tone: "blue",
  },
};

export const MODULE_META = {
  home: {
    description: "测试、学习与日常工作，在这里轻轻连接。",
    keywords: "首页 工作台 home dashboard",
  },
  emote_ui_automation: {
    description: "从一条用例到完整回归，让过程可见，让结果有据。",
    keywords: "ui emote 自动化 用例 回归 视频 截图",
  },
  circle_stats: {
    description: "收集团队反馈，核对每一条记录，再有序归入表格。",
    keywords: "钉钉 圈 采集 统计",
  },
  api_workspace: {
    description: "把接口、参数与调试经验，整理成随手可用的工作资产。",
    keywords: "api 接口 http 请求",
  },
  jenkins: {
    description: "连接构建流程，清楚地知道一次交付走到了哪里。",
    keywords: "jenkins ci 构建 打包",
  },
  online_preview: {
    description: "核对分支、同步版本，在真实页面里确认每一次变化。",
    keywords: "预览 preview 分支 同步",
  },
  test_packages: {
    description: "上传、分享与下载，让测试包顺畅到达需要的设备。",
    keywords: "apk 包 安装 下载",
  },
  learning: {
    description: "把知识变成练习，把练习变成自己的理解。",
    keywords: "学习 python 笔记 章节",
  },
  self_study: {
    description: "一次专注，一道题目；让每一步进步都有迹可循。",
    keywords: "考试 自考 答题 评分 deepseek",
  },
  command_library: {
    description: "收好那些解决过问题的命令，下次遇见时从容一点。",
    keywords: "命令 shell 收藏 手册",
  },
  restful_booker: {
    description: "在独立练习项目中，走通从请求到验证的完整链路。",
    keywords: "酒店 booker 预约 练习",
  },
  effects: {
    description: "给灵感一个可以运行、预览与分享的地方。",
    keywords: "效果 demo 演示 上传",
  },
  work_journal: {
    description: "记录今天的小进展，让日报与周报自然生长。",
    keywords: "日报 周报 日志 记录 工作手记",
  },
  data_generator: {
    description: "准备有规则、有边界的测试数据，把重复工作留在身后。",
    keywords: "手机号 身份证 账号 数据 批次",
  },
  files: {
    description: "让文件轻松跨越设备，从上传到扫码一步衔接。",
    keywords: "文件 传输 扫码 上传 下载",
  },
  images: {
    description: "尺寸、格式与压缩，一处完成日常图片处理。",
    keywords: "图片 压缩 裁切 格式 生成",
  },
  json_tools: {
    description: "格式化、比对与检查，把复杂结构看得清清楚楚。",
    keywords: "json 格式化 差异 比对",
  },
  codec: {
    description: "编码与解码随手切换，让文本回到容易理解的样子。",
    keywords: "base64 hex url unicode 转码",
  },
  family_oa_web: {
    description: "认真对待生活里的小计划，也温柔记录每一笔日常。",
    keywords: "审批 记账 莓好 家庭",
  },
  integrations: {
    description: "连接外部工具，把协作放进熟悉的工作流。",
    keywords: "配置 webhook 集成 通知",
  },
  users: {
    description: "清晰管理成员与权限，让每个人拥有合适的工作空间。",
    keywords: "用户 账号 权限 成员",
  },
  oa_management: {
    description: "维护审批成员与协作关系，让日常流程更有秩序。",
    keywords: "oa 小程序 人员 审核人",
  },
};

export function searchModules(items, query) {
  const terms = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  return items.filter((item) =>
    terms.every((term) =>
      `${item.label} ${item.sectionLabel || ""} ${MODULE_META[item.key]?.keywords || ""}`
        .toLocaleLowerCase()
        .includes(term),
    ),
  );
}

export function readRecentModules(storage, username, allowedKeys) {
  try {
    const rows = JSON.parse(
      storage.getItem(`cling:workspace:${username}:recent:v1`) || "[]",
    );
    if (!Array.isArray(rows)) return [];
    const seen = new Set();
    return rows
      .filter(
        (row) =>
          row &&
          allowedKeys.includes(row.key) &&
          row.key !== "home" &&
          Number.isFinite(row.at) &&
          Number.isFinite(new Date(row.at).getTime()) &&
          !seen.has(row.key) &&
          seen.add(row.key),
      )
      .slice(0, 5);
  } catch {
    return [];
  }
}
