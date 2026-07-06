"""Problem diagnosis routes for failure investigation and ownership tracking."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.db import get_db
from app.models.entities import ProblemFinding, TestResult
from app.modules.problem_diagnosis.schemas import ProblemFindingCreate, ProblemFindingRead
from app.modules.problem_diagnosis.service import build_finding_from_result, ensure_finding_relations, finding_payload_data


router = APIRouter(tags=["问题定位"])


@router.get("/v1/problem-findings", response_model=list[ProblemFindingRead], summary="查询问题定位记录")
def list_problem_findings(
    status: str | None = Query(default=None, description="可选处理状态过滤"),
    severity: str | None = Query(default=None, description="可选严重级别过滤"),
    _: AuthContext = Depends(require_menu("diagnosis")),
    db: Session = Depends(get_db),
):
    """List diagnosis records created manually or generated from failed results."""
    query = db.query(ProblemFinding)
    if status:
        query = query.filter(ProblemFinding.status == status)
    if severity:
        query = query.filter(ProblemFinding.severity == severity)
    return query.order_by(ProblemFinding.id.desc()).limit(300).all()


@router.post("/v1/problem-findings", response_model=ProblemFindingRead, summary="新增问题定位记录")
def create_problem_finding(payload: ProblemFindingCreate, _: AuthContext = Depends(require_menu("diagnosis")), db: Session = Depends(get_db)):
    """Create a manual diagnosis record."""
    ensure_finding_relations(db, payload)
    item = ProblemFinding(**finding_payload_data(payload))
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/v1/problem-findings/{finding_id}", response_model=ProblemFindingRead, summary="修改问题定位记录")
def update_problem_finding(finding_id: int, payload: ProblemFindingCreate, _: AuthContext = Depends(require_menu("diagnosis")), db: Session = Depends(get_db)):
    """Update an existing diagnosis record and resolve timestamp."""
    item = db.get(ProblemFinding, finding_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    ensure_finding_relations(db, payload)
    for key, value in finding_payload_data(payload).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/v1/problem-findings/{finding_id}", summary="删除问题定位记录")
def delete_problem_finding(finding_id: int, _: AuthContext = Depends(require_menu("diagnosis")), db: Session = Depends(get_db)):
    """Delete one diagnosis record without deleting its original test result."""
    item = db.get(ProblemFinding, finding_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    db.delete(item)
    db.commit()
    return {"status": "ok"}


@router.post("/v1/problem-findings/from-result/{result_id}", response_model=ProblemFindingRead, summary="从失败结果生成定位记录")
def create_problem_finding_from_result(result_id: int, _: AuthContext = Depends(require_menu("diagnosis")), db: Session = Depends(get_db)):
    """Generate an initial diagnosis record from one failed or errored test result."""
    result = db.get(TestResult, result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    if result.status not in {"failed", "error"}:
        raise HTTPException(status_code=400, detail="Only failed or errored results can generate findings")
    payload = build_finding_from_result(result)
    item = ProblemFinding(**finding_payload_data(payload))
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
