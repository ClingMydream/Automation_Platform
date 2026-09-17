"""Authenticated single-job runner for DingTalk circle statistics."""
import json, os, subprocess, sys, threading, uuid
from datetime import date
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

app = FastAPI(title="circle stats runner", docs_url=None, redoc_url=None)
TOKEN = os.environ.get("CIRCLE_RUNNER_TOKEN", "")
ROOT = Path(os.environ.get("CIRCLE_DATA_DIR", "/data")).resolve()
RUNS, LOCK = {}, threading.Lock()

class PrepareInput(BaseModel):
    start: date
    end: date
    row: int = Field(ge=2, le=100000)
    max_rows: int | None = Field(default=None, ge=1, le=100000)

def auth(value):
    if not TOKEN or value != f"Bearer {TOKEN}": raise HTTPException(401, "runner authentication failed")

def public(run):
    data = {k: v for k, v in run.items() if k not in {"process", "dir"}}
    paths = list(Path(run["dir"]).glob("*/run.json"))
    path = paths[0] if len(paths) == 1 else None
    if path and path.exists():
        plan = json.loads(path.read_text(encoding="utf-8"))
        data["preview"] = plan.get("posts", [])
        data["plan_status"] = plan.get("status")
    data["login_screenshot"] = (Path(run["dir"]) / "login.png").exists()
    return data

def execute(run_id, command, action):
    run = RUNS[run_id]; run.update(status="running", action=action, message="正在启动浏览器…")
    try:
        # A container restart can leave Chromium's symlink locks in the persistent
        # profile even though the owning process no longer exists in this container.
        profile = ROOT / "browser-profile"
        for name in ("SingletonCookie", "SingletonLock", "SingletonSocket"):
            (profile / name).unlink(missing_ok=True)
        output = []
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        run["process"] = proc
        for line in proc.stdout:
            line = line.strip()
            if line: output.append(line)
            if line.startswith("WAITING_LOGIN:"):
                run.update(status="waiting_login", message=f"请使用钉钉扫码登录，正在等待进入{line.split(':',1)[1]}")
            elif line and not line.startswith(("<", "- [pid=")): run["message"] = line[-500:]
        code = proc.wait()
        if code:
            meaningful = [line for line in output if not line.startswith(("<", "- [pid=", "Call log:"))]
            raise RuntimeError((meaningful[-1] if meaningful else f"脚本退出码 {code}")[-500:])
        run.update(status="prepared" if action == "prepare" else "completed", message="采集完成，请核对后确认写入" if action == "prepare" else "写入及回读校验完成")
    except Exception:
        raise
def safe_execute(run_id, command, action):
    try: execute(run_id, command, action)
    except Exception as exc: RUNS[run_id].update(status="failed", message=str(exc)[:500])
    finally: LOCK.release()

@app.get("/health")
def health():
    profile = ROOT / "browser-profile"
    return {"status": "ok", "busy": LOCK.locked(), "login_persistent": True, "profile_initialized": profile.exists() and any(profile.iterdir())}

@app.post("/runs")
def prepare(body: PrepareInput, authorization: str | None = Header(None)):
    auth(authorization)
    if body.start > body.end: raise HTTPException(422, "开始日期不能晚于结束日期")
    if body.end > date.today(): raise HTTPException(422, "结束日期不能晚于今天")
    if not LOCK.acquire(blocking=False): raise HTTPException(409, "已有统计任务正在执行")
    rid = uuid.uuid4().hex; folder = ROOT / "runs" / rid; folder.mkdir(parents=True)
    run = {"id": rid, "status": "queued", "action": "prepare", "message": "任务已排队", "dir": str(folder)}; RUNS[rid] = run
    cmd = [sys.executable, "/app/dingtalk_circle_sync.py", "--start", str(body.start), "--end", str(body.end), "--row", str(body.row), "--dry-run", "--headless", "--channel", "chromium", "--profile", str(ROOT/"browser-profile"), "--output", str(folder), "--login-screenshot", str(folder/"login.png")]
    if body.max_rows: cmd += ["--max-rows", str(body.max_rows)]
    threading.Thread(target=safe_execute, args=(rid,cmd,"prepare"), daemon=True).start()
    return public(run)

def get_run(run_id):
    run = RUNS.get(run_id)
    if not run:
        folder = ROOT / "runs" / run_id
        plans = list(folder.glob("*/run.json")) if folder.exists() else []
        if len(plans) != 1: raise HTTPException(404, "任务不存在")
        plan = json.loads(plans[0].read_text(encoding="utf-8"))
        status = "completed" if plan.get("status") == "completed" else "prepared"
        run = {"id": run_id, "status": status, "action": "prepare", "message": "已恢复历史采集计划", "dir": str(folder)}
        RUNS[run_id] = run
    return run

@app.get("/runs/{run_id}")
def status(run_id: str, authorization: str | None = Header(None)): auth(authorization); return public(get_run(run_id))

@app.post("/runs/{run_id}/write")
def write(run_id: str, authorization: str | None = Header(None)):
    auth(authorization); run = get_run(run_id)
    if run["status"] != "prepared": raise HTTPException(409, "只有已完成采集的任务可以写入")
    if not LOCK.acquire(blocking=False): raise HTTPException(409, "已有统计任务正在执行")
    plans = list(Path(run["dir"]).glob("*/run.json"))
    if len(plans) != 1: LOCK.release(); raise HTTPException(409, "未找到唯一的采集计划")
    run.update(status="queued", action="write", message="写入任务已排队")
    cmd = [sys.executable, "/app/dingtalk_circle_sync.py", "--resume", str(plans[0]), "--headless", "--channel", "chromium", "--profile", str(ROOT/"browser-profile"), "--login-screenshot", str(Path(run["dir"])/"login.png")]
    threading.Thread(target=safe_execute, args=(run_id,cmd,"write"), daemon=True).start()
    return public(run)

@app.get("/runs/{run_id}/login.png")
def login_image(run_id: str, authorization: str | None = Header(None)):
    auth(authorization); path=Path(get_run(run_id)["dir"])/"login.png"
    if not path.exists(): raise HTTPException(404,"暂无登录截图")
    return FileResponse(path, media_type="image/png")
