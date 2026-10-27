"""Atomic settings and content-free, local notification history."""

import json
import os
import shutil
import sqlite3
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

from allinone.models import THEME_MODES, LocalProfile, Service, validate_id


def data_directory() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home() / ".local" / "share"))
    return base / "AllInOneChatapp"


class Store:
    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "services.json"
        self.services: list[Service] = []
        self.pending_deletions: list[str] = []
        self.dnd = False
        self.theme = "system"
        self.profile = LocalProfile()
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if data.get("schema") != 1 or type(data.get("dnd", False)) is not bool:
                    raise ValueError("Unsupported settings schema")
                self.services = [Service(**row) for row in data["services"]]
                self.pending_deletions = [validate_id(x) for x in data["pending_deletions"]]
                ids = [s.id for s in self.services]
                if len(set(ids)) != len(ids) or set(ids) & set(self.pending_deletions):
                    raise ValueError("Duplicate or deleted service")
                self.dnd = data.get("dnd", False)
                self.profile = LocalProfile(**data.get("profile", {}))
                self.theme = data.get("theme", "system")
                if self.theme not in THEME_MODES:
                    raise ValueError("Unknown theme")
            except (ValueError, KeyError, TypeError) as exc:
                raise ValueError(
                    "Settings are invalid. The existing file has been preserved; "
                    "restore services.json from a backup before restarting."
                ) from exc

    def save(self) -> None:
        data = {
            "schema": 1,
            "dnd": self.dnd,
            "theme": self.theme,
            "profile": asdict(self.profile),
            "services": [s.to_dict() for s in self.services],
            "pending_deletions": self.pending_deletions,
        }
        fd, temporary = tempfile.mkstemp(dir=self.root, prefix="settings-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def add(self, service: Service) -> None:
        if any(s.id == service.id for s in self.services):
            raise ValueError("Duplicate service")
        self.services.append(service)
        try:
            self.save()
        except OSError:
            self.services.remove(service)
            raise

    def remove(self, service_id: str) -> None:
        validate_id(service_id)
        previous = self.services[:]
        if not any(s.id == service_id for s in previous):
            raise ValueError("Unknown service")
        self.services = [s for s in previous if s.id != service_id]
        self.pending_deletions.append(service_id)
        try:
            self.save()  # Tombstone first: a crash must never revive the account.
        except OSError:
            self.services = previous
            self.pending_deletions.remove(service_id)
            raise

    def profile_path(self, service_id: str) -> Path:
        return self.root / "profiles" / validate_id(service_id)

    def cleanup(self, only: str | None = None) -> None:
        for service_id in self.pending_deletions[:]:
            if only is not None and service_id != only:
                continue
            try:
                path = self.profile_path(service_id)
                if path.exists():
                    shutil.rmtree(path)
            except OSError:
                continue  # Chromium can retain Windows file handles until next launch.
            self.pending_deletions.remove(service_id)
        self.save()


class History:
    def __init__(self, path: Path) -> None:
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA secure_delete=ON")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS notifications "
            "(id INTEGER PRIMARY KEY, service_id TEXT, service_name TEXT, "
            "created REAL, opened INTEGER DEFAULT 0)"
        )
        self.prune()

    def record(self, service: Service, now: float | None = None) -> int:
        with self.db:
            cursor = self.db.execute(
                "INSERT INTO notifications(service_id,service_name,created) VALUES (?,?,?)",
                (service.id, service.name, time.time() if now is None else now),
            )
        return int(cursor.lastrowid or 0)

    def search(self, query: str = "") -> list[sqlite3.Row]:
        # instr treats %, _ and quotes as literal text.
        return self.db.execute(
            "SELECT * FROM notifications WHERE instr(lower(service_name),lower(?)) > 0 "
            "ORDER BY created DESC, id DESC LIMIT 500",
            (query,),
        ).fetchall()

    def mark_opened(self, notification_id: int) -> None:
        with self.db:
            self.db.execute("UPDATE notifications SET opened=1 WHERE id=?", (notification_id,))

    def unopened_counts(self) -> dict[str, int]:
        return {
            row["service_id"]: row["count"]
            for row in self.db.execute(
                "SELECT service_id, COUNT(*) AS count FROM notifications "
                "WHERE opened=0 GROUP BY service_id"
            )
        }

    def mark_service_opened(self, service_id: str) -> None:
        with self.db:
            self.db.execute("UPDATE notifications SET opened=1 WHERE service_id=?", (service_id,))

    def clear(self, service_id: str | None = None) -> None:
        with self.db:
            if service_id:
                self.db.execute("DELETE FROM notifications WHERE service_id=?", (service_id,))
            else:
                self.db.execute("DELETE FROM notifications")

    def prune(self, now: float | None = None) -> None:
        cutoff = (time.time() if now is None else now) - 90 * 86400
        with self.db:
            self.db.execute("DELETE FROM notifications WHERE created < ?", (cutoff,))

    def close(self) -> None:
        self.db.close()
