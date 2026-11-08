from dataclasses import replace

from app.config import settings
from app.handlers import admin


def test_only_configured_telegram_ids_are_admin(monkeypatch):
    monkeypatch.setattr(admin, "settings", replace(settings, admin_ids={1001, 2002}))

    assert admin.is_admin(1001)
    assert admin.is_admin(2002)
    assert not admin.is_admin(9999)


def test_empty_admin_allowlist_denies_everyone(monkeypatch):
    monkeypatch.setattr(admin, "settings", replace(settings, admin_ids=set()))

    assert not admin.is_admin(1001)
