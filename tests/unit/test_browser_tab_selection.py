from __future__ import annotations

from src import browser as browser_module
from src.browser import PlaywrightBrowser


class _DelayedMenuPage:
    def __init__(self, *, activate_after_wait: bool) -> None:
        self.activate_after_wait = activate_after_wait
        self.active = False
        self.wait_calls: list[tuple[str, int]] = []

    def evaluate(self, script: str, argument: list[str]) -> str:
        assert argument == [PlaywrightBrowser._MENU_SELECTOR, "定期报告"]
        if "target.click()" in script:
            return "inactive"
        return "active" if self.active else "inactive"

    def wait_for_function(self, script: str, argument: list[str], *, timeout: int) -> None:
        assert argument == [PlaywrightBrowser._MENU_SELECTOR, "定期报告"]
        self.wait_calls.append((script, timeout))
        if self.activate_after_wait:
            self.active = True
            return
        raise browser_module.PlaywrightTimeoutError("menu selection did not change")


class _UnknownMenuPage:
    def __init__(self) -> None:
        self.wait_calls = 0

    def evaluate(self, script: str, argument: list[str]) -> str:
        return "unknown"

    def wait_for_function(self, script: str, argument: list[str], *, timeout: int) -> None:
        self.wait_calls += 1


def _browser(page: object) -> PlaywrightBrowser:
    browser = PlaywrightBrowser.__new__(PlaywrightBrowser)
    browser._page = page
    return browser


def test_select_menu_item_waits_for_async_active_state() -> None:
    page = _DelayedMenuPage(activate_after_wait=True)

    result = _browser(page).select_menu_item("定期报告")

    assert result == PlaywrightBrowser.TAB_ACTIVE
    assert len(page.wait_calls) == 1
    wait_script, timeout = page.wait_calls[0]
    assert "aria-selected" in wait_script
    assert "is-active" in wait_script
    assert timeout > 0


def test_select_menu_item_returns_inactive_after_selection_timeout() -> None:
    page = _DelayedMenuPage(activate_after_wait=False)

    result = _browser(page).select_menu_item("定期报告")

    assert result == PlaywrightBrowser.TAB_INACTIVE
    assert len(page.wait_calls) == 1


def test_select_menu_item_does_not_wait_when_selection_state_is_unknown() -> None:
    page = _UnknownMenuPage()

    result = _browser(page).select_menu_item("定期报告")

    assert result == PlaywrightBrowser.TAB_UNKNOWN
    assert page.wait_calls == 0

