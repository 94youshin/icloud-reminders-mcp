import pytest
from pyicloud.services.reminders.client import RemindersAuthError

from icloud_reminders_mcp import server


def test_invoke_rebuilds_client_once_after_explicit_auth_error(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, should_fail):
            self.should_fail = should_fail

        def list_lists(self):
            calls.append(self.should_fail)
            if self.should_fail:
                raise RemindersAuthError("expired")
            return [{"id": "l1"}]

    clients = iter([FakeClient(True), FakeClient(False)])

    def fake_client():
        return next(clients)

    cache_clears = []
    fake_client.cache_clear = lambda: cache_clears.append(True)
    monkeypatch.setattr(server, "_client", fake_client)

    assert server._invoke("list_lists") == [{"id": "l1"}]
    assert calls == [True, False]
    assert cache_clears == [True]


def test_invoke_does_not_retry_non_auth_errors(monkeypatch):
    class FakeClient:
        def list_lists(self):
            raise RuntimeError("network failed")

    def fake_client():
        return FakeClient()

    cache_clears = []
    fake_client.cache_clear = lambda: cache_clears.append(True)
    monkeypatch.setattr(server, "_client", fake_client)

    with pytest.raises(RuntimeError, match="network failed"):
        server._invoke("list_lists")
    assert cache_clears == []
