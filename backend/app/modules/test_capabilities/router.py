"""Test capability routes for scenarios, mock, performance, and runner management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.db import get_db
from app.models.entities import ApiScenario, MockRule, PerformanceScenario, RunnerAgent
from app.modules.test_capabilities.schemas import (
    ApiScenarioCreate,
    ApiScenarioRead,
    MockRuleCreate,
    MockRuleRead,
    PerformanceScenarioCreate,
    PerformanceScenarioRead,
    RunnerAgentCreate,
    RunnerAgentRead,
)
from app.modules.test_capabilities.service import ensure_environment, ensure_project, ensure_unique_code, mark_runner_seen, validate_performance_target, validate_runner_url


router = APIRouter(tags=["测试能力"])


@router.get("/v1/api-scenarios", response_model=list[ApiScenarioRead], summary="查询接口场景")
def list_api_scenarios(_: AuthContext = Depends(require_menu("capabilities")), db: Session = Depends(get_db)):
    """List API scenario orchestration records."""
    return db.query(ApiScenario).order_by(ApiScenario.id.desc()).all()


@router.post("/v1/api-scenarios", response_model=ApiScenarioRead, summary="新增接口场景")
def create_api_scenario(payload: ApiScenarioCreate, _: AuthContext = Depends(require_menu("capabilities")), db: Session = Depends(get_db)):
    """Create an API scenario with variables, case order, and script notes."""
    ensure_project(db, payload.project_id)
    ensure_environment(db, payload.environment_id)
    ensure_unique_code(db, ApiScenario, payload.code, message="Scenario code already exists")
    item = ApiScenario(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/v1/api-scenarios/{scenario_id}", response_model=ApiScenarioRead, summary="修改接口场景")
def update_api_scenario(scenario_id: int, payload: ApiScenarioCreate, _: AuthContext = Depends(require_menu("capabilities")), db: Session = Depends(get_db)):
    """Update an API scenario."""
    item = db.get(ApiScenario, scenario_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    ensure_project(db, payload.project_id)
    ensure_environment(db, payload.environment_id)
    ensure_unique_code(db, ApiScenario, payload.code, exclude_id=scenario_id, message="Scenario code already exists")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/v1/api-scenarios/{scenario_id}", summary="删除接口场景")
def delete_api_scenario(scenario_id: int, _: AuthContext = Depends(require_menu("capabilities")), db: Session = Depends(get_db)):
    """Delete an API scenario."""
    item = db.get(ApiScenario, scenario_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    db.delete(item)
    db.commit()
    return {"status": "ok"}


@router.get("/v1/mock-rules", response_model=list[MockRuleRead], summary="查询 Mock 规则")
def list_mock_rules(_: AuthContext = Depends(require_menu("capabilities")), db: Session = Depends(get_db)):
    """List API mock rules."""
    return db.query(MockRule).order_by(MockRule.id.desc()).all()


@router.post("/v1/mock-rules", response_model=MockRuleRead, summary="新增 Mock 规则")
def create_mock_rule(payload: MockRuleCreate, _: AuthContext = Depends(require_menu("capabilities")), db: Session = Depends(get_db)):
    """Create a mock rule. This version stores rules; a mock gateway can consume them later."""
    ensure_project(db, payload.project_id)
    item = MockRule(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/v1/mock-rules/{rule_id}", response_model=MockRuleRead, summary="修改 Mock 规则")
def update_mock_rule(rule_id: int, payload: MockRuleCreate, _: AuthContext = Depends(require_menu("capabilities")), db: Session = Depends(get_db)):
    """Update a mock rule."""
    item = db.get(MockRule, rule_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Mock rule not found")
    ensure_project(db, payload.project_id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/v1/mock-rules/{rule_id}", summary="删除 Mock 规则")
def delete_mock_rule(rule_id: int, _: AuthContext = Depends(require_menu("capabilities")), db: Session = Depends(get_db)):
    """Delete a mock rule."""
    item = db.get(MockRule, rule_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Mock rule not found")
    db.delete(item)
    db.commit()
    return {"status": "ok"}


@router.get("/v1/performance-scenarios", response_model=list[PerformanceScenarioRead], summary="查询性能场景")
def list_performance_scenarios(_: AuthContext = Depends(require_menu("capabilities")), db: Session = Depends(get_db)):
    """List performance scenario configs."""
    return db.query(PerformanceScenario).order_by(PerformanceScenario.id.desc()).all()


@router.post("/v1/performance-scenarios", response_model=PerformanceScenarioRead, summary="新增性能场景")
def create_performance_scenario(payload: PerformanceScenarioCreate, _: AuthContext = Depends(require_menu("capabilities")), db: Session = Depends(get_db)):
    """Create a performance scenario for JMeter or external runner execution."""
    ensure_project(db, payload.project_id)
    validate_performance_target(payload.target_url)
    ensure_unique_code(db, PerformanceScenario, payload.code, message="Performance scenario code already exists")
    item = PerformanceScenario(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/v1/performance-scenarios/{scenario_id}", response_model=PerformanceScenarioRead, summary="修改性能场景")
def update_performance_scenario(scenario_id: int, payload: PerformanceScenarioCreate, _: AuthContext = Depends(require_menu("capabilities")), db: Session = Depends(get_db)):
    """Update a performance scenario."""
    item = db.get(PerformanceScenario, scenario_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Performance scenario not found")
    ensure_project(db, payload.project_id)
    validate_performance_target(payload.target_url)
    ensure_unique_code(db, PerformanceScenario, payload.code, exclude_id=scenario_id, message="Performance scenario code already exists")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/v1/performance-scenarios/{scenario_id}", summary="删除性能场景")
def delete_performance_scenario(scenario_id: int, _: AuthContext = Depends(require_menu("capabilities")), db: Session = Depends(get_db)):
    """Delete a performance scenario."""
    item = db.get(PerformanceScenario, scenario_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Performance scenario not found")
    db.delete(item)
    db.commit()
    return {"status": "ok"}


@router.get("/v1/runners", response_model=list[RunnerAgentRead], summary="查询执行机")
def list_runners(_: AuthContext = Depends(require_menu("capabilities")), db: Session = Depends(get_db)):
    """List runner agents and their capabilities."""
    return db.query(RunnerAgent).order_by(RunnerAgent.id.desc()).all()


@router.post("/v1/runners", response_model=RunnerAgentRead, summary="新增执行机")
def create_runner(payload: RunnerAgentCreate, _: AuthContext = Depends(require_menu("capabilities")), db: Session = Depends(get_db)):
    """Create a runner metadata record."""
    validate_runner_url(payload.base_url)
    ensure_unique_code(db, RunnerAgent, payload.code, message="Runner code already exists")
    item = RunnerAgent(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/v1/runners/{runner_id}", response_model=RunnerAgentRead, summary="修改执行机")
def update_runner(runner_id: int, payload: RunnerAgentCreate, _: AuthContext = Depends(require_menu("capabilities")), db: Session = Depends(get_db)):
    """Update a runner metadata record."""
    item = db.get(RunnerAgent, runner_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Runner not found")
    validate_runner_url(payload.base_url)
    ensure_unique_code(db, RunnerAgent, payload.code, exclude_id=runner_id, message="Runner code already exists")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.post("/v1/runners/{runner_id}/heartbeat", response_model=RunnerAgentRead, summary="执行机心跳")
def runner_heartbeat(runner_id: int, _: AuthContext = Depends(require_menu("capabilities")), db: Session = Depends(get_db)):
    """Mark a runner as online and update its heartbeat time."""
    item = db.get(RunnerAgent, runner_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Runner not found")
    mark_runner_seen(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/v1/runners/{runner_id}", summary="删除执行机")
def delete_runner(runner_id: int, _: AuthContext = Depends(require_menu("capabilities")), db: Session = Depends(get_db)):
    """Delete a runner metadata record."""
    item = db.get(RunnerAgent, runner_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Runner not found")
    db.delete(item)
    db.commit()
    return {"status": "ok"}
