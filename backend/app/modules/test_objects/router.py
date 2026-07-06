"""Test object API routes for describing what the platform should test."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.db import get_db
from app.models.entities import TestObject
from app.modules.test_objects.schemas import TestObjectCreate, TestObjectRead, TestObjectType
from app.modules.test_objects.service import ensure_project_exists, ensure_unique_code, payload_data


router = APIRouter(tags=["测试对象"])


# 测试对象层：只沉淀“测什么”，暂不强制改造旧接口用例和 UI 用例。
@router.get(
    "/v1/test-objects",
    response_model=list[TestObjectRead],
    summary="查询测试对象列表",
    description="按测试对象类型、项目、启用状态查询测试对象。该接口是测试对象层的第一批旁路能力。",
)
def list_test_objects(
    object_type: TestObjectType | None = Query(default=None, description="可选测试对象类型过滤"),
    project_id: int | None = Query(default=None, description="可选项目 ID 过滤"),
    is_active: bool | None = Query(default=None, description="可选启用状态过滤"),
    _: AuthContext = Depends(require_menu("test_objects")),
    db: Session = Depends(get_db),
):
    """List test objects with optional filters for the test object page."""
    query = db.query(TestObject)
    if object_type:
        query = query.filter(TestObject.object_type == object_type)
    if project_id is not None:
        query = query.filter(TestObject.project_id == project_id)
    if is_active is not None:
        query = query.filter(TestObject.is_active == is_active)
    return query.order_by(TestObject.id.desc()).all()


@router.post(
    "/v1/test-objects",
    response_model=TestObjectRead,
    summary="新增测试对象",
    description="创建一个平台级测试对象，例如接口、页面、自动化脚本、性能场景、设备或环境。",
)
def create_test_object(payload: TestObjectCreate, _: AuthContext = Depends(require_menu("test_objects")), db: Session = Depends(get_db)):
    """Create a test object after validating project relation and unique code."""
    data = payload_data(payload)
    ensure_project_exists(db, data["project_id"])
    ensure_unique_code(db, data["code"])
    item = TestObject(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put(
    "/v1/test-objects/{object_id}",
    response_model=TestObjectRead,
    summary="修改测试对象",
    description="更新测试对象的名称、类型、项目、业务模块、标签、启用状态和说明。",
)
def update_test_object(
    object_id: int,
    payload: TestObjectCreate,
    _: AuthContext = Depends(require_menu("test_objects")),
    db: Session = Depends(get_db),
):
    """Update an existing test object while preserving compatibility with old modules."""
    item = db.get(TestObject, object_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Test object not found")
    data = payload_data(payload)
    ensure_project_exists(db, data["project_id"])
    ensure_unique_code(db, data["code"], exclude_id=object_id)
    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete(
    "/v1/test-objects/{object_id}",
    summary="删除测试对象",
    description="删除测试对象记录。第一批改造中测试对象未强制绑定旧用例，因此删除不会影响旧用例和执行记录。",
)
def delete_test_object(object_id: int, _: AuthContext = Depends(require_menu("test_objects")), db: Session = Depends(get_db)):
    """Delete a test object without touching legacy cases or runs."""
    item = db.get(TestObject, object_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Test object not found")
    db.delete(item)
    db.commit()
    return {"status": "ok"}
