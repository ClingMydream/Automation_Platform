from calendar import monthrange
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import (LearningAttachment, LearningCheckin, LearningImport, LearningNote,
    LearningNoteFolder, LearningPlan, LearningProfile, LearningScheduleShift, LearningStudyTimer, LearningTask)

SEED = "learning_seed_v1"
TOPICS = [
    ("接口基础", "环境与首个接口测试", "配置 Python、Postman，完成 Restful Booker 首个 pytest 用例"),
    ("接口基础", "查询与异常场景", "覆盖查询、参数、状态码和负向场景"),
    ("接口基础", "Python 请求封装", "用函数和类封装 Restful Booker API"),
    ("接口基础", "Pytest 与断言", "掌握收集规则、断言并完成 10 个用例"),
    ("接口基础", "参数化", "使用 parametrize 消除重复测试代码"),
    ("接口基础", "鉴权与 CRUD 链路", "串联创建、查询、更新、删除及清理"),
    ("接口基础", "阶段复盘", "整理 15 个用例并录制 5 分钟讲解"),
    ("Pytest 项目化", "Fixture 与 conftest", "抽取登录、数据准备和清理 fixture"),
    ("Pytest 项目化", "多环境配置", "实现测试环境和配置切换"),
    ("Pytest 项目化", "测试数据分离", "从 JSON/YAML 加载测试数据"),
    ("Pytest 项目化", "请求工具层", "统一请求、响应与公共头处理"),
    ("Pytest 项目化", "日志体系", "输出可定位问题的结构化日志"),
    ("Pytest 项目化", "异常与清理", "处理失败、重试边界和数据清理"),
    ("Pytest 项目化", "项目交付", "完成 README 和至少 30 个可运行用例"),
    ("SQL/Linux/项目", "SQL 查询基础", "练习条件、排序、分页"),
    ("SQL/Linux/项目", "聚合查询", "练习聚合函数、分组和 HAVING"),
    ("SQL/Linux/项目", "多表连接", "掌握 INNER JOIN 和 LEFT JOIN"),
    ("SQL/Linux/项目", "SQL 综合练习", "完成子查询与累计 50 道 SQL 题"),
    ("SQL/Linux/项目", "Linux 日志", "掌握 grep、tail、less 定位日志"),
    ("SQL/Linux/项目", "Linux 系统排查", "掌握进程、端口和资源排查"),
    ("SQL/Linux/项目", "真实项目梳理", "整理业务、职责、测试策略和数据流"),
    ("SQL/Linux/项目", "质量故事", "整理典型缺陷和质量改进案例"),
    ("Git/Allure/Jenkins", "Git 工作流", "练习分支、提交、合并和冲突处理"),
    ("Git/Allure/Jenkins", "Allure 报告", "接入步骤、附件和趋势报告"),
    ("Git/Allure/Jenkins", "Jenkins 入门", "创建并运行自动化测试任务"),
    ("Git/Allure/Jenkins", "流水线", "使用 Jenkinsfile 构建流水线"),
    ("Git/Allure/Jenkins", "持续集成", "打通拉取、测试、报告完整流程"),
    ("Git/Allure/Jenkins", "作品集打磨", "清理仓库、演示脚本和 README"),
    ("求职冲刺", "简历项目", "把项目成果改写成量化简历要点"),
    ("求职冲刺", "简历定稿", "完成技能、经历和个人简介"),
    ("求职冲刺", "接口面试题", "复习 HTTP、接口测试设计和排障"),
    ("求职冲刺", "Python/Pytest 面试题", "完成核心题目和代码练习"),
    ("求职冲刺", "SQL/Linux 面试题", "完成常见查询和排障口述"),
    ("求职冲刺", "项目表达", "模拟讲解项目架构、难点和收益"),
    ("求职冲刺", "开始投递", "筛选成都岗位并记录首批投递"),
    ("求职冲刺", "投递复盘", "继续投递并根据反馈修正材料"),
    ("求职冲刺", "短板补强", "针对暴露问题进行专项练习"),
    ("求职冲刺", "全流程模拟面试", "完成一次技术与项目综合模拟"),
    ("求职冲刺", "最终演示", "从零运行项目并完成稳定演示"),
    ("求职冲刺", "收官与持续投递", "复核简历、作品集和后续投递清单"),
]

