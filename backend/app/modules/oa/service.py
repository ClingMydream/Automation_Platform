"""Seed data and serializers for the first OA approval workflow."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.entities import AppUser, OaApprovalAction, OaApprovalRequest, OaApprovalTemplate


DEFAULT_TEMPLATES = [
    {
        "key": "leave", "name": "请假申请", "description": "提交休假、病假或事假申请", "icon": "🌸", "color": "#f69ab7", "sort_order": 10,
        "fields": [{"key": "leave_type", "label": "请假类型", "type": "select", "options": ["事假", "病假", "年假", "其他"], "required": True}, {"key": "start_date", "label": "开始日期", "type": "date", "required": True}, {"key": "end_date", "label": "结束日期", "type": "date", "required": True}, {"key": "reason", "label": "请假事由", "type": "textarea", "required": True}],
    },
    {
        "key": "expense", "name": "费用报销", "description": "提交工作相关费用报销", "icon": "🎀", "color": "#c996e8", "sort_order": 20,
        "fields": [{"key": "amount", "label": "报销金额（元）", "type": "number", "required": True}, {"key": "expense_date", "label": "发生日期", "type": "date", "required": True}, {"key": "reason", "label": "报销说明", "type": "textarea", "required": True}],
    },
    {
        "key": "purchase", "name": "采购申请", "description": "申请办公用品或项目物资", "icon": "🍓", "color": "#f4b455", "sort_order": 30,
        "fields": [{"key": "item_name", "label": "采购物品", "type": "text", "required": True}, {"key": "amount", "label": "预计金额（元）", "type": "number", "required": True}, {"key": "reason", "label": "申请说明", "type": "textarea", "required": True}],
    },
]


def seed_templates(db: Session) -> None:
    """Create starter templates once; later changes are made through administration APIs."""
    for item in DEFAULT_TEMPLATES:
        if db.query(OaApprovalTemplate).filter(OaApprovalTemplate.key == item["key"]).first() is None:
            db.add(OaApprovalTemplate(**item))
    db.commit()


def template_response(template: OaApprovalTemplate) -> dict:
    return {"id": template.id, "key": template.key, "name": template.name, "description": template.description, "icon": template.icon, "color": template.color, "fields": template.fields, "is_active": template.is_active}


def request_response(request: OaApprovalRequest, template: OaApprovalTemplate, requester: AppUser, actions: list[OaApprovalAction], users: dict[int, AppUser]) -> dict:
    return {
        "id": request.id, "request_no": request.request_no, "title": request.title, "status": request.status,
        "form_data": request.form_data, "created_at": request.created_at.isoformat(), "completed_at": request.completed_at.isoformat() if request.completed_at else None,
        "template": template_response(template),
        "requester": {"name": requester.display_name or requester.username},
        "actions": [{"action": action.action, "comment": action.comment, "actor_name": (users.get(action.actor_user_id).display_name or users.get(action.actor_user_id).username) if users.get(action.actor_user_id) else "系统", "created_at": action.created_at.isoformat()} for action in actions],
    }


def request_number() -> str:
    return f"OA{datetime.utcnow():%Y%m%d%H%M%S%f}"
