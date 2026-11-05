"""Run News Mood as a desktop app in its own native window (no browser).

Starts the Streamlit app in the background on a free local port, opens it in
a native macOS window, and shuts the server down when you close the window.

    venv/bin/python desktop.py
"""

import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_until_up(url, server, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if server.poll() is not None:
            raise RuntimeError("The News Mood server stopped while starting up.")
        try:
            urllib.request.urlopen(url + "/_stcore/health", timeout=1)
            return
        except OSError:
            time.sleep(0.3)
    raise RuntimeError("The News Mood server took too long to start.")


def brand_app():
    """Show 'News Mood' and its icon in the Dock and menu bar instead of 'Python'."""
    try:
        from AppKit import NSApplication, NSImage
        from Foundation import NSBundle

        info = NSBundle.mainBundle().infoDictionary()
        info["CFBundleName"] = info["CFBundleDisplayName"] = "News Mood"
        icon = NSImage.alloc().initWithContentsOfFile_(str(HERE / "assets" / "icon.png"))
        if icon:
            NSApplication.sharedApplication().setApplicationIconImage_(icon)
    except Exception:
        pass  # purely cosmetic


def main():
    brand_app()
    port = free_port()
    url = f"http://127.0.0.1:{port}"
    server = subprocess.Popen(
        [
            sys.executable, __file__, "--serve", str(os.getpid()),
            "run", str(HERE / "app.py"),
            "--server.headless=true",
            "--server.address=127.0.0.1",
            f"--server.port={port}",
            "--browser.gatherUsageStats=false",
            "--client.toolbarMode=minimal",
        ],
        cwd=HERE,
    )
    try:
        wait_until_up(url, server)
        import webview  # imported here so the server process doesn't load the GUI toolkit

        webview.create_window("News Mood", url, width=1280, height=860, min_size=(700, 500))
        webview.start()  # blocks until the window is closed
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


def serve(parent_pid, streamlit_args):
    """Run Streamlit, exiting as soon as the window process goes away (e.g. ⌘Q or force quit)."""
    def watch_parent():
        while os.getppid() == parent_pid:
            time.sleep(1)
        os._exit(0)

    threading.Thread(target=watch_parent, daemon=True).start()
    from streamlit.web import cli
    sys.argv = ["streamlit", *streamlit_args]
    sys.exit(cli.main())


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--serve":
        serve(int(sys.argv[2]), sys.argv[3:])
    else:
        main()
