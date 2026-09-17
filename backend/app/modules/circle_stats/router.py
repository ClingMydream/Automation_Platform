"""Authenticated proxy for the isolated DingTalk statistics runner."""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from datetime import date
from app.core.auth import require_menu
from app.core.config import get_settings

router = APIRouter(prefix="/v1/circle-stats", tags=["全员圈统计"])
guard = Depends(require_menu("circle_stats"))

class PrepareInput(BaseModel):
    start: date
    end: date
    row: int = Field(ge=2, le=100000)
    max_rows: int | None = Field(default=None, ge=1, le=100000)

def target(path=""):
    settings=get_settings(); return settings.circle_runner_url.rstrip("/")+path, {"Authorization": f"Bearer {settings.ui_runner_token or ''}"}

async def request(method, path, **kwargs):
    url, headers=target(path)
    try:
        async with httpx.AsyncClient(timeout=20) as client: response=await client.request(method,url,headers=headers,**kwargs)
    except httpx.RequestError as exc: raise HTTPException(503,"全员圈统计服务暂不可用") from exc
    if response.status_code >= 400:
        try: detail=response.json().get("detail")
        except Exception: detail=None
        raise HTTPException(response.status_code, detail or "统计服务请求失败")
    return response

@router.get("/status", dependencies=[guard])
async def status(): return (await request("GET","/health")).json()

@router.post("/runs", dependencies=[guard])
async def prepare(body: PrepareInput): return (await request("POST","/runs",json=body.model_dump(mode="json"))).json()

@router.get("/runs/{run_id}", dependencies=[guard])
async def run_status(run_id: str): return (await request("GET",f"/runs/{run_id}")).json()

@router.post("/runs/{run_id}/write", dependencies=[guard])
async def write(run_id: str): return (await request("POST",f"/runs/{run_id}/write")).json()

@router.get("/runs/{run_id}/login.png", dependencies=[guard])
async def login_image(run_id: str):
    response=await request("GET",f"/runs/{run_id}/login.png")
    return StreamingResponse(iter([response.content]),media_type="image/png",headers={"Content-Disposition":"inline; filename=login.png"})
