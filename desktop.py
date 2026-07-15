"""Native desktop launcher using WebView2 on Windows and WebKit on macOS."""

from __future__ import annotations

import os
import shutil
import socket
import sys
import threading
import time
from pathlib import Path


APP_NAME = "CSLT-OnThi"


def bundle_root() -> Path:
    """Return the project root in development or PyInstaller's unpacked bundle."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    if sys.platform == "darwin" and getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent.parent / "Resources"
    return Path(__file__).resolve().parent


def application_data_path(platform: str | None = None) -> Path:
    """Return the writable per-user location for the installed question bank."""
    system = platform or sys.platform
    home = Path(os.environ.get("HOME", Path.home()))
    if system == "win32":
        return Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local")) / APP_NAME
    if system == "darwin":
        return home / "Library" / "Application Support" / APP_NAME
    return Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share")) / APP_NAME


def configure_database_path(root: Path | None = None) -> Path:
    """Copy the bundled seed database once, then point FastAPI to the writable copy."""
    source = (root or bundle_root()) / "data" / "review.db"
    destination = application_data_path() / "data" / "review.db"
    if not destination.exists():
        if not source.is_file():
            raise FileNotFoundError(f"Không tìm thấy database đóng gói: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    os.environ["CSLT_DATABASE_PATH"] = str(destination)
    return destination


def _free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_server(port: int, timeout_seconds: float = 10) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise TimeoutError("Máy chủ ứng dụng không khởi động kịp thời.")


def main() -> None:
    configure_database_path()
    import uvicorn
    import webview
    from app import app

    port = _free_local_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    )
    thread = threading.Thread(target=server.run, name="csltonthi-server", daemon=True)
    thread.start()
    _wait_for_server(port)
    webview.create_window("Ôn thi HUB", f"http://127.0.0.1:{port}/", width=1280, height=900, min_size=(1024, 700))
    try:
        if sys.platform == "win32":
            webview.start(gui="edgechromium")
        else:
            webview.start()
    finally:
        server.should_exit = True
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
