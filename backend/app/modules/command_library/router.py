from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.db import get_db
from app.models.entities import AppUser, CommandSnippet
from app.models.command_favorites import PersonalCommandFavorite
from pydantic import BaseModel, StrictBool
from sqlalchemy.exc import IntegrityError
from app.modules.command_library.schemas import CommandInput
from app.modules.command_library.service import ensure_commands

router = APIRouter(prefix="/v1/command-library", tags=["命令手册"], dependencies=[Depends(require_menu("command_library"))])


def data(item: CommandSnippet) -> dict:
    return {column.name: getattr(item, column.name) for column in item.__table__.columns}


def owner_id(db: Session, user: AuthContext):
    return db.scalar(select(AppUser.id).where(AppUser.username == user.username))


class FavoriteInput(BaseModel):
    is_favorite: StrictBool | None = None


@router.get("")
def list_commands(q: str = Query(default="", max_length=100), category: str = "", favorite: bool = False, db: Session = Depends(get_db), user: AuthContext = Depends(require_menu("command_library"))):
    ensure_commands(db); statement = select(CommandSnippet)
    if q:
        term = f"%{q.strip()}%"
        statement = statement.where(or_(CommandSnippet.title.like(term), CommandSnippet.command.like(term), CommandSnippet.description.like(term), CommandSnippet.interview_note.like(term)))
    if category: statement = statement.where(CommandSnippet.category == category)
    favorites = set(db.scalars(select(PersonalCommandFavorite.command_id).where(PersonalCommandFavorite.owner_user_id == owner_id(db, user))).all())
    if favorite: statement = statement.where(CommandSnippet.id.in_(favorites))
    rows = db.scalars(statement.order_by(CommandSnippet.is_favorite.desc(), CommandSnippet.category, CommandSnippet.id)).all()
    return [{**data(item), "is_favorite": item.id in favorites} for item in sorted(rows, key=lambda item: item.id not in favorites)]


@router.get("/categories")
def categories(db: Session = Depends(get_db)):
    ensure_commands(db)
    return list(db.scalars(select(CommandSnippet.category).distinct().order_by(CommandSnippet.category)).all())


@router.post("")
def create_command(payload: CommandInput, db: Session = Depends(get_db)):
    item = CommandSnippet(**payload.model_dump(), is_builtin=False); db.add(item); db.commit(); db.refresh(item); return data(item)


@router.put("/{command_id}")
def update_command(command_id: int, payload: CommandInput, db: Session = Depends(get_db)):
    item = db.get(CommandSnippet, command_id)
    if not item: raise HTTPException(404, "命令不存在")
    for key, value in payload.model_dump().items(): setattr(item, key, value)
    db.commit(); db.refresh(item); return data(item)


@router.put("/{command_id}/favorite")
def toggle_favorite(command_id: int, payload: FavoriteInput, db: Session = Depends(get_db), user: AuthContext = Depends(require_menu("command_library"))):
    item = db.get(CommandSnippet, command_id)
    if not item: raise HTTPException(404, "命令不存在")
    uid = owner_id(db, user)
    record = db.scalar(select(PersonalCommandFavorite).where(PersonalCommandFavorite.owner_user_id == uid, PersonalCommandFavorite.command_id == command_id))
    desired = payload.is_favorite if payload.is_favorite is not None else record is None
    if desired and record is None: db.add(PersonalCommandFavorite(owner_user_id=uid, command_id=command_id))
    elif not desired and record is not None: db.delete(record)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        if not desired: raise
    return {**data(item), "is_favorite": desired}


@router.delete("/{command_id}")
def delete_command(command_id: int, db: Session = Depends(get_db)):
    item = db.get(CommandSnippet, command_id)
    if not item: raise HTTPException(404, "命令不存在")
    if item.is_builtin: raise HTTPException(400, "内置命令不能删除，可以编辑或收藏")
    db.delete(item); db.commit(); return {"ok": True}
