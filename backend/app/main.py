"""FastAPI application entrypoint for backend startup, middleware, and route mounting."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.db import Base, engine
from app.models import entities  # noqa: F401


# Swagger 分组元数据：这里的顺序会影响 /api/docs 页面左侧接口分组的展示顺序。
OPENAPI_TAGS = [
    {
        "name": "健康检查",
        "description": "用于 Docker、Nginx、部署脚本和人工巡检确认后端是否存活。",
    },
    {
        "name": "认证",
        "description": "登录和当前用户信息。",
    },
    {
        "name": "用户管理",
        "description": "管理员维护登录人员和菜单权限；普通用户不可访问。",
    },
    {
        "name": "数据生成",
        "description": "生成手机号格式、受控短信号码和合成身份证号码。",
    },
    {
        "name": "文件快传",
        "description": "临时文件上传、扫码下载、手机下载回传；公开 token 接口用于手机端访问。",
    },
    {
        "name": "图片工具",
        "description": "图片生成、裁剪、缩放、压缩、文案叠加和格式转换。",
    },
    {
        "name": "集成开放",
        "description": "维护通用 Webhook、钉钉、企微和飞书配置。",
    },
]

# FastAPI instance is the backend HTTP application mounted by Uvicorn.
app = FastAPI(
    title="Toolbox API",
    summary="轻量效率工具箱后端接口",
    description="提供数据生成、文件快传、图片处理、Webhook 集成和用户管理能力。",
    version="2.0.0",
    openapi_tags=OPENAPI_TAGS,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "docExpansion": "none",
        "filter": True,
        "tryItOutEnabled": True,
    },
)

# CORS is permissive for the first version so the frontend can call the API from Nginx or local dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """Create database tables and ensure the default administrator account exists."""
    # SQLAlchemy creates missing tables at startup so a fresh Docker database can boot automatically.
    Base.metadata.create_all(bind=engine)


# All feature routers are grouped under /api for a clean Nginx reverse-proxy rule.
app.include_router(router, prefix="/api")
