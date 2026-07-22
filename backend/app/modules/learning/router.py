from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.auth import verify_admin
from app.core.config import get_settings
from app.db import get_db
from app.models.entities import (LearningAttachment, LearningCheckin, LearningNote, LearningNoteFolder,
    LearningPlan, LearningProfile, LearningScheduleShift, LearningTask)
from app.modules.learning.schemas import CheckinInput, FolderInput, NoteInput, ProfileUpdate, TaskInput
from app.modules.learning.service import ensure_seed, local_today, reconcile, stats
from app.modules.learning.importer import import_zip

router = APIRouter(prefix="/v1/learning", tags=["learning"], dependencies=[Depends(verify_admin)])


def data(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


@router.get("/profile")
def get_profile(db: Session = Depends(get_db)):
    ensure_seed(db); return data(db.scalar(select(LearningProfile)))


@router.put("/profile")
def put_profile(payload: ProfileUpdate, db: Session = Depends(get_db)):
    ensure_seed(db); obj = db.scalar(select(LearningProfile))
    for key, value in payload.model_dump().items(): setattr(obj, key, value)
    db.commit(); db.refresh(obj); return data(obj)


@router.post("/schedule/reconcile")
def reconcile_schedule(db: Session = Depends(get_db)): return reconcile(db)


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    ensure_seed(db); today = local_today(); plan = db.scalar(select(LearningPlan).where(LearningPlan.status == "active"))
    tasks = db.scalars(select(LearningTask).where(LearningTask.plan_id == plan.id).order_by(LearningTask.planned_date, LearningTask.sort_order)).all()
    latest = db.scalar(select(LearningCheckin).order_by(LearningCheckin.checkin_date.desc()))
    shift = db.scalar(select(LearningScheduleShift).order_by(LearningScheduleShift.id.desc()))
    done = sum(t.status == "completed" for t in tasks)
    today_tasks = [data(t) for t in tasks if t.planned_date == today]
    next_task = next((data(t) for t in tasks if t.status != "completed"), None)
    return {"profile": data(db.scalar(select(LearningProfile))), "plan": data(plan), "today": today,
        "today_tasks": today_tasks, "next_task": next_task, "current_phase": next_task["phase"] if next_task else "已完成",
        "completed_tasks": done, "total_tasks": len(tasks), "progress": round(done / len(tasks) * 100, 1) if tasks else 0,
        "latest_checkin": data(latest) if latest else None, "latest_shift": data(shift) if shift else None,
        "deadline_risk": plan.projected_end_date > db.scalar(select(LearningProfile)).target_date}


@router.get("/tasks")
def list_tasks(day: date | None = None, phase: str | None = None, db: Session = Depends(get_db)):
    ensure_seed(db); q = select(LearningTask)
    if day: q = q.where(LearningTask.planned_date == day)
    if phase: q = q.where(LearningTask.phase == phase)
    return [data(x) for x in db.scalars(q.order_by(LearningTask.planned_date, LearningTask.sort_order)).all()]


@router.post("/tasks")
def create_task(payload: TaskInput, db: Session = Depends(get_db)):
    ensure_seed(db); values = payload.model_dump(); values["plan_id"] = values["plan_id"] or db.scalar(select(LearningPlan).where(LearningPlan.status == "active")).id
    values["original_planned_date"] = values["original_planned_date"] or values["planned_date"]
    obj = LearningTask(**values); db.add(obj); db.commit(); db.refresh(obj); return data(obj)


@router.put("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskInput, db: Session = Depends(get_db)):
    obj = db.get(LearningTask, task_id)
    if not obj: raise HTTPException(404, "任务不存在")
    old_status = obj.status
    for key, value in payload.model_dump(exclude={"plan_id", "original_planned_date"}).items(): setattr(obj, key, value)
    if obj.status == "completed" and old_status != "completed": obj.completed_at = datetime.utcnow()
    if obj.status != "completed": obj.completed_at = None
    db.commit(); db.refresh(obj); return data(obj)


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    obj = db.get(LearningTask, task_id)
    if not obj: raise HTTPException(404, "任务不存在")
    db.delete(obj); db.commit(); return {"ok": True}


@router.put("/checkins/{checkin_date}")
def save_checkin(checkin_date: date, payload: CheckinInput, db: Session = Depends(get_db)):
    obj = db.scalar(select(LearningCheckin).where(LearningCheckin.checkin_date == checkin_date)) or LearningCheckin(checkin_date=checkin_date)
    for key, value in payload.model_dump().items(): setattr(obj, key, value)
    db.add(obj); db.commit(); db.refresh(obj); return data(obj)


@router.get("/stats")
def get_stats(month: str = Query(pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db)): ensure_seed(db); return stats(db, month)


@router.get("/note-folders")
def folders(db: Session = Depends(get_db)): return [data(x) for x in db.scalars(select(LearningNoteFolder).order_by(LearningNoteFolder.sort_order, LearningNoteFolder.name)).all()]


@router.post("/note-folders")
def create_folder(payload: FolderInput, db: Session = Depends(get_db)):
    obj = LearningNoteFolder(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return data(obj)


@router.put("/note-folders/{folder_id}")
def update_folder(folder_id: int, payload: FolderInput, db: Session = Depends(get_db)):
    obj = db.get(LearningNoteFolder, folder_id)
    if not obj: raise HTTPException(404, "文件夹不存在")
    for k,v in payload.model_dump().items(): setattr(obj,k,v)
    db.commit(); return data(obj)


@router.delete("/note-folders/{folder_id}")
def delete_folder(folder_id: int, db: Session = Depends(get_db)):
    obj=db.get(LearningNoteFolder,folder_id)
    if not obj: raise HTTPException(404,"文件夹不存在")
    for note in db.scalars(select(LearningNote).where(LearningNote.folder_id==folder_id)): note.folder_id=None
    db.delete(obj); db.commit(); return {"ok":True}


@router.get("/notes")
def notes(q: str = "", folder_id: int | None = None, trash: bool = False, db: Session = Depends(get_db)):
    stmt=select(LearningNote).where(LearningNote.deleted_at.is_not(None) if trash else LearningNote.deleted_at.is_(None))
    if folder_id is not None: stmt=stmt.where(LearningNote.folder_id==folder_id)
    if q: stmt=stmt.where(or_(LearningNote.title.contains(q), LearningNote.content_markdown.contains(q)))
    return [data(x) for x in db.scalars(stmt.order_by(LearningNote.is_pinned.desc(),LearningNote.updated_at.desc())).all()]


@router.post("/notes")
def create_note(payload: NoteInput, db: Session = Depends(get_db)):
    values=payload.model_dump(exclude={"restore"}); obj=LearningNote(**values); db.add(obj); db.commit(); db.refresh(obj); return data(obj)


@router.put("/notes/{note_id}")
def update_note(note_id:int,payload:NoteInput,db:Session=Depends(get_db)):
    obj=db.get(LearningNote,note_id)
    if not obj: raise HTTPException(404,"笔记不存在")
    for k,v in payload.model_dump(exclude={"restore"}).items(): setattr(obj,k,v)
    if payload.restore: obj.deleted_at=None
    db.commit(); db.refresh(obj); return data(obj)


@router.delete("/notes/{note_id}")
def delete_note(note_id:int,db:Session=Depends(get_db)):
    obj=db.get(LearningNote,note_id)
    if not obj: raise HTTPException(404,"笔记不存在")
    obj.deleted_at=datetime.utcnow(); db.commit(); return {"ok":True}


ALLOWED={".png",".jpg",".jpeg",".gif",".webp",".pdf",".doc",".docx",".xls",".xlsx",".ppt",".pptx",".txt",".md",".json",".yaml",".yml",".zip"}


@router.post("/notes/{note_id}/attachments")
async def upload_attachment(note_id:int,file:UploadFile=File(...),db:Session=Depends(get_db)):
    if not db.get(LearningNote,note_id): raise HTTPException(404,"笔记不存在")
    settings=get_settings(); suffix=Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED: raise HTTPException(400,"不支持该文件类型")
    content=await file.read(settings.learning_attachment_max_mb*1024*1024+1)
    if len(content)>settings.learning_attachment_max_mb*1024*1024: raise HTTPException(413,"附件超过 20MB")
    root=Path(settings.learning_data_dir)/"attachments"; root.mkdir(parents=True,exist_ok=True)
    used=sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
    if used+len(content)>settings.learning_storage_max_mb*1024*1024: raise HTTPException(507,"学习文件空间不足")
    stored=f"{uuid4().hex}{suffix}"; path=root/stored; path.write_bytes(content)
    is_image=suffix in {".png",".jpg",".jpeg",".gif",".webp"}
    if is_image:
        try:
            from PIL import Image
            with Image.open(path) as image: image.verify()
        except Exception:
            path.unlink(missing_ok=True); raise HTTPException(400,"图片内容无效")
    obj=LearningAttachment(note_id=note_id,original_name=Path(file.filename).name,stored_name=stored,
        content_type=file.content_type or "application/octet-stream",size_bytes=len(content),is_image=is_image)
    db.add(obj); db.commit(); db.refresh(obj)
    return {**data(obj),"url":f"/api/v1/learning/attachments/{obj.id}"}

@router.get("/notes/{note_id}/attachments")
def list_attachments(note_id:int,db:Session=Depends(get_db)):
    return [{**data(x),"url":f"/api/v1/learning/attachments/{x.id}"} for x in db.scalars(select(LearningAttachment).where(LearningAttachment.note_id==note_id)).all()]


@router.get("/attachments/{attachment_id}")
def download_attachment(attachment_id:int,db:Session=Depends(get_db)):
    obj=db.get(LearningAttachment,attachment_id)
    if not obj: raise HTTPException(404,"附件不存在")
    path=Path(get_settings().learning_data_dir)/"attachments"/obj.stored_name
    return FileResponse(path,media_type=obj.content_type,filename=None if obj.is_image else obj.original_name,
        headers={"X-Content-Type-Options":"nosniff","Content-Disposition":("inline" if obj.is_image else f'attachment; filename="{obj.original_name}"')})


@router.delete("/attachments/{attachment_id}")
def delete_attachment(attachment_id:int,db:Session=Depends(get_db)):
    obj=db.get(LearningAttachment,attachment_id)
    if not obj: raise HTTPException(404,"附件不存在")
    (Path(get_settings().learning_data_dir)/"attachments"/obj.stored_name).unlink(missing_ok=True)
    db.delete(obj); db.commit(); return {"ok":True}

@router.post("/imports/youdao")
async def import_youdao(file:UploadFile=File(...),db:Session=Depends(get_db)):
    import zipfile
    settings=get_settings()
    if Path(file.filename or "").suffix.lower()!=".zip": raise HTTPException(400,"请选择 ZIP 导出包")
    root=Path(settings.learning_data_dir); temp=root/"imports"/f"{uuid4().hex}.zip"; temp.parent.mkdir(parents=True,exist_ok=True); size=0
    try:
        with temp.open("wb") as out:
            while chunk:=await file.read(1024*1024):
                size+=len(chunk)
                if size>settings.learning_import_max_mb*1024*1024: raise HTTPException(413,"ZIP 超过 200MB")
                out.write(chunk)
        try: return import_zip(db,temp,Path(file.filename).name,root,{"entries":settings.learning_import_max_entries,"expanded":settings.learning_import_expanded_max_mb*1024*1024,"attachment":settings.learning_attachment_max_mb*1024*1024})
        except (ValueError,zipfile.BadZipFile) as exc: raise HTTPException(400,str(exc))
    finally: temp.unlink(missing_ok=True)
