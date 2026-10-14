"""Tests for the work journal module (二期：事项内容 / 状态 / 进度百分比).

这些测试走完整的 HTTP 与鉴权链路（真实 JWT -> get_current_user -> require_menu -> 数据库持久化），
不通过直接调用内部函数绕过权限。
"""

import uuid
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
    return SimpleNamespace(
        client=TestClient(app),
        session=TestingSession,
        alice={"Authorization": f"Bearer {create_access_token('alice')}"},
        bob={"Authorization": f"Bearer {create_access_token('bob')}"},
        carol={"Authorization": f"Bearer {create_access_token('carol')}"},
    )


def entry_payload(**overrides):
    """Build a valid log payload with sane defaults."""
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
    """Create one log through the API and return its JSON body."""
    response = env.client.post(f"{PREFIX}/entries", json=entry_payload(**overrides), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def daily_item(content, status="in_progress", percent=0):
    """Build one 二期 daily item: content / status / progress_percent."""
    return {"item_id": str(uuid.uuid4()), "content": content, "status": status, "progress_percent": percent}


def make_daily(env, headers, day, items, *, remarks="", blockers=None, next_plan=None, complete=True):
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
        "blockers": blockers or [],
        "next_plan": next_plan or [],
        "remarks": remarks,
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


def _legacy_report(env, report_type, period_start, body):
    """Insert one pre-P/R/O report directly so the conversion path can be exercised."""
    with env.session() as db:
        alice = db.query(AppUser).filter(AppUser.username == "alice").first()
        row = WorkJournalReport(
            owner_user_id=alice.id, report_type=report_type,
            period_start=period_start, period_end=period_start if report_type == "daily" else period_start + timedelta(days=6),
            title=f"旧版{report_type}", template_version=f"{report_type}_legacy_v1",
            sections={"body": body}, status="draft", source_refs=[], revision=1,
        )
        db.add(row)
        db.commit()
        return row.id


def _v1_report(env, report_type, period_start, sections):
    """Insert one 一期 structured report so the v1 -> v2 conversion path can be exercised."""
    with env.session() as db:
        alice = db.query(AppUser).filter(AppUser.username == "alice").first()
        row = WorkJournalReport(
            owner_user_id=alice.id, report_type=report_type,
            period_start=period_start, period_end=period_start if report_type == "daily" else period_start + timedelta(days=6),
            title=f"一期{report_type}", template_version="daily_v1" if report_type == "daily" else "weekly_pro_v1",
            sections=sections, status="draft", source_refs=[], revision=1,
        )
        db.add(row)
        db.commit()
        return row.id


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
        f"{PREFIX}/entries/{made['id']}", json={**entry_payload(), "revision": 1}, headers=env.bob
    ).status_code == 404
    assert env.client.delete(f"{PREFIX}/entries/{made['id']}?revision=1", headers=env.bob).status_code == 404
    assert env.client.get(f"{PREFIX}/entries/{made['id']}/export", headers=env.bob).status_code == 404
    assert env.client.get(f"{PREFIX}/entries", headers=env.bob).json()["total"] == 0
    assert env.client.get(f"{PREFIX}/calendar?month={today_shanghai():%Y-%m}", headers=env.bob).json()["days"]


def test_admin_still_only_sees_own_records(env):
    """Administrators bypass menu checks but must not read another user's journal."""
    with env.session() as db:
        db.add(AppUser(username="root", display_name="管理员", password_hash=hash_password("x"), is_admin=True))
        db.commit()
    make_entry(env, env.alice)
    admin_headers = {"Authorization": f"Bearer {create_access_token('root', is_admin=True)}"}
    assert env.client.get(f"{PREFIX}/entries", headers=admin_headers).json()["total"] == 0


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
    assert env.client.post(f"{PREFIX}/entries", json=entry_payload(work_date=tomorrow), headers=env.alice).status_code == 422


def test_blank_body_and_bad_tags_are_rejected(env):
    """Whitespace-only bodies are invalid and tags are de-duplicated and capped."""
    assert env.client.post(f"{PREFIX}/entries", json=entry_payload(body_markdown="   \n  "), headers=env.alice).status_code == 422
    tagged = make_entry(env, env.alice, client_request_id="req-bad-tags", tags=["a", "a", " b ", ""])
    assert tagged["tags"] == ["a", "b"]
    too_many = env.client.post(
        f"{PREFIX}/entries", json=entry_payload(client_request_id="req-many-tags", tags=[f"t{i}" for i in range(11)]), headers=env.alice
    )
    assert too_many.status_code == 422