DOCUMENT_TOPICS = [
    ("认识项目", "第一次完成酒店预约", "打开酒店前台，以普通用户身份浏览房间并完成一次预约"),
    ("认识项目", "前端、后端和数据库", "从预约流程理解页面、接口和数据分别负责什么"),
    ("认识项目", "什么是 API", "用生活化例子理解请求、响应和接口地址"),
    ("认识项目", "URL 与请求方法", "认识 URL、GET、POST、PUT 和 DELETE"),
    ("认识项目", "浏览器 Network", "观察一次页面操作产生的真实网络请求"),
    ("Postman", "第一个 GET 请求", "在 Postman 查询 Booking 列表"),
    ("Postman", "状态码与 JSON", "读懂 200、404 和 JSON 响应"),
    ("Postman", "创建 Booking", "使用 JSON 请求体创建一条预约"),
    ("Postman", "登录与 Token", "调用认证接口并理解 Token 的用途"),
    ("Postman", "手工 CRUD", "完成创建、查询、修改和删除完整流程"),
    ("Python 基础", "变量、字符串与输出", "用变量保存数据并使用 print 查看结果"),
    ("Python 基础", "数字、布尔值与比较", "理解状态码比较和真假结果"),
    ("Python 基础", "列表与字典", "读懂 Booking 的列表和 JSON 对象"),
    ("Python 基础", "if 条件判断", "根据响应状态执行不同处理"),
    ("Python 基础", "for 循环", "遍历 Booking 列表并输出 ID"),
    ("Python 基础", "函数与参数", "把重复操作写成可以调用的函数"),
    ("Python 基础", "文件、模块与 import", "拆分 Python 文件并导入 requests"),
    ("Requests", "Python 第一个 GET", "用 requests 查询 Booking 列表"),
    ("Requests", "读取状态码和 JSON", "解析响应并检查关键字段"),
    ("Requests", "发送 POST", "用 Python 创建 Booking"),
    ("Requests", "Headers 与 Token", "携带认证信息访问受保护接口"),
    ("Requests", "PUT 与 DELETE", "修改并删除自己创建的数据"),
    ("Requests", "单文件 CRUD", "在一个脚本中串联完整预约流程"),
    ("Pytest 入门", "为什么需要 pytest", "把普通脚本改成可重复运行的测试"),
    ("Pytest 入门", "第一条用例与 assert", "编写并运行第一条自动化测试"),
    ("Pytest 入门", "测试发现规则", "理解 test_ 文件和函数命名规则"),
    ("Pytest 入门", "Fixture", "复用客户端和测试数据准备过程"),
    ("Pytest 入门", "参数化", "使用同一段测试覆盖多组输入"),
    ("Pytest 入门", "异常场景与失败报告", "读懂失败信息并定位问题"),
    ("项目重构", "发现重复代码", "找出重复 URL、超时和请求调用"),
    ("项目重构", "提取配置", "统一 base_url、timeout 和 headers"),
    ("项目重构", "封装请求方法", "封装 get、post、put、delete"),
    ("项目重构", "BookerClient", "封装面向预约业务的客户端方法"),
    ("项目重构", "重写已有用例", "用客户端重写此前的 pytest 用例"),
    ("项目成果", "测试数据与参数化", "分离测试数据并增加场景覆盖"),
    ("项目成果", "日志与排错", "记录请求、响应和错误上下文"),
    ("项目成果", "Allure 报告", "生成可展示的自动化测试报告"),
    ("项目成果", "Git 与 README", "整理提交记录和项目使用文档"),
    ("项目成果", "SQL、Linux 与 Jenkins 串联", "理解测试项目的持续执行和排查链路"),
    ("项目成果", "项目验收与面试讲解", "从零运行项目并用自己的话讲清设计"),
]


def local_today() -> date:
    return datetime.now(ZoneInfo(get_settings().app_timezone)).date()


def ensure_seed(db: Session):
    profile = db.scalar(select(LearningProfile).where(LearningProfile.seed_version == SEED))
    if profile:
        return profile
    profile = LearningProfile(seed_version=SEED, years_experience=6, current_role="功能测试工程师",
        target_role="中级/接口自动化测试工程师", target_city="成都", current_salary="约 8K",
        target_salary="约 12K", target_date=date(2026, 8, 31), daily_target_minutes=300,
        current_focus="Restful Booker 第 1 天任务（尚未完成）", strengths=["功能测试", "需求分析", "用例设计"],
        gaps=["Python", "接口自动化", "SQL", "Linux", "可展示项目"])
    plan = LearningPlan(title="40 天测试能力提升计划", original_start_date=date(2026, 7, 22),
        original_end_date=date(2026, 8, 30), projected_end_date=date(2026, 8, 30), status="active")
    db.add_all([profile, plan]); db.flush()
    for i, (phase, title, details) in enumerate(TOPICS, 1):
        day = plan.original_start_date + timedelta(days=i - 1)
        db.add(LearningTask(plan_id=plan.id, day_number=i, phase=phase, category="实操", title=title,
            details=details, acceptance_criteria=f"形成可运行或可展示的成果，并能口述说明：{title}",
            expected_minutes=240, original_planned_date=day, planned_date=day, sort_order=1))
        db.add(LearningTask(plan_id=plan.id, day_number=i, phase=phase, category="复盘", title="当日练习与复盘",
            details="补充练习、整理笔记并记录问题", acceptance_criteria="完成学习笔记和当日复盘",
            expected_minutes=60, original_planned_date=day, planned_date=day, sort_order=2))
    db.commit()
    return profile


