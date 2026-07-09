"""Aggregate every backend module router under the shared /api prefix."""

from fastapi import APIRouter

from app.modules.api_testing.router import router as api_testing_router
from app.modules.auth.router import router as auth_router
from app.modules.file_transfer.router import router as file_transfer_router
from app.modules.health.router import router as health_router
from app.modules.image_tools.router import router as image_tools_router
from app.modules.integrations.router import router as integrations_router
from app.modules.mock_service.router import router as mock_service_router
from app.modules.projects.router import router as projects_router
from app.modules.problem_diagnosis.router import router as problem_diagnosis_router
from app.modules.quality_analysis.router import router as quality_analysis_router
from app.modules.reports.router import router as reports_router
from app.modules.result_center.router import router as result_center_router
from app.modules.runs.router import router as runs_router
from app.modules.test_datasets.router import router as test_datasets_router
from app.modules.test_capabilities.router import router as test_capabilities_router
from app.modules.test_objects.router import router as test_objects_router
from app.modules.test_tasks.router import router as test_tasks_router
from app.modules.ui_testing.router import router as ui_testing_router
from app.modules.users.router import router as users_router


router = APIRouter()

# Keep the order aligned with the platform menu and shared services.
for module_router in [
    health_router,
    auth_router,
    users_router,
    projects_router,
    test_objects_router,
    test_capabilities_router,
    mock_service_router,
    test_tasks_router,
    result_center_router,
    problem_diagnosis_router,
    quality_analysis_router,
    test_datasets_router,
    api_testing_router,
    ui_testing_router,
    file_transfer_router,
    image_tools_router,
    integrations_router,
    runs_router,
    reports_router,
]:
    router.include_router(module_router)