def test_entry_remarks_round_trip(env):
    """日志备注可保存、返回与导出；留空时导出不出现备注区块。"""
    with_remarks = make_entry(env, env.alice, client_request_id="req-remarks-1", remarks_markdown="补充背景与链接")
    assert with_remarks["remarks_markdown"] == "补充背景与链接"
    exported = env.client.get(f"{PREFIX}/entries/{with_remarks['id']}/export", headers=env.alice).text
    assert "## 备注" in exported and "补充背景与链接" in exported

    without = make_entry(env, env.alice, client_request_id="req-remarks-2", title="无备注日志")
    assert without["remarks_markdown"] in (None, "")
    assert "## 备注" not in env.client.get(f"{PREFIX}/entries/{without['id']}/export", headers=env.alice).text


def test_update_delete_and_restore_require_matching_revision(env):
    """Stale revisions conflict; deleted rows land in the recycle bin and can be restored."""
    made = make_entry(env, env.alice)
    assert env.client.put(
        f"{PREFIX}/entries/{made['id']}", json={**entry_payload(), "revision": 99}, headers=env.alice
    ).status_code == 409
    updated = env.client.put(
        f"{PREFIX}/entries/{made['id']}",
        json={**entry_payload(), "title": "登录接口自动化（二）", "revision": made["revision"]},
        headers=env.alice,
    )
    assert updated.status_code == 200
    assert updated.json()["revision"] == made["revision"] + 1

    assert env.client.delete(f"{PREFIX}/entries/{made['id']}?revision={updated.json()['revision']}", headers=env.alice).status_code == 200
    assert env.client.get(f"{PREFIX}/entries", headers=env.alice).json()["total"] == 0
    assert env.client.get(f"{PREFIX}/entries?deleted=true", headers=env.alice).json()["total"] == 1
    assert env.client.post(f"{PREFIX}/entries/{made['id']}/restore", headers=env.alice).status_code == 200
    assert env.client.get(f"{PREFIX}/entries", headers=env.alice).json()["total"] == 1


def test_filters_run_on_the_server(env):
    """Filters and keyword search apply to the whole result set, not just one page."""
    for index in range(3):
        make_entry(
            env, env.alice, client_request_id=f"req-page-{index}",
            work_date=(today_shanghai() - timedelta(days=index)).isoformat(),
            title=f"分页用例 {index}",
            body_markdown="内容命中关键字" if index == 2 else "普通内容",
            project="霖感 APP" if index != 1 else "商城",
        )
    assert env.client.get(f"{PREFIX}/entries?project=霖感 APP", headers=env.alice).json()["total"] == 2
    assert env.client.get(f"{PREFIX}/entries?q=命中关键字", headers=env.alice).json()["total"] == 1
    assert len(env.client.get(f"{PREFIX}/entries?page=1&page_size=2", headers=env.alice).json()["items"]) == 2
    assert set(env.client.get(f"{PREFIX}/filters", headers=env.alice).json()["projects"]) == {"霖感 APP", "商城"}


# --------------------------------------------------------------------------------------
# 日报（二期结构）
# --------------------------------------------------------------------------------------
def test_daily_assemble_uses_content_status_and_progress(env):
    """J06：日志按新结构整理，状态真实，不再出现测试与质量 / 成长与复盘。"""
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
    preview = env.client.post(
        f"{PREFIX}/assemble-preview",
        json={"report_type": "daily", "period_start": today.isoformat()},
        headers=env.alice,
    ).json()
    sections = preview["sections"]
    assert preview["template_version"] == "daily_v2"
    assert "quality" not in sections and "reflection" not in sections
    assert len(sections["items"]) == 2
    by_content = {item["content"].splitlines()[0]: item for item in sections["items"]}
    assert by_content["回归线上版本"]["status"] == "completed"
    assert by_content["回归线上版本"]["progress_percent"] == 100
    assert by_content["自动化脚本优化"]["status"] == "in_progress"
    assert by_content["自动化脚本优化"]["progress_percent"] == 0
    assert sections["blockers"][0]["text"] == "支付回调偶发失败"
    assert sections["next_plan"][0]["text"] == "跟进支付回调问题"
    assert sections["remarks"] == ""
    assert preview["totals"]["duration_minutes"] == 90


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