def restart_learning(db: Session, start_date: date, title: str):
    ensure_seed(db)
    for old_plan in db.scalars(select(LearningPlan).where(LearningPlan.status == "active")).all():
        old_plan.status = "archived"
    end_date = start_date + timedelta(days=len(DOCUMENT_TOPICS) - 1)
    plan = LearningPlan(title=title, original_start_date=start_date, original_end_date=end_date,
        projected_end_date=end_date, status="active")
    db.add(plan); db.flush()
    for number, (phase, topic, details) in enumerate(DOCUMENT_TOPICS, 1):
        planned = start_date + timedelta(days=number - 1)
        db.add(LearningTask(plan_id=plan.id, day_number=number, phase=phase, category="文档实操",
            title=topic, details=details, acceptance_criteria=f"完成跟做、填空和独立练习，并能用自己的话解释：{topic}",
            expected_minutes=180, original_planned_date=planned, planned_date=planned, sort_order=1))
        db.add(LearningTask(plan_id=plan.id, day_number=number, phase=phase, category="复盘",
            title="当日练习与复盘", details="整理操作结果、错误和自己的理解",
            acceptance_criteria="保存练习结果并完成当日学习笔记", expected_minutes=60,
            original_planned_date=planned, planned_date=planned, sort_order=2))
    db.commit(); db.refresh(plan)
    return plan


def reset_learning_space(db: Session, start_date: date, title: str):
    """Remove only personal learning records, retain the profile, then create a clean plan."""
    settings = get_settings()
    for attachment in db.scalars(select(LearningAttachment)).all():
        (Path(settings.learning_data_dir) / "attachments" / attachment.stored_name).unlink(missing_ok=True)
    # Explicit child deletion also supports databases created before foreign-key cascades existed.
    for model in (LearningAttachment, LearningNote, LearningNoteFolder, LearningCheckin, LearningStudyTimer,
                  LearningScheduleShift, LearningTask, LearningPlan, LearningImport):
        db.execute(delete(model))
    db.commit()
    return restart_learning(db, start_date, title)


def reconcile(db: Session):
    ensure_seed(db); today = local_today()
    active_plan = db.scalar(select(LearningPlan).where(LearningPlan.status == "active"))
    overdue = db.scalar(select(LearningTask).where(LearningTask.plan_id == active_plan.id, LearningTask.status != "completed", LearningTask.planned_date < today).order_by(LearningTask.planned_date))
    if not overdue:
        return {"shifted": False, "days_shifted": 0}
    days = (today - overdue.planned_date).days
    plan = db.get(LearningPlan, overdue.plan_id)
    tasks = db.scalars(select(LearningTask).where(LearningTask.plan_id == plan.id, LearningTask.status != "completed", LearningTask.planned_date >= overdue.planned_date)).all()
    for task in tasks: task.planned_date += timedelta(days=days)
    plan.projected_end_date += timedelta(days=days)
    db.add(LearningScheduleShift(plan_id=plan.id, shifted_on=today, days_shifted=days, earliest_overdue_date=overdue.planned_date))
    db.commit()
    return {"shifted": True, "days_shifted": days, "projected_end_date": plan.projected_end_date}


def stats(db: Session, month: str):
    year, mon = map(int, month.split("-")); start = date(year, mon, 1); end = date(year, mon, monthrange(year, mon)[1])
    plan = db.scalar(select(LearningPlan).where(LearningPlan.status == "active"))
    tasks = db.scalars(select(LearningTask).where(LearningTask.plan_id == plan.id, LearningTask.planned_date.between(start, end))).all()
    checks = db.scalars(select(LearningCheckin).where(LearningCheckin.checkin_date.between(start, end))).all()
    by_day = {}
    for task in tasks:
        row = by_day.setdefault(str(task.planned_date), {"total": 0, "completed": 0, "minutes": 0, "checked_in": False})
        row["total"] += 1; row["completed"] += task.status == "completed"
    for check in checks:
        row = by_day.setdefault(str(check.checkin_date), {"total": 0, "completed": 0, "minutes": 0, "checked_in": False})
        row.update({"checked_in": True, "minutes": check.actual_minutes, "gains": check.gains,
            "blockers": check.blockers, "tomorrow_focus": check.tomorrow_focus})
    completed = sum(t.status == "completed" for t in tasks)
    dates = sorted(c.checkin_date for c in checks)
    streak = 0; cursor = local_today()
    while cursor in dates: streak += 1; cursor -= timedelta(days=1)
    return {"month": month, "checkin_days": len(dates), "current_streak": streak, "total_minutes": sum(c.actual_minutes for c in checks),
        "task_completion_rate": round(completed / len(tasks) * 100, 1) if tasks else 0, "days": by_day}
