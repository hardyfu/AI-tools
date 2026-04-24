#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sqlite3
import sys
import threading
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "flowplan.db"
PID_FILE = ROOT / ".server.pid"


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                data TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO app_state (id, data)
            VALUES (1, ?)
            ON CONFLICT(id) DO NOTHING
            """,
            (json.dumps({"categories": [], "projects": [], "plans": []}, ensure_ascii=False),),
        )
        conn.commit()


def load_state() -> dict[str, Any]:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT data FROM app_state WHERE id = 1").fetchone()
    if not row:
        return {"categories": [], "projects": [], "plans": []}
    return json.loads(row[0])


def save_state(payload: dict[str, Any]) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE app_state SET data = ? WHERE id = 1", (json.dumps(payload, ensure_ascii=False),))
        conn.commit()


class FlowPlanHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self) -> None:
        if self.path == "/api/state":
            self._write_json(load_state())
            return
        super().do_GET()

    def end_headers(self) -> None:
        if self.path != "/api/state":
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        super().end_headers()

    def do_PUT(self) -> None:
        if self.path != "/api/state":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON")
            return

        if not isinstance(payload, dict):
            self.send_error(HTTPStatus.BAD_REQUEST, "Payload must be an object")
            return

        save_state(payload)
        self._write_json({"ok": True})

    def do_POST(self) -> None:
        if self.path != "/api/shutdown":
          self.send_error(HTTPStatus.NOT_FOUND)
          return

        self._write_json({"ok": True, "message": "server shutting down"})

        def _shutdown() -> None:
            try:
                if PID_FILE.exists():
                    PID_FILE.unlink(missing_ok=True)
            except OSError:
                pass
            threading.Thread(target=self.server.shutdown, daemon=True).start()

        threading.Timer(0.1, _shutdown).start()

    def _write_json(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    init_db()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", port), FlowPlanHandler)
    print(f"FlowPlan server running at http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            PID_FILE.unlink(missing_ok=True)
        except OSError:
            pass
        server.server_close()


if __name__ == "__main__":
    main()
