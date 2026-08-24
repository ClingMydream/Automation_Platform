from fastapi import APIRouter,Depends,File,HTTPException,Query,UploadFile
from sqlalchemy import or_,select
from sqlalchemy.orm import Session

from app.core.auth import require_menu
from app.db import get_db
from app.models.entities import ApiRecord
from app.modules.api_workspace.schemas import ApiRecordInput
from app.modules.api_workspace.service import parse_api_import

router=APIRouter(prefix="/v1/api-workspace",tags=["api-workspace"],dependencies=[Depends(require_menu("api_workspace"))])

def output(item): return {c.name:getattr(item,c.name) for c in item.__table__.columns}

@router.get("/records")
def records(q:str="",method:str|None=None,db:Session=Depends(get_db)):
    stmt=select(ApiRecord)
    if q: stmt=stmt.where(or_(ApiRecord.name.contains(q),ApiRecord.url.contains(q),ApiRecord.description.contains(q)))
    if method: stmt=stmt.where(ApiRecord.method==method.upper())
    return [output(x) for x in db.scalars(stmt.order_by(ApiRecord.updated_at.desc())).all()]

@router.post("/records")
def create(payload:ApiRecordInput,db:Session=Depends(get_db)):
    item=ApiRecord(**payload.model_dump());db.add(item);db.commit();db.refresh(item);return output(item)

@router.put("/records/{record_id}")
def update(record_id:int,payload:ApiRecordInput,db:Session=Depends(get_db)):
    item=db.get(ApiRecord,record_id)
    if not item: raise HTTPException(404,"接口记录不存在")
    for k,v in payload.model_dump().items():setattr(item,k,v)
    db.commit();db.refresh(item);return output(item)

@router.delete("/records/{record_id}")
def delete(record_id:int,db:Session=Depends(get_db)):
    item=db.get(ApiRecord,record_id)
    if not item: raise HTTPException(404,"接口记录不存在")
    db.delete(item);db.commit();return {"ok":True}

@router.post("/imports")
async def import_records(file:UploadFile=File(...),db:Session=Depends(get_db)):
    content=await file.read(10*1024*1024+1)
    if len(content)>10*1024*1024: raise HTTPException(413,"导入文件不能超过 10MB")
    try: rows=parse_api_import(file.filename or "",content)
    except (ValueError,UnicodeError) as exc: raise HTTPException(400,str(exc))
    created=[];failed=[]
    for index,row in enumerate(rows,1):
        try:
            payload=ApiRecordInput(**row);created.append(ApiRecord(**payload.model_dump()))
        except Exception as exc: failed.append({"row":index,"reason":str(exc)})
    db.add_all(created);db.commit()
    return {"created":len(created),"failed":failed}
