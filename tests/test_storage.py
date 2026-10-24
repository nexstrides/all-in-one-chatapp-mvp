import json
from unittest.mock import patch

import pytest

from allinone.models import Service
from allinone.storage import History, Store, data_directory


def test_ten_accounts_persist_separately(tmp_path):
    store = Store(tmp_path)
    for i in range(10):
        store.add(Service(f"Slack {i}", "https://app.slack.com", "slack"))
    loaded = Store(tmp_path)
    assert len(loaded.services) == 10
    assert len({loaded.profile_path(s.id) for s in loaded.services}) == 10
    assert loaded.services == store.services


def test_atomic_failure_keeps_last_good_file(tmp_path):
    store = Store(tmp_path)
    original = Service("Original", "https://web.telegram.org")
    store.add(original)
    before = store.path.read_bytes()
    with patch("allinone.storage.os.replace", side_effect=OSError("disk error")):
        with pytest.raises(OSError):
            store.add(Service("New", "https://web.telegram.org"))
    assert store.path.read_bytes() == before
    assert store.services == [original]
    assert not list(tmp_path.glob("settings-*.tmp"))


def test_remove_retry_and_history_purge(tmp_path):
    store = Store(tmp_path)
    service = Service("Private work", "https://app.slack.com")
    store.add(service)
    profile = store.profile_path(service.id)
    profile.mkdir(parents=True)
    (profile / "session").write_text("test fixture, not a credential")
    history = History(tmp_path / "history.sqlite3")
    history.record(service)
    store.remove(service.id)
    history.clear(service.id)
    with patch("allinone.storage.shutil.rmtree", side_effect=PermissionError):
        store.cleanup()
    assert Store(tmp_path).pending_deletions == [service.id]
    restarted = Store(tmp_path)
    restarted.cleanup()
    assert not profile.exists()
    assert not restarted.services
    assert not restarted.pending_deletions
    assert not history.search()
    history.close()


def test_remove_save_failure_rolls_back(tmp_path):
    store = Store(tmp_path)
    service = Service("A", "https://example.test")
    store.add(service)
    with patch("allinone.storage.os.replace", side_effect=OSError):
        with pytest.raises(OSError):
            store.remove(service.id)
    assert store.services == [service]
    assert store.pending_deletions == []
    with pytest.raises(ValueError):
        store.add(service)
    with pytest.raises(ValueError):
        store.remove("0" * 32)


def test_invalid_settings_preserved(tmp_path):
    path = tmp_path / "services.json"
    for content in ["broken", '{"schema":99}', '{"schema":1,"services":[{}]}']:
        path.write_text(content)
        with pytest.raises(ValueError):
            Store(tmp_path)
        assert path.read_text() == content


def test_duplicate_and_tombstone_collision_rejected(tmp_path):
    store = Store(tmp_path)
    service = Service("A", "https://example.test")
    store.add(service)
    data = json.loads(store.path.read_text())
    data["services"].append(service.to_dict())
    store.path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        Store(tmp_path)
    data["services"].pop()
    data["pending_deletions"] = [service.id]
    store.path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        Store(tmp_path)


def test_history_is_metadata_only_literal_search_and_retention(tmp_path):
    history = History(tmp_path / "history.sqlite3")
    service = Service("Client % alpha", "https://app.slack.com")
    now = 1800000000.0
    history.record(service, now - 91 * 86400)
    current = history.record(service, now)
    history.prune(now)
    assert len(history.search("%")) == 1
    assert not history.search("' OR 1=1 --")
    history.mark_opened(current)
    row = history.search("ALPHA")[0]
    assert row["opened"] == 1
    assert set(row.keys()) == {"id", "service_id", "service_name", "created", "opened"}
    history.clear()
    assert history.search() == []
    history.close()


def test_appdata_path(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert data_directory() == tmp_path / "AllInOneChatapp"
