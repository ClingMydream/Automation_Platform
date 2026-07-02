from fastapi import APIRouter

from app.modules.api_testing.router import router as api_testing_router
from app.modules.auth.router import router as auth_router
from app.modules.file_transfer.router import router as file_transfer_router
from app.modules.health.router import router as health_router
from app.modules.image_tools.router import router as image_tools_router
from app.modules.projects.router import router as projects_router
from app.modules.reports.router import router as reports_router
from app.modules.runs.router import router as runs_router
from app.modules.ui_testing.router import router as ui_testing_router
from app.modules.users.router import router as users_router


router = APIRouter()

for module_router in [
    health_router,
    auth_router,
    users_router,
    projects_router,
    api_testing_router,
    ui_testing_router,
    file_transfer_router,
    image_tools_router,
    runs_router,
    reports_router,
]:
    router.include_router(module_router)
