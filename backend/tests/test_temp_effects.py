"""Temporary effects stay isolated and can be removed completely."""

import asyncio
import io
import zipfile

import pytest
from fastapi import HTTPException, UploadFile

from app.modules.effects import router as effects


def archive(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as bundle:
        for name, content in files.items():
            bundle.writestr(name, content)
    stream.seek(0)
    return UploadFile(file=stream, filename="demo.zip")


def test_upload_preview_and_clear(tmp_path, monkeypatch):
    monkeypatch.setattr(effects, "ROOT", tmp_path)
    item = asyncio.run(effects.upload_effect(archive({"index.html": "<h1>OK</h1>", "assets/site.js": "ok"}), None))
    assert effects.list_effects(None) == [item]
    assert (tmp_path / item["id"] / "assets/site.js").read_text() == "ok"
    assert effects.preview_effect(item["id"], "index.html").path.name == "index.html"
    effects.clear_effects(None)
    assert effects.list_effects(None) == []


def test_rejects_zip_slip(tmp_path, monkeypatch):
    monkeypatch.setattr(effects, "ROOT", tmp_path)
    with pytest.raises(HTTPException) as error:
        asyncio.run(effects.upload_effect(archive({"index.html": "ok", "../escape": "bad"}), None))
    assert error.value.status_code == 400


def test_builtin_effect_can_be_disabled_without_clearing_uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(effects, "ROOT", tmp_path)
    assert effects.builtin_effect() == {"enabled": True}
    effects.delete_builtin_effect(None)
    assert effects.builtin_effect() == {"enabled": False}
    effects.clear_effects(None)
    assert effects.builtin_effect() == {"enabled": False}
