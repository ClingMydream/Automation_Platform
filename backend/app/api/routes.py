"""Aggregate every backend module router under the shared /api prefix."""

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.api_workspace.router import router as api_workspace_router
from app.modules.data_generator.router import router as data_generator_router
from app.modules.file_transfer.router import router as file_transfer_router
from app.modules.health.router import router as health_router
from app.modules.image_tools.router import router as image_tools_router
from app.modules.integrations.router import router as integrations_router
from app.modules.learning.mastery_router import router as learning_mastery_router
from app.modules.users.router import router as users_router
from app.modules.test_packages.router import router as test_packages_router
from app.modules.command_library.router import router as command_library_router
from app.modules.hotel_practice.router import router as hotel_practice_router
from app.modules.online_preview.router import router as online_preview_router
from app.modules.ui_automation.router import router as ui_automation_router


router = APIRouter()

# Keep the API surface intentionally limited to efficiency tools and settings.
for module_router in [
    health_router,
    api_workspace_router,
    auth_router,
    users_router,
    data_generator_router,
    file_transfer_router,
    test_packages_router,
    image_tools_router,
    integrations_router,
    learning_mastery_router,
    command_library_router,
    hotel_practice_router,
    online_preview_router,
    ui_automation_router,
]:
    router.include_router(module_router)
