"""Health check route used by Docker, Nginx, and deployment verification."""

from fastapi import APIRouter


router = APIRouter()

# 基础健康检查：Docker 和反向代理用它判断后端是否可用。
@router.get("/health")
def health():
    """Return backend health status."""
    return {"status": "ok"}
