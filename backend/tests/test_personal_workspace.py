from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.modules.personal_workspace.router import RecordInput, RecordUpdate, create, records, save, remove, restore


def test_private_records_revision_and_recycle_bin(tmp_path):
    engine = create_engine('sqlite:///' + str(tmp_path / 'workspace.db'))
    Base.metadata.create_all(engine)
    alice, bob = SimpleNamespace(username='alice'), SimpleNamespace(username='bob')
    with Session(engine) as db:
        item = create(RecordInput(kind='note', title=' Python ', content='print(1)', tags=['Python','Python']), alice, db)
        assert item['title'] == 'Python' and item['tags'] == ['Python']
        assert records(None, '', False, bob, db) == []
        with pytest.raises(HTTPException) as error:
            remove(item['id'], bob, db)
        assert error.value.status_code == 404
        changed = save(item['id'], RecordUpdate(kind='note', title='笔记', content='print(2)', revision=1), alice, db)
        assert changed['revision'] == 2
        with pytest.raises(HTTPException) as error:
            save(item['id'], RecordUpdate(kind='note', title='过期修改', revision=1), alice, db)
        assert error.value.status_code == 409
        remove(item['id'], alice, db)
        assert records(None, '', False, alice, db) == []
        assert len(records(None, '', True, alice, db)) == 1
        restored = restore(item['id'], alice, db)
        assert restored['content'] == 'print(2)' and restored['revision'] == 4
