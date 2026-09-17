"""Regression coverage for Mini Program OA personnel administration."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.modules.oa.router import (
    AccountCreate,
    AccountUpdate,
    create_mini_account,
    delete_mini_account,
    list_mini_accounts,
    update_mini_account,
)


def test_admin_can_create_update_and_remove_mini_program_people():
    """A manually-created account can choose another person as its reviewer."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        first = create_mini_account(
            AccountCreate(username="baby_a", password="secret12", display_name="小美", family_role="宝宝"),
            None,
            db,
        )
        second = create_mini_account(
            AccountCreate(username="baby_b", password="secret12", display_name="小林", family_role="男朋友"),
            None,
            db,
        )

        update_mini_account(
            first["id"],
            AccountUpdate(
                display_name="小美呀",
                family_role="女朋友",
                is_enabled=True,
                approver_account_ids=[second["id"]],
            ),
            None,
            db,
        )
        updated = next(item for item in list_mini_accounts(None, db)["accounts"] if item["id"] == first["id"])
        assert updated["name"] == "小美呀"
        assert updated["family_role"] == "女朋友"
        assert updated["approver_account_ids"] == [second["id"]]

        delete_mini_account(first["id"], None, db)
        assert all(item["id"] != first["id"] for item in list_mini_accounts(None, db)["accounts"])
