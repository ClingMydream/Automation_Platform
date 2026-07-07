"""Tests for result-center attachment evidence helpers."""

from app.models.entities import TestAttachment as AttachmentModel
from app.modules.result_center.service import list_attachments_for_target


class FakeQuery:
    """Tiny query object that records filter/order calls and returns rows."""

    def __init__(self, rows):
        """Store rows and initialize a filter counter for assertions."""
        self.rows = rows
        self.filter_count = 0

    def filter(self, *_args, **_kwargs):
        """Count applied filters without evaluating SQLAlchemy expressions."""
        self.filter_count += 1
        return self

    def order_by(self, *_args, **_kwargs):
        """Ignore ordering because this test only checks query wiring."""
        return self

    def limit(self, _count):
        """Ignore limits while preserving the chained query interface."""
        return self

    def all(self):
        """Return configured attachment rows."""
        return self.rows


class FakeDb:
    """Tiny fake database for attachment service tests."""

    def __init__(self, rows):
        """Store rows and keep the last query for assertions."""
        self.rows = rows
        self.last_query = None

    def query(self, model):
        """Return a fake query for attachment models."""
        assert model is AttachmentModel
        self.last_query = FakeQuery(self.rows)
        return self.last_query


def test_list_attachments_for_result_and_batch_applies_filters():
    """Attachment listing should support result and batch filters together."""
    rows = [AttachmentModel(id=1, result_id=2, batch_id=3, original_name="report.html", stored_name="stored", size_bytes=10)]
    db = FakeDb(rows)

    result = list_attachments_for_target(db, result_id=2, batch_id=3)

    assert result == rows
    assert db.last_query.filter_count == 2
