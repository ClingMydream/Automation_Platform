from types import SimpleNamespace

from app.api.routes import router
from app.core.menu import ALL_MENU_KEYS
from app.db import Base
from app.modules.users.service import user_response


def test_retired_apis_and_permissions_are_removed():
    paths = [route.path for route in router.routes]
    assert not any(path.startswith(('/v1/learning', '/v1/hotel-practice')) for path in paths)
    assert {'learning', 'restful_booker', 'family_oa_web'}.isdisjoint(ALL_MENU_KEYS)
    assert any(path.startswith('/oa/admin') for path in paths)
    assert any(path.startswith('/v1/self-study') for path in paths)
    assert not any(name.startswith(('learning_', 'hotel_practice_')) for name in Base.metadata.tables)


def test_existing_users_do_not_receive_retired_permission_choices():
    user = SimpleNamespace(id=1, username='existing', display_name='Existing', is_admin=False,
                           is_active=True, menu_permissions=['learning', 'codec', 'restful_booker', 'family_oa_web'],
                           created_at=None)
    assert user_response(user)['menu_permissions'] == ['codec']
