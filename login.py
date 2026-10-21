#!/usr/bin/env python
"""Open an account's profile in a visible window so you can log in by hand.

    .venv/bin/python login.py instagram https://www.instagram.com/
    .venv/bin/python login.py tiktok    https://www.tiktok.com/login

Log in, then close the window. Closing saves the session — cookies into
~/.config/social-bot/state/<account>.json, the rest into the profile — and
every later headless run picks it up. This is what stands in for API
credentials, so it is the first thing to try when an adapter acts logged out.
"""

import argparse

from pw_session import profile_dir, session, state_path


def main() -> int:
    ap = argparse.ArgumentParser(description="Log into a profile by hand.")
    ap.add_argument("account", help="profile name, e.g. instagram")
    ap.add_argument("url", nargs="?", default="about:blank")
    args = ap.parse_args()

    print(f"profile: {profile_dir(args.account)}")
    print(f"cookies: {state_path(args.account)}")
    with session(args.account, headless=False) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(args.url)
        print("\nLog in by hand, then close the browser window.")
        try:
            page.wait_for_event("close", timeout=0)
        except Exception:
            pass
    print("session saved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
