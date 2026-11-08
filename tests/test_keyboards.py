from app.keyboards import admin_menu, main_menu, news_management, notification_menu


def test_main_menu_contains_core_sections_and_referral():
    markup = main_menu()
    callbacks = {
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
    }
    assert {"menu:news", "menu:channels", "menu:education", "menu:media", "menu:referral"} <= callbacks
    assert "admin:home" not in callbacks


def test_admin_menu_exposes_broadcast_and_content_actions():
    markup = admin_menu()
    callbacks = {
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
    }
    assert {"admin:broadcast", "admin:news_new", "admin:news_list", "admin:media_new"} <= callbacks


def test_notification_menu_reflects_preferences():
    markup = notification_menu({"news": True, "announcements": False, "media": True})
    buttons = [button for row in markup.inline_keyboard for button in row]
    labels = [button.text for button in buttons]
    assert "Новости: Вкл." in labels
    assert "Анонсы: Выкл." in labels
    assert "HARISTON MEDIA: Вкл." in labels


def test_news_management_has_edit_and_delete_actions():
    markup = news_management([{"id": 7}, {"id": 8}])
    callbacks = {
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
    }
    assert {"admin:news_edit:7", "admin:news_delete:7", "admin:news_edit:8", "admin:news_delete:8"} <= callbacks


def test_content_management_menu_exposes_all_content_types():
    from app.keyboards import content_type_menu

    markup = content_type_menu()
    callbacks = {
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
    }
    assert {
        "admin:manage:channels",
        "admin:manage:lessons",
        "admin:manage:team",
        "admin:manage:media",
    } <= callbacks



def test_admin_menu_exposes_required_subscription_management():
    callbacks = {
        button.callback_data
        for row in admin_menu().inline_keyboard
        for button in row
    }
    assert "admin:required_channels" in callbacks
