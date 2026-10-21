"""Serve a Recorded page from an explicit path on localhost."""

from __future__ import annotations

import contextlib
import functools
import http.server
import mimetypes
import socketserver
import threading
from pathlib import Path
from urllib.parse import unquote, urlsplit


class _RecordedPageHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class _ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


@contextlib.contextmanager
def recorded_page(path: str | Path):
    """Yield a localhost URL serving the given saved page.

    `path` must point at the HTML file to open. Any sibling assets are served
    from the same directory, so a human capture can include sidecar files.
    """
    page_path = Path(path).expanduser().resolve(strict=True)
    if not page_path.is_file():
        raise ValueError(f"Recorded page must be a file: {page_path}")

    directory = str(page_path.parent)
    handler = functools.partial(_RecordedPageHandler, directory=directory)
    with _ThreadingTCPServer(("127.0.0.1", 0), handler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            quoted_name = page_path.name
            yield f"http://127.0.0.1:{httpd.server_address[1]}/{quoted_name}"
        finally:
            httpd.shutdown()
            thread.join(timeout=5)
