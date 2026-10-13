"""Tests for the work journal module.

这些测试走完整的 HTTP 与鉴权链路（真实 JWT -> get_current_user -> require_menu -> 数据库持久化），
不通过直接调用内部函数绕过权限，符合方案第 12 节"不能只直接调用函数绕过权限"的要求。
"""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.auth import create_access_token, hash_password
from app.db import Base, get_db
from app.models.entities import AppUser, WorkJournalReport
from app.modules.work_journal import assemble
from app.modules.work_journal.dates import today_shanghai, week_range
from app.modules.work_journal.router import router as work_journal_router

PREFIX = "/api/v1/work-journal"
MENU = ["work_journal"]


@pytest.fixture()
def env(tmp_path):
    """Spin up the module on a private SQLite database with three real users."""
    engine = create_engine(f"sqlite:///{tmp_path / 'journal.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with TestingSession() as db:
        db.add_all(
            [
                AppUser(username="alice", display_name="爱丽丝", password_hash=hash_password("x"), menu_permissions=MENU),
                AppUser(username="bob", display_name="鲍勃", password_hash=hash_password("x"), menu_permissions=MENU),
                AppUser(username="carol", display_name="卡罗", password_hash=hash_password("x"), menu_permissions=[]),
            ]
        )
        db.commit()

    app = FastAPI()
    app.include_router(work_journal_router, prefix="/api")

    def override_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    return SimpleNamespace(
        client=client,
        session=TestingSession,
        alice={"Authorization": f"Bearer {create_access_token('alice')}"},
        bob={"Authorization": f"Bearer {create_access_token('bob')}"},
        carol={"Authorization": f"Bearer {create_access_token('carol')}"},
    )


def entry_payload(**overrides):
    """Build a valid entry payload with sane defaults."""
    payload = {
        "client_request_id": "req-0000-0000-0000-000000000001",
        "work_date": today_shanghai().isoformat(),
        "title": "登录接口自动化",
        "body_markdown": "编写登录接口自动化用例",
        "category": "自动化开发",
        "progress_status": "in_progress",
        "tags": ["自动化", "登录"],
    }
    payload.update(overrides)
    return payload


def make_entry(env, headers, **overrides):
    """Create one entry through the API and return its JSON body."""
    response = env.client.post(f"{PREFIX}/entries", json=entry_payload(**overrides), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def make_daily(env, headers, day, items, *, quality="", reflection="", blockers=None, next_plan=None, complete=True):
    """Create and optionally complete one daily report with the given body."""
    created = env.client.post(
        f"{PREFIX}/reports", json={"report_type": "daily", "period_start": day.isoformat()}, headers=headers
    )
    if created.status_code == 409:
        report_id = created.json()["detail"]["report_id"]
        current = env.client.get(f"{PREFIX}/reports/{report_id}", headers=headers).json()
    else:
        assert created.status_code == 201, created.text
        current = created.json()
        report_id = current["id"]
    sections = {
        "items": items,
        "quality": quality,
        "blockers": blockers or [],
        "next_plan": next_plan or [],
        "reflection": reflection,
    }
    saved = env.client.put(
        f"{PREFIX}/reports/{report_id}",
        json={"title": current["title"], "sections": sections, "revision": current["revision"]},
        headers=headers,
    )
    assert saved.status_code == 200, saved.text
    current = saved.json()
    if complete:
        done = env.client.post(
            f"{PREFIX}/reports/{report_id}/complete", json={"revision": current["revision"]}, headers=headers
        )
        assert done.status_code == 200, done.text
        current = done.json()
    return current


def daily_item(name, progress, result="", project="", status="completed"):
    """Build one daily report item."""
    return {
        "item_id": f"item-{name}-{progress}"[:36],
        "name": name,
        "project": project,
        "progress": progress,
        "result": result,
        "status": status,
    }


# --------------------------------------------------------------------------------------
# 鉴权与隔离
# --------------------------------------------------------------------------------------
def test_requires_login_and_menu_permission(env):
    """No token is 401, a token without the menu is 403, and the owner gets 200."""
    assert env.client.get(f"{PREFIX}/entries").status_code == 401
    assert env.client.get(f"{PREFIX}/entries", headers=env.carol).status_code == 403
    assert env.client.get(f"{PREFIX}/entries", headers=env.alice).status_code == 200


def test_owner_isolation_across_every_read(env):
    """Another user must not reach the owner's entry through any endpoint."""
    made = make_entry(env, env.alice)
    assert env.client.get(f"{PREFIX}/entries/{made['id']}", headers=env.bob).status_code == 404
    assert env.client.put(
        f"{PREFIX}/entries/{made['id']}",
        json={**entry_payload(), "revision": 1},
        headers=env.bob,
    ).status_code == 404
    assert env.client.delete(f"{PREFIX}/entries/{made['id']}?revision=1", headers=env.bob).status_code == 404
    assert env.client.get(f"{PREFIX}/entries/{made['id']}/export", headers=env.bob).status_code == 404
    assert env.client.get(f"{PREFIX}/entries", headers=env.bob).json()["total"] == 0
    assert env.client.get(f"{PREFIX}/calendar?month={today_shanghai():%Y-%m}", headers=env.bob).json()["days"]


def test_admin_still_only_sees_own_records(env):
    """Administrators bypass menu checks but must not read another user's journal."""
    with env.session() as db:
        alice = db.query(AppUser).filter(AppUser.username == "alice").first()
        admin = AppUser(username="root", display_name="管理员", password_hash=hash_password("x"), is_admin=True)
        db.add(admin)
        db.commit()
        alice_id = alice.id
    make_entry(env, env.alice)
    admin_headers = {"Authorization": f"Bearer {create_access_token('root', is_admin=True)}"}
    assert env.client.get(f"{PREFIX}/entries", headers=admin_headers).json()["total"] == 0
    assert alice_id is not None


# --------------------------------------------------------------------------------------
# 日志读写
# --------------------------------------------------------------------------------------
def test_create_is_idempotent_for_repeated_request_id(env):
    """A retried create with the same client_request_id must not duplicate the row."""
    first = make_entry(env, env.alice)
    second = env.client.post(f"{PREFIX}/entries", json=entry_payload(), headers=env.alice)
    assert second.status_code == 201
    assert second.json()["id"] == first["id"]
    assert env.client.get(f"{PREFIX}/entries", headers=env.alice).json()["total"] == 1


def test_future_work_date_is_rejected(env):
    """First release does not allow future work dates."""
    tomorrow = (today_shanghai() + timedelta(days=1)).isoformat()
    response = env.client.post(f"{PREFIX}/entries", json=entry_payload(work_date=tomorrow), headers=env.alice)
    assert response.status_code == 422


def test_blank_body_and_bad_tags_are_rejected(env):
    """Whitespace-only bodies are invalid and tags are de-duplicated and capped."""
    blank = env.client.post(f"{PREFIX}/entries", json=entry_payload(body_markdown="   \n  "), headers=env.alice)
    assert blank.status_code == 422
    tagged = make_entry(
        env, env.alice, client_request_id="req-bad-tags", tags=["a", "a", " b ", ""]
    )
    assert tagged["tags"] == ["a", "b"]
    too_many = env.client.post(
        f"{PREFIX}/entries", json=entry_payload(client_request_id="req-many-tags", tags=[f"t{i}" for i in range(11)]), headers=env.alice
    )
    assert too_many.status_code == 422


def test_update_delete_and_restore_require_matching_revision(env):
    """Stale revisions conflict; deleted rows land in the recycle bin and can be restored."""
    made = make_entry(env, env.alice)
    stale = env.client.put(
        f"{PREFIX}/entries/{made['id']}", json={**entry_payload(), "revision": 99}, headers=env.alice
    )
    assert stale.status_code == 409
    updated = env.client.put(
        f"{PREFIX}/entries/{made['id']}",
        json={**entry_payload(), "title": "登录接口自动化（二）", "revision": made["revision"]},
        headers=env.alice,
    )
    assert updated.status_code == 200
    assert updated.json()["revision"] == made["revision"] + 1

    deleted = env.client.delete(f"{PREFIX}/entries/{made['id']}?revision={updated.json()['revision']}", headers=env.alice)
    assert deleted.status_code == 200
    assert env.client.get(f"{PREFIX}/entries", headers=env.alice).json()["total"] == 0
    assert env.client.get(f"{PREFIX}/entries?deleted=true", headers=env.alice).json()["total"] == 1

    restored = env.client.post(f"{PREFIX}/entries/{made['id']}/restore", headers=env.alice)
    assert restored.status_code == 200
    assert env.client.get(f"{PREFIX}/entries", headers=env.alice).json()["total"] == 1


def test_filters_run_on_the_server(env):
    """Filters and keyword search apply to the whole result set, not just one page."""
    for index in range(3):
        make_entry(
            env,
            env.alice,
            client_request_id=f"req-page-{index}",
            work_date=(today_shanghai() - timedelta(days=index)).isoformat(),
            title=f"分页用例 {index}",
            body_markdown="内容命中关键字" if index == 2 else "普通内容",
            project="霖感 APP" if index != 1 else "商城",
        )
    assert env.client.get(f"{PREFIX}/entries?project=霖感 APP", headers=env.alice).json()["total"] == 2
    assert env.client.get(f"{PREFIX}/entries?q=命中关键字", headers=env.alice).json()["total"] == 1
    assert env.client.get(f"{PREFIX}/entries?page=1&page_size=2", headers=env.alice).json()["items"].__len__() == 2
    filters = env.client.get(f"{PREFIX}/filters", headers=env.alice).json()
    assert set(filters["projects"]) == {"霖感 APP", "商城"}


# --------------------------------------------------------------------------------------
# 日报汇总
# --------------------------------------------------------------------------------------
def test_daily_assemble_maps_logs_to_the_five_sections(env):
    """Logs map to items/quality/blockers/next_plan/reflection with the real progress status."""
    today = today_shanghai()
    make_entry(
        env, env.alice, client_request_id="req-daily-1", work_date=today.isoformat(), title="回归线上版本",
        body_markdown="执行核心流程回归", category="测试执行", progress_status="completed",
        outcome_markdown="发现 2 个问题", blocker_markdown="支付回调偶发失败",
        next_step_markdown="跟进支付回调问题", duration_minutes=90,
    )
    make_entry(
        env, env.alice, client_request_id="req-daily-2", work_date=today.isoformat(), title="自动化脚本优化",
        body_markdown="重构登录态复用", category="自动化开发", progress_status="in_progress",
    )
    make_entry(
        env, env.alice, client_request_id="req-daily-3", work_date=today.isoformat(), title="学习 Pytest",
        body_markdown="学习 fixture 用法", category="学习成长", progress_status="completed",
    )
    preview = env.client.post(
        f"{PREFIX}/assemble-preview",
        json={"report_type": "daily", "period_start": today.isoformat()},
        headers=env.alice,
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    sections = body["sections"]
    assert len(sections["items"]) == 3
    statuses = {item["name"]: item["status"] for item in sections["items"]}
    assert statuses["自动化脚本优化"] == "in_progress"
    assert statuses["回归线上版本"] == "completed"
    assert "回归线上版本" in sections["quality"]
    assert sections["blockers"][0]["text"] == "支付回调偶发失败"
    assert sections["next_plan"][0]["text"] == "跟进支付回调问题"
    assert "学习 Pytest" in sections["reflection"]
    assert body["source_count"] == 3
    assert body["totals"]["duration_minutes"] == 90
    # 每条来源都要能追溯回具体日志
    assert all(item["source_refs"] for item in sections["items"])


def test_daily_assemble_with_no_logs_never_fabricates(env):
    """An empty day yields an empty candidate plus a warning, never invented content."""
    preview = env.client.post(
        f"{PREFIX}/assemble-preview",
        json={"report_type": "daily", "period_start": today_shanghai().isoformat()},
        headers=env.alice,
    ).json()
    assert preview["sections"]["items"] == []
    assert preview["source_count"] == 0
    assert preview["warnings"]


def test_daily_completion_requires_a_filled_item(env):
    """A daily report cannot be completed without a named item carrying progress."""
    created = env.client.post(
        f"{PREFIX}/reports", json={"report_type": "daily", "period_start": today_shanghai().isoformat()}, headers=env.alice
    ).json()
    blocked = env.client.post(
        f"{PREFIX}/reports/{created['id']}/complete", json={"revision": created["revision"]}, headers=env.alice
    )
    assert blocked.status_code == 422

    saved = env.client.put(
        f"{PREFIX}/reports/{created['id']}",
        json={
            "title": created["title"],
            "sections": {
                "items": [daily_item("今日主要为排查", "排查线上告警，尚无完成项", "", "", "in_progress")],
                "quality": "",
                "blockers": [],
                "next_plan": [],
                "reflection": "",
            },
            "revision": created["revision"],
        },
        headers=env.alice,
    ).json()
    done = env.client.post(f"{PREFIX}/reports/{created['id']}/complete", json={"revision": saved["revision"]}, headers=env.alice)
    assert done.status_code == 200
    assert done.json()["status"] == "completed"
    # 完成态不能直接改，必须先重新编辑
    assert env.client.put(
        f"{PREFIX}/reports/{created['id']}",
        json={"title": "改", "sections": saved["sections"], "revision": done.json()["revision"]},
        headers=env.alice,
    ).status_code == 409
    reopened = env.client.post(
        f"{PREFIX}/reports/{created['id']}/reopen", json={"revision": done.json()["revision"]}, headers=env.alice
    )
    assert reopened.json()["status"] == "draft"


def test_one_daily_report_per_day_including_recycle_bin(env):
    """A second daily report for the same day conflicts and points at the existing row."""
    day = today_shanghai().isoformat()
    first = env.client.post(f"{PREFIX}/reports", json={"report_type": "daily", "period_start": day}, headers=env.alice)
    assert first.status_code == 201
    duplicate = env.client.post(f"{PREFIX}/reports", json={"report_type": "daily", "period_start": day}, headers=env.alice)
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["report_id"] == first.json()["id"]
    # 软删除后唯一键仍然占位，因此再次创建依旧冲突，前端据此提示恢复
    env.client.delete(f"{PREFIX}/reports/{first.json()['id']}?revision=1", headers=env.alice)
    again = env.client.post(f"{PREFIX}/reports", json={"report_type": "daily", "period_start": day}, headers=env.alice)
    assert again.status_code == 409
    assert again.json()["detail"]["deleted"] is True


# --------------------------------------------------------------------------------------
# 周报汇总
# --------------------------------------------------------------------------------------
def test_weekly_merges_the_same_item_across_days(env):
    """One item logged on several days becomes a single P block with ordered, de-duplicated progress."""
    monday, _ = week_range(today_shanghai())
    monday = monday - timedelta(days=7)  # 用上一周，避免与其它用例互相影响
    for offset, (progress, result) in enumerate(
        [("调整登录态复用流程", ""), ("调整登录态复用流程", "回归待验证"), ("补充异常分支用例", "")]
    ):
        make_daily(
            env,
            env.alice,
            monday + timedelta(days=offset),
            [daily_item("UI 自动化测试优化", progress, result, "霖感 APP")],
        )
    report = env.client.post(
        f"{PREFIX}/reports", json={"report_type": "weekly", "period_start": monday.isoformat()}, headers=env.alice
    ).json()
    preview = env.client.post(
        f"{PREFIX}/assemble-preview",
        json={"report_type": "weekly", "period_start": monday.isoformat(), "report_id": report["id"]},
        headers=env.alice,
    ).json()
    p_items = [item for item in preview["sections"]["p_items"] if item["name"] == "UI 自动化测试优化"]
    assert len(p_items) == 1
    assert p_items[0]["progress"].count("调整登录态复用流程") == 1
    assert "补充异常分支用例" in p_items[0]["progress"]
    assert p_items[0]["result"] == "回归待验证"
    assert len(p_items[0]["source_item_refs"]) == 3


def test_weekly_does_not_merge_same_name_in_different_projects(env):
    """Identical names in different projects stay separate, and a missing result is flagged."""
    monday, _ = week_range(today_shanghai()) 
    monday = monday - timedelta(days=14)
    make_daily(env, env.alice, monday, [daily_item("版本巡检", "巡检 A 项目", "完成 A", "项目A")])
    make_daily(env, env.alice, monday + timedelta(days=1), [daily_item("版本巡检", "巡检 B 项目", "", "项目B")])
    preview = env.client.post(
        f"{PREFIX}/assemble-preview",
        json={"report_type": "weekly", "period_start": monday.isoformat()},
        headers=env.alice,
    ).json()
    names = [item["name"] for item in preview["sections"]["p_items"]]
    assert names.count("版本巡检") == 2
    empty_result = [item for item in preview["sections"]["p_items"] if item["project"] == "项目B"][0]
    assert "待确认" in empty_result["result"]


def test_weekly_result_conflict_and_explicit_correction(env):
    """Different results conflict unless the later daily report explicitly corrects the earlier one."""
    monday, _ = week_range(today_shanghai())
    monday = monday - timedelta(days=21)
    make_daily(env, env.alice, monday, [daily_item("缺陷跟进", "跟进失败率", "失败率 12%")])
    make_daily(env, env.alice, monday + timedelta(days=1), [daily_item("缺陷跟进", "继续跟进失败率", "失败率 8%")])
    conflict = env.client.post(
        f"{PREFIX}/assemble-preview",
        json={"report_type": "weekly", "period_start": monday.isoformat()},
        headers=env.alice,
    ).json()
    item = [row for row in conflict["sections"]["p_items"] if row["name"] == "缺陷跟进"][0]
    assert item["result_conflict"] is True
    assert "结果存在差异" in item["result"]

    monday2 = monday - timedelta(days=7)
    make_daily(env, env.alice, monday2, [daily_item("缺陷跟进", "跟进失败率", "失败率 12%")])
    make_daily(env, env.alice, monday2 + timedelta(days=1), [daily_item("缺陷跟进", "继续跟进失败率", "更正：实际失败率 8%")])
    corrected = env.client.post(
        f"{PREFIX}/assemble-preview",
        json={"report_type": "weekly", "period_start": monday2.isoformat()},
        headers=env.alice,
    ).json()
    item = [row for row in corrected["sections"]["p_items"] if row["name"] == "缺陷跟进"][0]
    assert item["result_conflict"] is False
    assert "更正" in item["result"]


def test_weekly_without_sources_reports_gaps_without_fabricating(env):
    """A week with no daily reports must not invent progress, risks or numbers."""
    monday, _ = week_range(today_shanghai())
    monday = monday - timedelta(days=28)
    preview = env.client.post(
        f"{PREFIX}/assemble-preview",
        json={"report_type": "weekly", "period_start": monday.isoformat()},
        headers=env.alice,
    ).json()
    assert preview["source_count"] == 0
    assert preview["sections"]["p_items"] == []
    assert preview["sections"]["r_items"][0]["text"] == assemble.NO_RISK_TEXT
    assert preview["sections"]["o_items"][0]["text"] == assemble.NO_PLAN_TEXT
    assert len(preview["missing_dates"]) == 7
    assert preview["warnings"]


def test_weekly_excludes_draft_reports_by_default(env):
    """Draft daily reports stay out unless explicitly selected, and the gap is disclosed."""
    monday, _ = week_range(today_shanghai())
    monday = monday - timedelta(days=35)
    make_daily(
        env, env.alice, monday, [daily_item("草稿事项", "只写了一半", "")], complete=False
    )
    default = env.client.post(
        f"{PREFIX}/assemble-preview",
        json={"report_type": "weekly", "period_start": monday.isoformat()},
        headers=env.alice,
    ).json()
    assert default["source_count"] == 0
    assert any("草稿" in warning for warning in default["warnings"])
    included = env.client.post(
        f"{PREFIX}/assemble-preview",
        json={"report_type": "weekly", "period_start": monday.isoformat(), "include_draft_reports": True},
        headers=env.alice,
    ).json()
    assert included["source_count"] == 1
    assert [row["name"] for row in included["sections"]["p_items"]] == ["草稿事项"]


def test_weekly_requires_monday_and_one_complete_item(env):
    """Weekly periods start on Monday and completion needs name + progress + result."""
    wednesday = week_range(today_shanghai())[0] + timedelta(days=2) - timedelta(days=42)
    bad = env.client.post(
        f"{PREFIX}/reports", json={"report_type": "weekly", "period_start": wednesday.isoformat()}, headers=env.alice
    )
    assert bad.status_code == 422

    monday = week_range(today_shanghai())[0] - timedelta(days=42)
    report = env.client.post(
        f"{PREFIX}/reports", json={"report_type": "weekly", "period_start": monday.isoformat()}, headers=env.alice
    ).json()
    assert report["period_end"] == (monday + timedelta(days=6)).isoformat()
    incomplete = env.client.put(
        f"{PREFIX}/reports/{report['id']}",
        json={
            "title": report["title"],
            "sections": {"p_items": [{"item_id": "1", "name": "事项", "progress": "做了", "result": ""}], "r_items": [], "o_items": []},
            "revision": report["revision"],
        },
        headers=env.alice,
    ).json()
    refused = env.client.post(
        f"{PREFIX}/reports/{report['id']}/complete", json={"revision": incomplete["revision"]}, headers=env.alice
    )
    assert refused.status_code == 422
    # 用户明确写"结果待确认"即可完成，系统不得自动填充"已完成"
    fixed = env.client.put(
        f"{PREFIX}/reports/{report['id']}",
        json={
            "title": report["title"],
            "sections": {"p_items": [{"item_id": "1", "name": "事项", "progress": "做了", "result": "结果待确认"}], "r_items": [], "o_items": []},
            "revision": incomplete["revision"],
        },
        headers=env.alice,
    ).json()
    assert env.client.post(
        f"{PREFIX}/reports/{report['id']}/complete", json={"revision": fixed["revision"]}, headers=env.alice
    ).status_code == 200


def test_assemble_endpoint_appends_then_replaces(env):
    """The assemble endpoint writes the candidate body and append mode does not duplicate sources."""
    monday, _ = week_range(today_shanghai())
    monday = monday - timedelta(days=49)
    make_daily(env, env.alice, monday, [daily_item("回归验证", "执行剩余场景", "已通过")])
    report = env.client.post(
        f"{PREFIX}/reports", json={"report_type": "weekly", "period_start": monday.isoformat()}, headers=env.alice
    ).json()
    first = env.client.post(f"{PREFIX}/reports/{report['id']}/assemble?mode=append", headers=env.alice)
    assert first.status_code == 200, first.text
    names_after_first = [row["name"] for row in first.json()["sections"]["p_items"]]
    second = env.client.post(f"{PREFIX}/reports/{report['id']}/assemble?mode=append", headers=env.alice)
    assert [row["name"] for row in second.json()["sections"]["p_items"]] == names_after_first
    replaced = env.client.post(f"{PREFIX}/reports/{report['id']}/assemble?mode=replace", headers=env.alice)
    assert [row["name"] for row in replaced.json()["sections"]["p_items"]] == names_after_first
    assert replaced.json()["source_refs"]


# --------------------------------------------------------------------------------------
# 格式与导出
# --------------------------------------------------------------------------------------
def test_weekly_body_uses_the_fixed_p_r_o_format(env):
    """The weekly body must be exactly the P / R / O blocks with 事项编号 and ● progress/result."""
    monday, _ = week_range(today_shanghai())
    monday = monday - timedelta(days=56)
    make_daily(
        env,
        env.alice,
        monday,
        [daily_item("线上版本巡检", "围绕霖感 APP 线上版本开展日常巡检", "完成本周巡检并记录问题", "霖感 APP")],
        blockers=[{"id": "b1", "item_id": "", "text": "部分场景尚未完成回归验证", "resolved": False}],
        next_plan=[{"id": "p1", "item_id": "", "text": "完成剩余场景的回归验证"}],
    )
    report = env.client.post(
        f"{PREFIX}/reports", json={"report_type": "weekly", "period_start": monday.isoformat()}, headers=env.alice
    ).json()
    env.client.post(f"{PREFIX}/reports/{report['id']}/assemble?mode=replace", headers=env.alice)
    exported = env.client.get(f"{PREFIX}/reports/{report['id']}/export", headers=env.alice)
    assert exported.status_code == 200
    text = exported.text
    assert "# P-核心进展与结果:" in text
    assert "# R-需要关注的风险与问题:" in text
    assert "# O-下周核心目标与计划:" in text
    assert "**事项一：线上版本巡检**" in text
    assert "● 进展：" in text and "● 结果：" in text
    # 正文不能夹带来源 ID、缺失日期或草稿标记
    assert "source_refs" not in text and "草稿来源" not in text
    assert exported.headers["content-disposition"].startswith("attachment; filename*=UTF-8''")


def test_entry_export_contains_the_metadata_block(env):
    """Entry export carries the title, date, type and body."""
    made = make_entry(env, env.alice, outcome_markdown="完成登录用例", duration_minutes=45)
    exported = env.client.get(f"{PREFIX}/entries/{made['id']}/export", headers=env.alice)
    assert exported.status_code == 200
    assert "# 登录接口自动化" in exported.text
    assert "工时：45 分钟" in exported.text
    assert "## 结果与产出" in exported.text


def test_weekly_index_handles_more_than_ten_items(env):
    """Item numbering must stay correct beyond ten entries."""
    from app.modules.work_journal.service import chinese_index

    assert chinese_index(1) == "一"
    assert chinese_index(10) == "十"
    assert chinese_index(11) == "11"


def test_week_range_and_today_use_beijing_time(env):
    """Week boundaries are Monday..Sunday and today comes from Asia/Shanghai."""
    monday, sunday = week_range(date(2026, 10, 14))
    assert monday == date(2026, 10, 12)
    assert sunday == date(2026, 10, 18)
    assert monday.weekday() == 0
    # 跨年周以周一日期作为周 ID，不会与其它年份冲突
    assert week_range(date(2027, 1, 1))[0] == date(2026, 12, 28)


# --------------------------------------------------------------------------------------
# 来源变更、人工修改与旧版兼容
# --------------------------------------------------------------------------------------
def test_report_keeps_its_snapshot_after_the_source_changes(env):
    """J10：改动或删除来源日志后，已保存报告的正文与来源快照都不随之改变。"""
    day = today_shanghai().isoformat()
    made = make_entry(env, env.alice, work_date=day, title="快照来源", body_markdown="原始内容", outcome_markdown="原始结果")
    report = env.client.post(
        f"{PREFIX}/reports", json={"report_type": "daily", "period_start": day}, headers=env.alice
    ).json()
    adopted = env.client.post(f"{PREFIX}/reports/{report['id']}/assemble?mode=replace", headers=env.alice).json()
    names_before = [row["name"] for row in adopted["sections"]["items"]]
    assert "快照来源" in names_before

    # 改动来源日志
    env.client.put(
        f"{PREFIX}/entries/{made['id']}",
        json={**entry_payload(work_date=day), "title": "改名后的日志", "revision": made["revision"]},
        headers=env.alice,
    )
    after = env.client.get(f"{PREFIX}/reports/{report['id']}", headers=env.alice).json()
    assert [row["name"] for row in after["sections"]["items"]] == names_before
    assert after["source_refs"][0]["title"] == "快照来源"

    # 删除来源日志后报告仍然可读
    env.client.delete(f"{PREFIX}/entries/{made['id']}?revision=2", headers=env.alice)
    still = env.client.get(f"{PREFIX}/reports/{report['id']}", headers=env.alice)
    assert still.status_code == 200
    assert "快照来源" in still.json()["source_refs"][0]["title"]


def test_resolved_blocker_leaves_the_risk_section(env):
    """J23：用户明确标记为已解决的阻碍不再出现在 R 段。"""
    monday = week_range(today_shanghai())[0] - timedelta(days=63)
    make_daily(
        env,
        env.alice,
        monday,
        [daily_item("回归验证", "执行回归", "已通过")],
        blockers=[
            {"id": "b1", "item_id": "", "text": "已经解决的阻碍", "resolved": True},
            {"id": "b2", "item_id": "", "text": "仍未解决的阻碍", "resolved": False},
        ],
    )
    preview = env.client.post(
        f"{PREFIX}/assemble-preview",
        json={"report_type": "weekly", "period_start": monday.isoformat()},
        headers=env.alice,
    ).json()
    risks = [row["text"] for row in preview["sections"]["r_items"]]
    assert "仍未解决的阻碍" in risks
    assert "已经解决的阻碍" not in risks


def test_regeneration_keeps_manual_edits_without_duplicating(env):
    """J24：重新生成更新未修改的块、保留人工修改，并且不新增重复事项。"""
    monday = week_range(today_shanghai())[0] - timedelta(days=70)
    make_daily(env, env.alice, monday, [daily_item("事项甲", "进展甲", "结果甲", "项目A")])
    make_daily(env, env.alice, monday + timedelta(days=1), [daily_item("事项乙", "进展乙", "结果乙", "项目B")])
    report = env.client.post(
        f"{PREFIX}/reports", json={"report_type": "weekly", "period_start": monday.isoformat()}, headers=env.alice
    ).json()
    first = env.client.post(f"{PREFIX}/reports/{report['id']}/assemble?mode=replace", headers=env.alice).json()
    assert len(first["sections"]["p_items"]) == 2

    # 人工修改第一条事项
    sections = first["sections"]
    sections["p_items"][0] = {**sections["p_items"][0], "name": "人工改名的事项", "manually_edited": True}
    saved = env.client.put(
        f"{PREFIX}/reports/{report['id']}",
        json={"title": first["title"], "sections": sections, "revision": first["revision"]},
        headers=env.alice,
    ).json()

    again = env.client.post(f"{PREFIX}/reports/{report['id']}/assemble?mode=replace", headers=env.alice).json()
    names = [row["name"] for row in again["sections"]["p_items"]]
    assert "人工改名的事项" in names, names
    assert names.count("人工改名的事项") == 1
    assert len(again["sections"]["p_items"]) == 2
    assert saved["revision"] < again["revision"]


def test_legacy_report_body_stays_readable(env):
    """J26：旧版五段报告原文可读，且不会因新校验而被拒绝保存。"""
    with env.session() as db:
        alice = db.query(AppUser).filter(AppUser.username == "alice").first()
        legacy = WorkJournalReport(
            owner_user_id=alice.id, report_type="weekly",
            period_start=date(2026, 1, 5), period_end=date(2026, 1, 11),
            title="旧版周报", template_version="weekly_legacy_v1",
            sections={"body": "旧版五段正文内容"}, status="draft", source_refs=[], revision=1,
        )
        db.add(legacy)
        db.commit()
        legacy_id = legacy.id

    exported = env.client.get(f"{PREFIX}/reports/{legacy_id}/export", headers=env.alice)
    assert exported.status_code == 200
    assert "旧版五段正文内容" in exported.text

    # 旧版结构保存时不套用新模板校验
    current = env.client.get(f"{PREFIX}/reports/{legacy_id}", headers=env.alice).json()
    saved = env.client.put(
        f"{PREFIX}/reports/{legacy_id}",
        json={"title": current["title"], "sections": {"body": "旧版五段正文内容（已补充）"}, "revision": current["revision"]},
        headers=env.alice,
    )
    assert saved.status_code == 200
    assert "已补充" in env.client.get(f"{PREFIX}/reports/{legacy_id}/export", headers=env.alice).text


def test_weekly_copy_body_excludes_platform_meta(env):
    """J25：复制用的正文只有 P/R/O 三段，不含标题、作者、周期等平台信息。"""
    monday = week_range(today_shanghai())[0] - timedelta(days=77)
    make_daily(env, env.alice, monday, [daily_item("复制验证", "进展", "结果", "项目")])
    report = env.client.post(
        f"{PREFIX}/reports", json={"report_type": "weekly", "period_start": monday.isoformat()}, headers=env.alice
    ).json()
    env.client.post(f"{PREFIX}/reports/{report['id']}/assemble?mode=replace", headers=env.alice)
    body = env.client.get(f"{PREFIX}/reports/{report['id']}/export?body_only=true", headers=env.alice).text
    assert body.startswith("# P-核心进展与结果:")
    assert "- 周期：" not in body
    assert "- 作者：" not in body
    assert "复制验证" in body
