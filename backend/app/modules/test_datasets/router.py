"""Test dataset routes for variables, accounts, and parameterized data pools."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.core.config import get_settings
from app.db import get_db
from app.models.entities import Project, TestDataset
from app.modules.test_datasets.schemas import TestDataGenerateRequest, TestDataGenerateResponse, TestDatasetCreate, TestDatasetRead
from app.modules.test_datasets.service import generate_id_cards, generate_phone_numbers


router = APIRouter(tags=["测试数据"])


@router.post("/v1/test-data/generate", response_model=TestDataGenerateResponse, summary="生成合成测试数据")
def generate_test_data(payload: TestDataGenerateRequest, _: AuthContext = Depends(require_menu("datasets"))):
    """Generate format-valid test values without pretending synthetic phones receive SMS."""
    if payload.kind == "id_card":
        rows = generate_id_cards(
            payload.count,
            gender=payload.gender,
            min_birth_year=payload.min_birth_year,
            max_birth_year=payload.max_birth_year,
        )
        warning = "身份证号码仅为规则校验通过的合成测试数据，不对应或证明任何真实身份。"
    else:
        rows = generate_phone_numbers(
            payload.count,
            mode=payload.phone_mode,
            configured_numbers=get_settings().test_sms_phone_numbers,
        )
        if payload.phone_mode == "configured_receivers":
            warning = "号码来自服务端配置的自有/已租用接收号码；能否收信仍取决于运营商、供应商能力和合规配置。"
        elif payload.phone_mode == "twilio_magic":
            warning = "Twilio 魔术号码只模拟 API 校验，不连接运营商，也不会收到真实短信。"
        else:
            warning = "中国手机号仅保证格式，不保证未分配；不得拨打或发送短信。真实收信请使用自有/已租用号码模式。"
    return TestDataGenerateResponse(rows=rows, warning=warning)


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
