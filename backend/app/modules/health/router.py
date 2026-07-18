"""Health check route used by Docker, Nginx, and deployment verification."""

from fastapi import APIRouter


router = APIRouter(tags=["健康检查"])

# 基础健康检查：Docker 和反向代理用它判断后端是否可用。
@router.get(
    "/health",
    summary="后端健康检查",
    description="返回后端服务是否可用，适合部署巡检和容器健康检查。",
)
def health():
    """Return backend health status."""
    return {"status": "ok"}
