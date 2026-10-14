from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app.db import Base, get_db
from app.core.auth import create_access_token
from app.models.entities import AppUser, CommandSnippet
from app.models.command_favorites import PersonalCommandFavorite
from app.modules.command_library.router import router


def test_personal_favorites_isolated_and_explicit_set_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr('app.modules.command_library.router.ensure_commands', lambda db: None)
    engine = create_engine(f"sqlite:///{tmp_path / 'favorites.db'}", connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        for name in ['alice', 'bob']:
            db.add(AppUser(username=name, password_hash='unused', menu_permissions=['command_library']))
        db.add(CommandSnippet(category='自定义分类', title='示例', command='echo demo', tags=[], is_favorite=True, is_builtin=True))
        db.commit()
    app = FastAPI(); app.include_router(router, prefix='/api')
    def session():
        with factory() as db: yield db
    app.dependency_overrides[get_db] = session
    with TestClient(app) as client:
        alice = {'Authorization': f"Bearer {create_access_token('alice')}"}
        bob = {'Authorization': f"Bearer {create_access_token('bob')}"}
        url = '/api/v1/command-library'
        assert client.get(url).status_code == 401
        for _ in range(2):
            result = client.put(url + '/1/favorite', headers=alice, json={'is_favorite': True})
            assert result.status_code == 200 and result.json()['is_favorite']
        assert len(client.get(url + '?favorite=true', headers=alice).json()) == 1
        assert client.get(url + '?favorite=true', headers=bob).json() == []
        assert client.get(url, headers=bob).json()[0]['is_favorite'] is False
        assert client.get(url + '/categories', headers=alice).json() == ['自定义分类']
        assert client.put(url + '/1/favorite', headers=alice, json={'is_favorite': 'true'}).status_code == 422
        for _ in range(2): assert client.put(url + '/1/favorite', headers=alice, json={'is_favorite': False}).status_code == 200
    with factory() as db:
        assert db.scalar(select(CommandSnippet.is_favorite)) is True  # legacy data untouched
        assert db.query(PersonalCommandFavorite).count() == 0