def test_daily_completion_needs_one_valid_item_and_allows_empty_remarks(env):
    """验收4：至少一个有效事项即可完成，空备注可正常保存与完成。"""
    day = today_shanghai().isoformat()
    created = env.client.post(f"{PREFIX}/reports", json={"report_type": "daily", "period_start": day}, headers=env.alice).json()
    saved = env.client.put(
        f"{PREFIX}/reports/{created['id']}",
        json={"title": created["title"], "sections": {"items": [{"item_id": str(uuid.uuid4()), "content": "写了一半", "status": "in_progress", "progress_percent": None}], "blockers": [], "next_plan": [], "remarks": ""}, "revision": created["revision"]},
        headers=env.alice,
    ).json()
    refused = env.client.post(f"{PREFIX}/reports/{created['id']}/complete", json={"revision": saved["revision"]}, headers=env.alice)
    assert refused.status_code == 422
    assert "进度" in refused.json()["detail"]

    fixed = env.client.put(
        f"{PREFIX}/reports/{created['id']}",
        json={"title": created["title"], "sections": {"items": [daily_item("优化发帖自动化流程", "in_progress", 60)], "blockers": [], "next_plan": [], "remarks": ""}, "revision": saved["revision"]},
        headers=env.alice,
    ).json()
    done = env.client.post(f"{PREFIX}/reports/{created['id']}/complete", json={"revision": fixed["revision"]}, headers=env.alice)
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "completed"


def test_empty_item_and_missing_items_are_reported(env):
    """空内容卡片被拒绝，没有任何事项时也不能完成。"""
    day = today_shanghai().isoformat()
    created = env.client.post(f"{PREFIX}/reports", json={"report_type": "daily", "period_start": day}, headers=env.alice).json()
    blank = env.client.put(
        f"{PREFIX}/reports/{created['id']}",
        json={"title": created["title"], "sections": {"items": [{"item_id": str(uuid.uuid4()), "content": "   ", "status": "in_progress", "progress_percent": 0}], "blockers": [], "next_plan": [], "remarks": ""}, "revision": created["revision"]},
        headers=env.alice,
    )
    assert blank.status_code == 422
    empty = env.client.post(f"{PREFIX}/reports/{created['id']}/complete", json={"revision": created["revision"]}, headers=env.alice)
    assert empty.status_code == 422
    assert "事项" in empty.json()["detail"]


