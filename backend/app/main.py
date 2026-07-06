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
        "description": "登录、退出和当前登录用户信息；JMeter 压测时通常先调用登录接口提取 token。",
    },
    {
        "name": "用户管理",
        "description": "管理员维护登录人员和菜单权限；普通用户不可访问。",
    },
    {
        "name": "项目与环境",
        "description": "维护项目和测试环境，是接口测试、UI 测试和执行记录的基础数据。",
    },
    {
        "name": "接口测试",
        "description": "维护接口自动化用例配置，执行逻辑由 worker 中的 pytest + requests + allure 完成。",
    },
    {
        "name": "UI测试",
        "description": "维护低代码 UI 自动化步骤，执行逻辑由 worker 中的 pytest + Playwright + allure 完成。",
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
        "name": "执行记录",
        "description": "创建自动化执行任务并查询执行结果；性能测试时重点关注创建任务和轮询结果。",
    },
    {
        "name": "测试报告",
        "description": "从执行记录汇总测试报告，供页面展示和后续导出扩展。",
    },
]

# FastAPI instance is the backend HTTP application mounted by Uvicorn.
app = FastAPI(
    title="Automation Platform API",
    summary="自动化测试平台后端接口",
    description=(
        "该 Swagger 文档按平台菜单抽象接口，覆盖登录认证、项目环境、接口测试、UI 测试、"
        "文件快传、图片工具、执行记录、测试报告和用户管理。后续做 JMeter 性能测试时，"
        "可直接使用 /api/openapi.json 作为接口清单，并通过登录接口提取 Bearer Token。"
    ),
    version="1.0.0",
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
