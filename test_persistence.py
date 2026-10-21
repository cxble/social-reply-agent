"""Proves the thing the whole no-API design rests on: the login survives.

Both halves matter — the profile carries localStorage and the state file
carries cookies — and Chromium will not flush the cookie store on its own. A
regression here means every adapter silently logs out between runs.
"""

import http.server
import shutil
import socketserver
import threading

import pytest

from pw_session import profile_dir, session, state_path


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"<title>probe</title>ok"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Set-Cookie", "srvprobe=1; Path=/")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def site():
    """A throwaway localhost site, so none of these tests need the network."""
    with socketserver.TCPServer(("127.0.0.1", 0), _Handler) as httpd:
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
        httpd.shutdown()


@pytest.fixture
def account():
    name = "_selftest"
    shutil.rmtree(profile_dir(name), ignore_errors=True)
    state_path(name).unlink(missing_ok=True)
    yield name
    shutil.rmtree(profile_dir(name), ignore_errors=True)
    state_path(name).unlink(missing_ok=True)


def test_cookies_survive_between_sessions(site, account):
    with session(account, headless=True) as ctx:
        ctx.new_page().goto(site)
        assert "srvprobe" in {c["name"] for c in ctx.cookies()}

    with session(account, headless=True) as ctx:
        jar = {c["name"] for c in ctx.cookies()}  # read before navigating
        assert "srvprobe" in jar, f"cookie jar did not persist: {jar}"


def test_localstorage_survives_between_sessions(site, account):
    with session(account, headless=True) as ctx:
        page = ctx.new_page()
        page.goto(site)
        page.evaluate("localStorage.setItem('probe', 'kept')")

    with session(account, headless=True) as ctx:
        page = ctx.new_page()
        page.goto(site)
        assert page.evaluate("localStorage.getItem('probe')") == "kept"


def test_state_file_is_not_world_readable(site, account):
    with session(account, headless=True) as ctx:
        ctx.new_page().goto(site)
    mode = state_path(account).stat().st_mode
    assert mode & 0o077 == 0, f"session jar is too permissive: {oct(mode)}"