def test_progress_type_and_range_are_enforced_server_side(env):
    """验收3：字符串、布尔、负数、超过 100、非 10 的倍数一律拒绝；0 正常保存。"""
    day = today_shanghai().isoformat()
    created = env.client.post(f"{PREFIX}/reports", json={"report_type": "daily", "period_start": day}, headers=env.alice).json()
    for bad in ("60", True, -10, 110, 65):
        response = env.client.put(
            f"{PREFIX}/reports/{created['id']}",
            json={"title": created["title"], "sections": {"items": [{"item_id": str(uuid.uuid4()), "content": "事项", "status": "in_progress", "progress_percent": bad}], "blockers": [], "next_plan": [], "remarks": ""}, "revision": created["revision"]},
            headers=env.alice,
        )
        assert response.status_code == 422, (bad, response.text)

    ok = env.client.put(
        f"{PREFIX}/reports/{created['id']}",
        json={"title": created["title"], "sections": {"items": [daily_item("刚开始排查", "in_progress", 0)], "blockers": [], "next_plan": [], "remarks": ""}, "revision": created["revision"]},
        headers=env.alice,
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["sections"]["items"][0]["progress_percent"] == 0


def test_status_and_percentage_must_stay_consistent(env):
    """验收3：已完成必须是 100%，100% 必须对应已完成，其余状态只允许 0–90%。"""
    day = today_shanghai().isoformat()
    created = env.client.post(f"{PREFIX}/reports", json={"report_type": "daily", "period_start": day}, headers=env.alice).json()
    assert env.client.put(
        f"{PREFIX}/reports/{created['id']}",
        json={"title": created["title"], "sections": {"items": [daily_item("事项", "completed", 60)], "blockers": [], "next_plan": [], "remarks": ""}, "revision": created["revision"]},
        headers=env.alice,
    ).status_code == 422
    assert env.client.put(
        f"{PREFIX}/reports/{created['id']}",
        json={"title": created["title"], "sections": {"items": [daily_item("事项", "blocked", 100)], "blockers": [], "next_plan": [], "remarks": ""}, "revision": created["revision"]},
        headers=env.alice,
    ).status_code == 422
    assert env.client.put(
        f"{PREFIX}/reports/{created['id']}",
        json={"title": created["title"], "sections": {"items": [daily_item("事项", "blocked", 60)], "blockers": [], "next_plan": [], "remarks": ""}, "revision": created["revision"]},
        headers=env.alice,
    ).status_code == 200


def test_one_daily_report_per_day_including_recycle_bin(env):
    """A second daily report for the same day conflicts and points at the existing row."""
    day = today_shanghai().isoformat()
    first = env.client.post(f"{PREFIX}/reports", json={"report_type": "daily", "period_start": day}, headers=env.alice)
    assert first.status_code == 201
    duplicate = env.client.post(f"{PREFIX}/reports", json={"report_type": "daily", "period_start": day}, headers=env.alice)
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["report_id"] == first.json()["id"]
    env.client.delete(f"{PREFIX}/reports/{first.json()['id']}?revision=1", headers=env.alice)
    again = env.client.post(f"{PREFIX}/reports", json={"report_type": "daily", "period_start": day}, headers=env.alice)
    assert again.status_code == 409
    assert again.json()["detail"]["deleted"] is True


# --------------------------------------------------------------------------------------
# 周报（P / R / O）
# --------------------------------------------------------------------------------------
def test_weekly_merges_the_same_item_and_uses_the_latest_status(env):
    """验收6：同事项跨天归并，状态与进度取时间最晚的明确记录，不取最大值。"""
    monday = week_range(today_shanghai())[0] - timedelta(days=7)
    make_daily(env, env.alice, monday, [daily_item("UI 自动化测试优化", "in_progress", 80)])
    make_daily(env, env.alice, monday + timedelta(days=2), [daily_item("UI 自动化测试优化", "blocked", 60)])
    preview = env.client.post(
        f"{PREFIX}/assemble-preview",
        json={"report_type": "weekly", "period_start": monday.isoformat()},
        headers=env.alice,
    ).json()
    assert preview["template_version"] == "weekly_pro_v2"
    items = [row for row in preview["sections"]["p_items"] if row["content"] == "UI 自动化测试优化"]
    assert len(items) == 1
    assert items[0]["status"] == "blocked"
    assert items[0]["progress_percent"] == 60
    assert len(items[0]["source_item_refs"]) == 2


def test_weekly_same_day_conflict_is_flagged(env):
    """同日出现互相冲突的状态/进度时标记待核对。"""
    monday = week_range(today_shanghai())[0] - timedelta(days=14)
    make_daily(env, env.alice, monday, [
        daily_item("同名事项", "in_progress", 30),
        daily_item("同名事项", "blocked", 70),
    ])
    preview = env.client.post(
        f"{PREFIX}/assemble-preview",
        json={"report_type": "weekly", "period_start": monday.isoformat()},
        headers=env.alice,
    ).json()
    items = [row for row in preview["sections"]["p_items"] if row["content"] == "同名事项"]
    assert len(items) == 1
    assert items[0]["status_conflict"] is True


def test_weekly_keeps_different_descriptions_apart(env):
    """没有项目字段后按去空格后的相同内容匹配，不同描述不模糊合并。"""
    monday = week_range(today_shanghai())[0] - timedelta(days=21)
    make_daily(env, env.alice, monday, [daily_item("版本巡检（A 项目）", "completed", 100)])
    make_daily(env, env.alice, monday + timedelta(days=1), [daily_item("版本巡检（B 项目）", "in_progress", 20)])
    preview = env.client.post(
        f"{PREFIX}/assemble-preview",
        json={"report_type": "weekly", "period_start": monday.isoformat()},
        headers=env.alice,
    ).json()
    assert sorted(row["content"] for row in preview["sections"]["p_items"]) == ["版本巡检（A 项目）", "版本巡检（B 项目）"]


def test_weekly_without_sources_reports_gaps_without_fabricating(env):
    """A week with no daily reports must not invent progress, risks or numbers."""
    monday = week_range(today_shanghai())[0] - timedelta(days=28)
    preview = env.client.post(
        f"{PREFIX}/assemble-preview",
        json={"report_type": "weekly", "period_start": monday.isoformat()},
        headers=env.alice,
    ).json()
    assert preview["source_count"] == 0
    assert preview["sections"]["p_items"] == []
    assert preview["sections"]["r_items"][0]["text"] == assemble.NO_RISK_TEXT
    assert preview["sections"]["o_items"][0]["text"] == assemble.NO_PLAN_TEXT
    assert preview["sections"]["remarks"] == ""
    assert len(preview["missing_dates"]) == 7


def test_weekly_excludes_draft_reports_by_default(env):
    """Draft daily reports stay out unless explicitly selected."""
    monday = week_range(today_shanghai())[0] - timedelta(days=35)
    make_daily(env, env.alice, monday, [daily_item("草稿事项", "in_progress", 40)], complete=False)
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
    assert [row["content"] for row in included["sections"]["p_items"]] == ["草稿事项"]


def test_weekly_requires_monday_and_one_valid_item(env):
    """验收7：周报周期必须是周一；完成需要事项内容 + 状态 + 进度。"""
    wednesday = week_range(today_shanghai())[0] + timedelta(days=2) - timedelta(days=42)
    assert env.client.post(
        f"{PREFIX}/reports", json={"report_type": "weekly", "period_start": wednesday.isoformat()}, headers=env.alice
    ).status_code == 422

    monday = week_range(today_shanghai())[0] - timedelta(days=42)
    report = env.client.post(
        f"{PREFIX}/reports", json={"report_type": "weekly", "period_start": monday.isoformat()}, headers=env.alice
    ).json()
    assert report["period_end"] == (monday + timedelta(days=6)).isoformat()
    assert env.client.post(f"{PREFIX}/reports/{report['id']}/complete", json={"revision": report["revision"]}, headers=env.alice).status_code == 422

    fixed = env.client.put(
        f"{PREFIX}/reports/{report['id']}",
        json={"title": report["title"], "sections": {"p_items": [daily_item("输出调研报告", "completed", 100)], "r_items": [], "o_items": [], "remarks": ""}, "revision": report["revision"]},
        headers=env.alice,
    ).json()
    assert env.client.post(f"{PREFIX}/reports/{report['id']}/complete", json={"revision": fixed["revision"]}, headers=env.alice).status_code == 200


def test_assemble_endpoint_appends_then_replaces(env):
    """The assemble endpoint writes the candidate body and append mode does not duplicate items."""
    monday = week_range(today_shanghai())[0] - timedelta(days=49)
    make_daily(env, env.alice, monday, [daily_item("回归验证", "completed", 100)])
    report = env.client.post(
        f"{PREFIX}/reports", json={"report_type": "weekly", "period_start": monday.isoformat()}, headers=env.alice
    ).json()
    first = env.client.post(f"{PREFIX}/reports/{report['id']}/assemble?mode=append", headers=env.alice)
    assert first.status_code == 200, first.text
    contents = [row["content"] for row in first.json()["sections"]["p_items"]]
    second = env.client.post(f"{PREFIX}/reports/{report['id']}/assemble?mode=append", headers=env.alice)
    assert [row["content"] for row in second.json()["sections"]["p_items"]] == contents
    replaced = env.client.post(f"{PREFIX}/reports/{report['id']}/assemble?mode=replace", headers=env.alice)
    assert [row["content"] for row in replaced.json()["sections"]["p_items"]] == contents


def test_report_keeps_its_snapshot_after_the_source_changes(env):
    """J10：改动来源日志后，已保存报告的正文与来源快照都不随之改变。"""
    day = today_shanghai().isoformat()
    made = make_entry(env, env.alice, work_date=day, title="快照来源", body_markdown="原始内容")
    report = env.client.post(f"{PREFIX}/reports", json={"report_type": "daily", "period_start": day}, headers=env.alice).json()
    adopted = env.client.post(f"{PREFIX}/reports/{report['id']}/assemble?mode=replace", headers=env.alice).json()
    contents = [row["content"] for row in adopted["sections"]["items"]]
    assert any("快照来源" in text for text in contents)

    env.client.put(
        f"{PREFIX}/entries/{made['id']}",
        json={**entry_payload(work_date=day), "title": "改名后的日志", "revision": made["revision"]},
        headers=env.alice,
    )
    after = env.client.get(f"{PREFIX}/reports/{report['id']}", headers=env.alice).json()
    assert [row["content"] for row in after["sections"]["items"]] == contents
    assert after["source_refs"][0]["title"] == "快照来源"


def test_resolved_blocker_leaves_the_risk_section(env):
    """J23：用户明确标记为已解决的阻碍不再出现在 R 段。"""
    monday = week_range(today_shanghai())[0] - timedelta(days=63)
    make_daily(
        env, env.alice, monday, [daily_item("回归验证", "completed", 100)],
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
    make_daily(env, env.alice, monday, [daily_item("事项甲", "in_progress", 30)])
    make_daily(env, env.alice, monday + timedelta(days=1), [daily_item("事项乙", "completed", 100)])
    report = env.client.post(
        f"{PREFIX}/reports", json={"report_type": "weekly", "period_start": monday.isoformat()}, headers=env.alice
    ).json()
    first = env.client.post(f"{PREFIX}/reports/{report['id']}/assemble?mode=replace", headers=env.alice).json()
    assert len(first["sections"]["p_items"]) == 2

    sections = first["sections"]
    sections["p_items"][0] = {**sections["p_items"][0], "content": "人工改名的事项", "manually_edited": True}
    saved = env.client.put(
        f"{PREFIX}/reports/{report['id']}",
        json={"title": first["title"], "sections": sections, "revision": first["revision"]},
        headers=env.alice,
    ).json()

    again = env.client.post(f"{PREFIX}/reports/{report['id']}/assemble?mode=replace", headers=env.alice).json()
    contents = [row["content"] for row in again["sections"]["p_items"]]
    assert contents.count("人工改名的事项") == 1
    assert len(contents) == 2
    assert saved["revision"] < again["revision"]


# --------------------------------------------------------------------------------------
# 格式、导出与备注
# --------------------------------------------------------------------------------------
def test_weekly_body_uses_the_fixed_p_r_o_format(env):
    """验收2/7：正文严格 P/R/O，进展含内容与状态进度，结果由规则推导。"""
    monday = week_range(today_shanghai())[0] - timedelta(days=56)
    make_daily(
        env, env.alice, monday,
        [daily_item("优化 UI 自动化登录态复用与发帖流程", "in_progress", 60)],
        blockers=[{"id": "b1", "item_id": "", "text": "发帖流程仍需完成剩余回归验证。", "resolved": False}],
        next_plan=[{"id": "p1", "item_id": "", "text": "完成发帖流程剩余场景的回归验证。"}],
    )
    report = env.client.post(
        f"{PREFIX}/reports", json={"report_type": "weekly", "period_start": monday.isoformat()}, headers=env.alice
    ).json()
    env.client.post(f"{PREFIX}/reports/{report['id']}/assemble?mode=replace", headers=env.alice)
    text = env.client.get(f"{PREFIX}/reports/{report['id']}/export", headers=env.alice).text
    assert "# P-核心进展与结果:" in text
    assert "# R-需要关注的风险与问题:" in text
    assert "# O-下周核心目标与计划:" in text
    assert "**事项一：优化 UI 自动化登录态复用与发帖流程**" in text
    assert "● 进展：优化 UI 自动化登录态复用与发帖流程，目前进行中，进度60%。" in text
    assert "● 结果：该事项尚未完成，当前进度60%。" in text
    assert "发帖流程仍需完成剩余回归验证。" in text
    assert "测试与质量" not in text and "成长与复盘" not in text
    assert "source_refs" not in text and "草稿来源" not in text


def test_blocked_and_completed_result_sentences(env):
    """受阻与已完成各自生成结果句，不从百分比臆断测试通过结论。"""
    monday = week_range(today_shanghai())[0] - timedelta(days=98)
    make_daily(env, env.alice, monday, [
        daily_item("受阻事项", "blocked", 40),
        daily_item("完成事项", "completed", 100),
    ])
    report = env.client.post(
        f"{PREFIX}/reports", json={"report_type": "weekly", "period_start": monday.isoformat()}, headers=env.alice
    ).json()
    env.client.post(f"{PREFIX}/reports/{report['id']}/assemble?mode=replace", headers=env.alice)
    text = env.client.get(f"{PREFIX}/reports/{report['id']}/export", headers=env.alice).text
    assert "● 结果：该事项受阻，当前进度40%。" in text
    assert "● 结果：该事项已完成，进度100%。" in text
    for forbidden in ("测试通过", "缺陷已修复", "线上稳定", "效率提升"):
        assert forbidden not in text


def test_remarks_appear_after_the_plan_and_stay_empty_when_unset(env):
    """验收5：备注跟在 O 区之后，不新增一级标题；留空则完全不出现在导出里。"""
    monday = week_range(today_shanghai())[0] - timedelta(days=105)
    make_daily(env, env.alice, monday, [daily_item("事项", "in_progress", 20)])
    report = env.client.post(
        f"{PREFIX}/reports", json={"report_type": "weekly", "period_start": monday.isoformat()}, headers=env.alice
    ).json()
    env.client.post(f"{PREFIX}/reports/{report['id']}/assemble?mode=replace", headers=env.alice)
    assert "备注" not in env.client.get(f"{PREFIX}/reports/{report['id']}/export", headers=env.alice).text

    current = env.client.get(f"{PREFIX}/reports/{report['id']}", headers=env.alice).json()
    sections = dict(current["sections"])
    sections["remarks"] = "补充说明与背景链接"
    saved = env.client.put(
        f"{PREFIX}/reports/{report['id']}",
        json={"title": current["title"], "sections": sections, "revision": current["revision"]},
        headers=env.alice,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["sections"]["remarks"] == "补充说明与背景链接"
    with_remarks = env.client.get(f"{PREFIX}/reports/{report['id']}/export", headers=env.alice).text
    assert with_remarks.rstrip().endswith("**备注：** 补充说明与背景链接")
    # 正文只有 P / R / O 三个一级标题，备注不新增第四个
    assert with_remarks.count("# P-核心进展与结果:") == 1
    assert with_remarks.count("# R-需要关注的风险与问题:") == 1
    assert with_remarks.count("# O-下周核心目标与计划:") == 1


def test_weekly_copy_body_excludes_platform_meta(env):
    """J25：复制用的正文只有 P/R/O，不含标题、作者、周期等平台信息。"""
    monday = week_range(today_shanghai())[0] - timedelta(days=77)
    make_daily(env, env.alice, monday, [daily_item("复制验证", "in_progress", 10)])
    report = env.client.post(
        f"{PREFIX}/reports", json={"report_type": "weekly", "period_start": monday.isoformat()}, headers=env.alice
    ).json()
    env.client.post(f"{PREFIX}/reports/{report['id']}/assemble?mode=replace", headers=env.alice)
    body = env.client.get(f"{PREFIX}/reports/{report['id']}/export?body_only=true", headers=env.alice).text
    assert body.startswith("# P-核心进展与结果:")
    assert "- 周期：" not in body and "- 作者：" not in body
    assert "复制验证" in body


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
    assert week_range(date(2027, 1, 1))[0] == date(2026, 12, 28)


# --------------------------------------------------------------------------------------
# 历史兼容与转换
# --------------------------------------------------------------------------------------
def test_legacy_report_body_stays_readable(env):
    """验收8：旧版纯文本报告原文可读，且不会被新校验拒绝。"""
    legacy_id = _legacy_report(env, "weekly", date(2026, 1, 5), "旧版五段正文内容")
    exported = env.client.get(f"{PREFIX}/reports/{legacy_id}/export", headers=env.alice)
    assert exported.status_code == 200
    assert "旧版五段正文内容" in exported.text

    current = env.client.get(f"{PREFIX}/reports/{legacy_id}", headers=env.alice).json()
    saved = env.client.put(
        f"{PREFIX}/reports/{legacy_id}",
        json={"title": current["title"], "sections": {"body": "旧版五段正文内容（已补充）"}, "revision": current["revision"]},
        headers=env.alice,
    )
    assert saved.status_code == 200
    assert "已补充" in env.client.get(f"{PREFIX}/reports/{legacy_id}/export", headers=env.alice).text


def test_legacy_weekly_can_be_converted_without_losing_the_original(env):
    """验收8：旧版周报可主动转换，原文保留在 legacy_body，不被静默覆盖。"""
    monday = week_range(today_shanghai())[0] - timedelta(days=84)
    make_daily(env, env.alice, monday, [daily_item("转换来源事项", "completed", 100)])
    legacy_id = _legacy_report(env, "weekly", monday, "旧版五段原文")

    preview = env.client.post(
        f"{PREFIX}/assemble-preview",
        json={"report_type": "weekly", "period_start": monday.isoformat(), "report_id": legacy_id},
        headers=env.alice,
    ).json()
    assert preview["sections"]["legacy_body"] == "旧版五段原文"
    assert any("旧版" in warning for warning in preview["warnings"])

    adopted = env.client.post(f"{PREFIX}/reports/{legacy_id}/assemble?mode=replace", headers=env.alice).json()
    assert adopted["template_version"] == "weekly_pro_v2"
    assert adopted["sections"]["legacy_body"] == "旧版五段原文"
    assert [row["content"] for row in adopted["sections"]["p_items"]] == ["转换来源事项"]


def test_legacy_conversion_append_keeps_the_original_too(env):
    """追加模式同样不能丢掉旧版原文，且模板一并升级。"""
    monday = week_range(today_shanghai())[0] - timedelta(days=91)
    legacy_id = _legacy_report(env, "weekly", monday, "追加模式旧版原文")
    adopted = env.client.post(f"{PREFIX}/reports/{legacy_id}/assemble?mode=append", headers=env.alice).json()
    assert adopted["sections"]["legacy_body"] == "追加模式旧版原文"
    assert adopted["sections"]["body"] == "追加模式旧版原文"
    assert adopted["template_version"] == "weekly_pro_v2"


def test_legacy_daily_gets_an_editable_candidate(env):
    """旧版日报按标题给出候选，不靠正则武断拆分，也不猜百分比。"""
    day = today_shanghai() - timedelta(days=3)
    legacy_id = _legacy_report(env, "daily", day, "旧版日报正文，无法可靠拆分")
    preview = env.client.post(
        f"{PREFIX}/assemble-preview",
        json={"report_type": "daily", "period_start": day.isoformat(), "report_id": legacy_id},
        headers=env.alice,
    ).json()
    items = preview["sections"]["items"]
    assert len(items) == 1
    assert items[0]["content"] == "旧版daily"
    assert items[0]["progress_percent"] is None
    assert any("结构化事项" in warning for warning in preview["warnings"])


def test_v1_daily_converts_to_v2_and_keeps_the_removed_sections(env):
    """验收8：一期日报转二期合成 content、保留 item_id，被移除的区域收进历史补充内容。"""
    day = today_shanghai() - timedelta(days=5)
    item_id = str(uuid.uuid4())
    v1_id = _v1_report(env, "daily", day, {
        "items": [{"item_id": item_id, "name": "优化发帖流程", "project": "霖感 APP",
                   "progress": "调整登录态复用", "result": "改造完成，回归待验证", "status": "completed"}],
        "quality": "覆盖发帖主流程",
        "blockers": [],
        "next_plan": [],
        "reflection": "熟悉了状态复用",
    })
    preview = env.client.post(
        f"{PREFIX}/assemble-preview",
        json={"report_type": "daily", "period_start": day.isoformat(), "report_id": v1_id},
        headers=env.alice,
    ).json()
    items = preview["sections"]["items"]
    assert items[0]["item_id"] == item_id
    assert items[0]["content"] == "优化发帖流程：调整登录态复用"
    assert items[0]["status"] == "completed"
    assert items[0]["progress_percent"] == 100

    supplement = preview["sections"]["legacy_supplement"]
    assert supplement["quality"] == "覆盖发帖主流程"
    assert supplement["reflection"] == "熟悉了状态复用"
    assert supplement["results"][0]["result"] == "改造完成，回归待验证"

    adopted = env.client.post(f"{PREFIX}/reports/{v1_id}/assemble?mode=replace", headers=env.alice).json()
    assert adopted["template_version"] == "daily_v2"
    assert adopted["sections"]["legacy_supplement"]["quality"] == "覆盖发帖主流程"


def test_v1_in_progress_item_converts_without_guessing_progress(env):
    """验收8：一期进行中事项的百分比未知，转换后保持空，完成前必须选择。"""
    day = today_shanghai() - timedelta(days=6)
    v1_id = _v1_report(env, "daily", day, {
        "items": [{"item_id": str(uuid.uuid4()), "name": "排查告警", "progress": "定位中", "result": "", "status": "in_progress"}],
        "quality": "", "blockers": [], "next_plan": [], "reflection": "",
    })
    preview = env.client.post(
        f"{PREFIX}/assemble-preview",
        json={"report_type": "daily", "period_start": day.isoformat(), "report_id": v1_id},
        headers=env.alice,
    ).json()
    assert preview["sections"]["items"][0]["progress_percent"] is None
    adopted = env.client.post(f"{PREFIX}/reports/{v1_id}/assemble?mode=replace", headers=env.alice).json()
    assert adopted["status"] == "draft"
    assert env.client.post(f"{PREFIX}/reports/{v1_id}/complete", json={"revision": adopted["revision"]}, headers=env.alice).status_code == 422


def test_v1_weekly_converts_and_keeps_the_original(env):
    """验收8：一期周报转二期时不把人工写好的结果替换成百分比模板。"""
    monday = week_range(today_shanghai())[0] - timedelta(days=112)
    v1_id = _v1_report(env, "weekly", monday, {
        "p_items": [{"item_id": str(uuid.uuid4()), "name": "线上巡检", "progress": "日常巡检",
                     "result": "完成巡检并记录问题", "manually_edited": True}],
        "r_items": [], "o_items": [],
    })
    preview = env.client.post(
        f"{PREFIX}/assemble-preview",
        json={"report_type": "weekly", "period_start": monday.isoformat(), "report_id": v1_id},
        headers=env.alice,
    ).json()
    assert preview["sections"]["legacy_supplement"]["p_items"][0]["result"] == "完成巡检并记录问题"
    assert any("一期" in warning for warning in preview["warnings"])
    adopted = env.client.post(f"{PREFIX}/reports/{v1_id}/assemble?mode=replace", headers=env.alice).json()
    assert adopted["template_version"] == "weekly_pro_v2"
    assert adopted["sections"]["legacy_supplement"]["p_items"][0]["result"] == "完成巡检并记录问题"


def test_v1_report_can_still_be_saved_without_conversion(env):
    """一期报告不转换也能继续保存，避免用户改个标题就被新版校验拦住。"""
    day = today_shanghai() - timedelta(days=7)
    v1_id = _v1_report(env, "daily", day, {
        "items": [{"item_id": str(uuid.uuid4()), "name": "旧事项", "progress": "旧进展", "result": "旧结果", "status": "completed"}],
        "quality": "", "blockers": [], "next_plan": [], "reflection": "",
    })
    current = env.client.get(f"{PREFIX}/reports/{v1_id}", headers=env.alice).json()
    saved = env.client.put(
        f"{PREFIX}/reports/{v1_id}",
        json={"title": "改过的标题", "sections": current["sections"], "revision": current["revision"]},
        headers=env.alice,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["template_version"] == "daily_v1"
    assert saved.json()["sections"]["items"][0]["name"] == "旧事项"
