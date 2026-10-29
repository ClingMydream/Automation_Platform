import os
from datetime import datetime
from typing import Literal
from pathlib import PurePosixPath
import httpx
from fastapi import Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Integer, JSON, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from app.core.auth import AuthContext
from app.core.config import get_settings
from app.db import Base, get_db
from .router import management, guard, issue_token
from . import store


class PracticeRun(Base):
    __tablename__ = 'practice_execution_runs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner: Mapped[str] = mapped_column(String(120), index=True)
    suite: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default='queued')
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RunInput(BaseModel):
    suite: Literal['api','ui','performance']
    users: int = Field(default=1, ge=1, le=5, strict=True)
    duration: int = Field(default=10, ge=5, le=30, strict=True)


def runner_request(method, path, **kwargs):
    token = get_settings().ui_runner_token
    if not token:
        raise HTTPException(503, '实践执行器未配置，请先配置内部执行凭据')
    url = os.getenv('PRACTICE_RUNNER_URL','http://practice-runner:8093').rstrip('/')
    try:
        return httpx.request(method,url+path,headers={'X-Runner-Token':token},timeout=15,**kwargs)
    except httpx.RequestError:
        raise HTTPException(503, '实践执行器暂时失联，可刷新查看；不会自动重复启动测试')


def output(row):
    return {'id':row.id,'suite':row.suite,'status':row.status,'result':row.result,'created_at':row.created_at}


def owned_run(db,user,identifier):
    row=db.scalar(select(PracticeRun).where(PracticeRun.id==identifier,PracticeRun.owner==user.username))
    if not row:raise HTTPException(404,'执行记录不存在')
    return row


@management.post('/runs',status_code=201)
def start_run(payload:RunInput,user:AuthContext=Depends(guard),db:Session=Depends(get_db)):
    active=db.scalar(select(PracticeRun).where(PracticeRun.owner==user.username,PracticeRun.status.in_(['queued','running'])))
    if active:raise HTTPException(409,f'已有执行 #{active.id}，请先查看或停止它')
    tenant=store.tenant_id(user.username);store.initialize(tenant)
    conn=store.connect(tenant)
    try:
        gen=store.generation(conn)
        admin=conn.execute("SELECT * FROM users WHERE role='admin'").fetchone()
        customer=conn.execute("SELECT * FROM users WHERE username='_auto_customer'").fetchone()
        warehouse=conn.execute("SELECT * FROM users WHERE username='warehouse'").fetchone()
        other=conn.execute("SELECT * FROM users WHERE username='_auto_customer_two'").fetchone()
        credentials={'admin_token':issue_token(tenant,admin,gen),'customer_token':issue_token(tenant,customer,gen),'warehouse_token':issue_token(tenant,warehouse,gen),'other_customer_token':issue_token(tenant,other,gen)}
    finally:conn.close()
    row=PracticeRun(owner=user.username,suite=payload.suite,status='queued',result={'seed_version':store.SEED_VERSION,'target':'个人独立练习数据库'});db.add(row);db.commit();db.refresh(row)
    try:
        response=runner_request('POST','/runs',json={'id':str(row.id),'tenant':tenant,'suite':payload.suite,'users':payload.users,'duration':payload.duration,**credentials})
        if response.status_code!=202:raise HTTPException(503,'执行器拒绝启动，请刷新状态后重试')
    except HTTPException as error:
        row.status='blocked';row.result={'error':error.detail};db.commit();raise
    return output(row)


@management.get('/runs')
def runs(user:AuthContext=Depends(guard),db:Session=Depends(get_db)):
    return [output(row)for row in db.scalars(select(PracticeRun).where(PracticeRun.owner==user.username).order_by(PracticeRun.id.desc()).limit(100)).all()]


@management.get('/runs/{identifier}')
def run_status(identifier:int,user:AuthContext=Depends(guard),db:Session=Depends(get_db)):
    row=owned_run(db,user,identifier)
    if row.status in ['queued','running']:
        try:
            response=runner_request('GET',f'/runs/{identifier}')
            if response.status_code==404:
                row.status='interrupted';row.result={'error':'执行器重启或记录不存在，请重新运行'}
            elif response.status_code==200:
                data=response.json();row.status=data['status'];row.result={**row.result,**data.get('result',{})}
            else:raise HTTPException(503,'执行器返回异常，稍后刷新状态')
            db.commit()
        except HTTPException as error:
            return {**output(row),'connection_error':error.detail}
    return output(row)


@management.post('/runs/{identifier}/stop')
def stop_run(identifier:int,user:AuthContext=Depends(guard),db:Session=Depends(get_db)):
    row=owned_run(db,user,identifier)
    if row.status not in ['queued','running']:return output(row)
    response=runner_request('POST',f'/runs/{identifier}/stop')
    if response.status_code not in [200,404]:raise HTTPException(503,'尚未确认停止，请刷新状态')
    row.status='stopped';row.result={**row.result,'message':'用户停止执行'};db.commit();return output(row)


@management.get('/runs/{identifier}/artifacts/{filename}')
def artifact(identifier:int,filename:str,user:AuthContext=Depends(guard),db:Session=Depends(get_db)):
    row=owned_run(db,user,identifier)
    if filename not in row.result.get('artifacts',[]) or PurePosixPath(filename).name!=filename:raise HTTPException(404,'证据不存在')
    response=runner_request('GET',f'/runs/{identifier}/artifacts/{filename}')
    if response.status_code!=200:raise HTTPException(404,'证据文件不可用')
    return Response(response.content,media_type='application/octet-stream',headers={'Content-Disposition':f'attachment; filename="{filename}"','X-Content-Type-Options':'nosniff'})
