"""Test dataset routes for variables, accounts, and parameterized data pools."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.db import get_db
from app.models.entities import Project, TestDataset
from app.modules.test_datasets.schemas import TestDatasetCreate, TestDatasetRead


router = APIRouter(tags=["测试数据"])


def ensure_dataset_project(db: Session, project_id: int | None) -> None:
    """Validate an optional project relation for a test dataset."""
    if project_id is not None and db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")


@router.get("/v1/test-datasets", response_model=list[TestDatasetRead], summary="查询测试数据集")
def list_test_datasets(_: AuthContext = Depends(require_menu("datasets")), db: Session = Depends(get_db)):
    """List reusable variable sets, accounts, and parameterized data pools."""
    return db.query(TestDataset).order_by(TestDataset.id.desc()).all()


@router.post("/v1/test-datasets", response_model=TestDatasetRead, summary="新增测试数据集")
def create_test_dataset(payload: TestDatasetCreate, _: AuthContext = Depends(require_menu("datasets")), db: Session = Depends(get_db)):
    """Create a reusable test dataset."""
    ensure_dataset_project(db, payload.project_id)
    item = TestDataset(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/v1/test-datasets/{dataset_id}", response_model=TestDatasetRead, summary="修改测试数据集")
def update_test_dataset(dataset_id: int, payload: TestDatasetCreate, _: AuthContext = Depends(require_menu("datasets")), db: Session = Depends(get_db)):
    """Update one reusable test dataset."""
    item = db.get(TestDataset, dataset_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    ensure_dataset_project(db, payload.project_id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/v1/test-datasets/{dataset_id}", summary="删除测试数据集")
def delete_test_dataset(dataset_id: int, _: AuthContext = Depends(require_menu("datasets")), db: Session = Depends(get_db)):
    """Delete one reusable test dataset."""
    item = db.get(TestDataset, dataset_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    db.delete(item)
    db.commit()
    return {"status": "ok"}
