"""Business helpers for turning failed test evidence into diagnosis records."""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import ExecutionBatch, ProblemFinding, TestObject, TestResult
from app.modules.problem_diagnosis.schemas import ProblemFindingCreate


def ensure_finding_relations(db: Session, payload: ProblemFindingCreate) -> None:
    """Validate optional result, batch, and test object relations."""
    if payload.result_id is not None and db.get(TestResult, payload.result_id) is None:
        raise HTTPException(status_code=404, detail="Result not found")
    if payload.batch_id is not None and db.get(ExecutionBatch, payload.batch_id) is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    if payload.test_object_id is not None and db.get(TestObject, payload.test_object_id) is None:
        raise HTTPException(status_code=404, detail="Test object not found")


def finding_payload_data(payload: ProblemFindingCreate) -> dict:
    """Convert request data into ORM-ready values and normalize optional fields."""
    data = payload.model_dump()
    for key in ["failure_category", "root_cause", "reproduce_steps", "owner", "suggestion"]:
        data[key] = data[key] or None
    if data["status"] == "fixed":
        data["resolved_at"] = datetime.utcnow()
    else:
        data["resolved_at"] = None
    return data


def infer_category(result: TestResult) -> str:
    """Infer a failure category from explicit labels, error text, logs, and assertions."""
    text = " ".join(
        [
            result.failure_category or "",
            result.error or "",
            result.logs or "",
            str(result.assertions or ""),
        ]
    ).lower()
    if result.failure_category:
        return result.failure_category
    if "timeout" in text or "timed out" in text:
        return "timeout"
    if "assert" in text or "expected" in text:
        return "assertion"
    if "connection" in text or "dns" in text or "network" in text:
        return "network"
    if result.result_type == "ui":
        return "ui_element"
    return "unknown"


def infer_severity(result: TestResult, category: str) -> str:
    """Pick a default severity from result status and failure category."""
    if result.status == "error" or category in {"network", "timeout"}:
        return "high"
    if category == "assertion":
        return "medium"
    return "low"


def build_finding_from_result(result: TestResult) -> ProblemFindingCreate:
    """Create a suggested diagnosis payload from one failed or errored result."""
    category = infer_category(result)
    result_label = f"{result.result_type.upper()} 结果 #{result.id}"
    root_cause = result.error or result.logs or "暂无明确错误信息，需要结合请求、响应、截图或日志继续定位。"
    reproduce_steps = "\n".join(
        [
            f"1. 打开结果中心，查看测试结果 #{result.id}。",
            "2. 复核请求数据、响应数据、断言详情和附件证据。",
            "3. 在相同环境下重新执行关联用例，确认是否稳定复现。",
        ]
    )
    suggestion = "优先确认环境、测试数据和断言配置；如果可以稳定复现，再提交给对应研发或服务负责人处理。"
    evidence = {
        "status": result.status,
        "result_type": result.result_type,
        "duration_ms": result.duration_ms,
        "request_data": result.request_data or {},
        "response_data": result.response_data or {},
        "assertions": result.assertions or [],
        "metrics": result.metrics or {},
    }
    return ProblemFindingCreate(
        result_id=result.id,
        batch_id=result.batch_id,
        test_object_id=result.test_object_id,
        title=f"{result_label} 失败定位",
        severity=infer_severity(result, category),
        status="open",
        failure_category=category,
        root_cause=root_cause,
        reproduce_steps=reproduce_steps,
        evidence=evidence,
        suggestion=suggestion,
        source="generated",
    )
