from __future__ import annotations

import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

from .license import require_pro


def serve() -> None:
    require_pro("Full web dashboard")

    root = Path(__file__).resolve().parent.parent
    ui_dir = root / "dashboard-ui"

    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError("npm was not found. Install Node.js (which includes npm) to run the dashboard UI.")

    if not ui_dir.exists():
        raise RuntimeError("dashboard-ui directory not found.")

    if not (ui_dir / "node_modules").exists():
        subprocess.run([npm, "install"], cwd=str(ui_dir), check=True)

    api_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "watchagent.dashboard_api:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=str(root),
    )

    ui_proc = subprocess.Popen(
        [npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", "3001"],
        cwd=str(ui_dir),
    )

    try:
        time.sleep(2)
        webbrowser.open("http://127.0.0.1:3001")
        print("watchagent dashboard started")
        print("API: http://127.0.0.1:8000")
        print("UI : http://127.0.0.1:3001")
        print("Press Ctrl+C to stop.")
        while True:
            if api_proc.poll() is not None:
                raise RuntimeError("API process exited unexpectedly.")
            if ui_proc.poll() is not None:
                raise RuntimeError("UI process exited unexpectedly.")
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        if api_proc.poll() is None:
            api_proc.terminate()
        if ui_proc.poll() is None:
            ui_proc.terminate()
        try:
            api_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_proc.kill()
        try:
            ui_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            ui_proc.kill()
