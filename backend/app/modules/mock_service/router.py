"""Public mock response routes."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.mock_service.service import build_mock_response, find_mock_rule


router = APIRouter(tags=["Mock服务"])


@router.api_route("/mock/{mock_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], summary="调用 Mock 响应")
def call_mock(mock_path: str, request: Request, db: Session = Depends(get_db)) -> Response:
    """Return the configured mock response for the requested method and path."""
    rule = find_mock_rule(db, request.method, mock_path)
    return build_mock_response(rule)
