"""Tiny no-install local server for the SGX Swing Dashboard."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import socket
import threading
import urllib.request
import webbrowser

HOST = "127.0.0.1"
PORT = 8765
URL = f"http://{HOST}:{PORT}/?v=5.2.0"


class NoCacheHandler(SimpleHTTPRequestHandler):
    """Serve local files without letting Safari mix old and new versions."""

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, _format, *_args):
        # Keep the Terminal window calm and readable for everyday use.
        return


def port_is_in_use():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        return connection.connect_ex((HOST, PORT)) == 0


def existing_server_is_this_dashboard():
    try:
        with urllib.request.urlopen(f"http://{HOST}:{PORT}/app.js?v=5.2.0", timeout=2) as response:
            return b"sgx-watchlist-v4" in response.read(12000)
    except Exception:
        return False


def open_dashboard():
    webbrowser.open(URL)


def main():
    os.chdir(Path(__file__).resolve().parent)
    print("\nSGX Swing Dashboard running\n")
    print(URL)
    print("\nKeep this window open. Press Control-C to stop.\n")

    if port_is_in_use():
        if existing_server_is_this_dashboard():
            print("The dashboard is already running. Opening it now…")
            open_dashboard()
        else:
            print("Another dashboard is already using this address.")
            print("Close its Terminal window, then double-click START.command again.")
        return

    server = ThreadingHTTPServer((HOST, PORT), NoCacheHandler)
    threading.Timer(0.6, open_dashboard).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
