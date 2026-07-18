"""Aggregate every backend module router under the shared /api prefix."""

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.data_generator.router import router as data_generator_router
from app.modules.file_transfer.router import router as file_transfer_router
from app.modules.health.router import router as health_router
from app.modules.image_tools.router import router as image_tools_router
from app.modules.integrations.router import router as integrations_router
from app.modules.users.router import router as users_router


router = APIRouter()

# Keep the API surface intentionally limited to efficiency tools and settings.
for module_router in [
    health_router,
    auth_router,
    users_router,
    data_generator_router,
    file_transfer_router,
    image_tools_router,
    integrations_router,
]:
    router.include_router(module_router)
